"""Main orchestrator coordinating parsing, AST mapping, sandboxing, and verification."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from patchpilot.core.issue_parser import IssueParser, ParsedIssue
from patchpilot.core.repo_map import RepoMap
from patchpilot.git.worktree import GitWorktreeManager
from patchpilot.llm.base import BaseLLMClient
from patchpilot.llm.gemini_client import GeminiLLMClient
from patchpilot.llm.mock_client import MockLLMClient
from patchpilot.llm.ollama_client import OllamaLLMClient
from patchpilot.llm.openai_client import OpenAILLMClient
from patchpilot.verifier.loop import VerificationLoop, VerificationOutcome


class PatchPilotResult(BaseModel):
    issue: ParsedIssue
    outcome: VerificationOutcome
    branch_name: str
    worktree_path: Optional[str] = None


class PatchPilotOrchestrator:
    """End-to-end controller for autonomous issue reproduction, triage, and patch synthesis."""

    def __init__(
        self,
        repo_dir: Path | str,
        provider: str = "mock",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        self.repo_map = RepoMap(self.repo_dir)
        self.git_manager = GitWorktreeManager(self.repo_dir)
        self.llm = self._init_llm(provider, api_key, model)

    def _init_llm(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseLLMClient:
        prov = provider.lower()
        if prov == "openai":
            return OpenAILLMClient(api_key=api_key, model=model or "gpt-4o")
        elif prov == "gemini":
            return GeminiLLMClient(api_key=api_key, model=model or "gemini-2.5-flash")
        elif prov == "ollama":
            return OllamaLLMClient(model=model or "llama3:latest")
        else:
            return MockLLMClient()

    def triage(self, title: str, body: str, url: Optional[str] = None) -> dict:
        """Scan codebase and triage an issue, mapping relevant symbols and files."""
        parsed = IssueParser.parse_text(title, body, url=url)
        self.repo_map.scan()

        # Query terms from title and error types
        query_terms = parsed.title.split() + parsed.error_types
        ranked_files = self.repo_map.rank_relevance(query_terms, parsed.referenced_files)
        context_prompt = self.repo_map.generate_context_prompt(ranked_files, max_files=5)

        return {
            "parsed_issue": parsed,
            "top_relevant_files": [f.rel_path for f in ranked_files[:5]],
            "context_prompt": context_prompt,
        }

    def solve(
        self,
        title: str,
        body: str,
        url: Optional[str] = None,
        max_iterations: int = 3,
    ) -> PatchPilotResult:
        """Execute full autonomous workflow: triage -> sandbox -> reproduce -> patch -> verify."""
        # 1. Triage & Map
        triage_info = self.triage(title, body, url=url)
        parsed: ParsedIssue = triage_info["parsed_issue"]
        context_prompt: str = triage_info["context_prompt"]

        # 2. Check Git Repo
        if not self.git_manager.is_git_repo():
            raise RuntimeError(f"Target directory {self.repo_dir} is not a valid git repository.")

        # 3. Create Isolated Worktree
        issue_id = parsed.issue_number or uuid.uuid4().hex[:6]
        branch_name = f"patchpilot/issue-{issue_id}"
        worktree_path = self.git_manager.create_worktree(branch_name)

        try:
            # 4. Generate Reproduction Test
            repro_test = self.llm.generate_reproduction_test(
                issue_title=parsed.title,
                issue_body=parsed.body,
                repo_context=context_prompt,
            )

            # 5. Run Verification Loop
            loop = VerificationLoop(
                worktree_path=worktree_path,
                worktree_manager=self.git_manager,
                llm_client=self.llm,
                max_iterations=max_iterations,
            )
            outcome = loop.execute(
                issue_title=parsed.title,
                issue_body=parsed.body,
                repo_context=context_prompt,
                initial_reproduction_test=repro_test,
            )

            return PatchPilotResult(
                issue=parsed,
                outcome=outcome,
                branch_name=branch_name,
                worktree_path=str(worktree_path),
            )
        finally:
            # Clean up worktree if not successful
            pass
