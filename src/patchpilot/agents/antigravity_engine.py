"""Google Antigravity Multi-Agent Orchestration Engine for PatchPilot."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from patchpilot.core.universal_scanner import UniversalCodeScanner
from patchpilot.git.worktree import GitWorktreeManager
from patchpilot.security.guardrails import SecurityGuard
from patchpilot.verifier.runner import TestRunner


class AntigravitySolveResult(BaseModel):
    success: bool
    iterations: int
    final_diff: str = ""
    reproduction_test: str = ""
    agent_reasoning: str = ""


class AntigravityAgentEngine:
    """Autonomous agentic co-maintainer powered by the Google Antigravity SDK."""

    def __init__(
        self,
        repo_dir: Path | str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        use_local: bool = False,
    ) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.use_local = use_local
        self.git_manager = GitWorktreeManager(self.repo_dir)

    def is_available(self) -> bool:
        """Check if google-antigravity SDK is installed and available."""
        try:
            import google.antigravity
            return True
        except ImportError:
            return False

    def build_tools(self, worktree_path: Path):
        """Construct native Python functions with typed signatures for Antigravity Agent tools."""

        def scan_codebase_symbols(query: str) -> str:
            """Scans polyglot codebase (Python, TypeScript, Go, Rust, C++) for symbols matching query.

            Args:
                query: Search keyword or function/class name.
            """
            scanner = UniversalCodeScanner(worktree_path)
            scanner.scan()
            ranked = scanner.rank_relevance(query.split(), [])
            return scanner.generate_context_prompt(ranked, max_files=4)

        def run_isolated_test(test_rel_path: str) -> str:
            """Executes a test file inside the isolated sandbox to check pass/fail state.

            Args:
                test_rel_path: Relative path to test file e.g. tests/test_reproduce.py
            """
            res = TestRunner.run_tests(worktree_path, test_file=test_rel_path)
            if res.success:
                return f"TEST PASSED: {res.passed_count} test(s) succeeded."
            return f"TEST FAILED: {res.error_summary or res.stdout or res.stderr}"

        def audit_diff_security(unified_diff: str) -> str:
            """Audits a proposed git diff patch against Zero-Trust security rules.

            Args:
                unified_diff: Raw unified diff string starting with --- and +++
            """
            is_safe, violations = SecurityGuard.validate_patch_diff(unified_diff)
            if is_safe:
                return "SECURITY PASSED: Diff does not modify protected paths (.github, .env, secrets)."
            return f"SECURITY BLOCKED: {', '.join(violations)}"

        return [scan_codebase_symbols, run_isolated_test, audit_diff_security]

    async def solve_async(
        self,
        issue_title: str,
        issue_body: str,
    ) -> AntigravitySolveResult:
        """Orchestrate multi-step autonomous bug investigation and resolution using Antigravity Agent."""
        if not self.is_available():
            raise RuntimeError("google-antigravity SDK is not installed.")

        from google.antigravity import Agent, AgentBehavior, LocalAgentConfig, LocalOpenAIAgentConfig

        # 1. Setup isolated worktree
        branch_name = "patchpilot/antigravity-solve"
        worktree_path = self.git_manager.create_worktree(branch_name)

        try:
            tools = self.build_tools(worktree_path)

            if self.use_local:
                config = LocalOpenAIAgentConfig(
                    tools=tools,
                    agent_behavior=AgentBehavior.AUTONOMOUS,
                )
            else:
                config = LocalAgentConfig(
                    api_key=self.api_key,
                    tools=tools,
                    agent_behavior=AgentBehavior.AUTONOMOUS,
                )

            system_instruction = (
                "You are PatchPilot's Lead Autonomous Software Engineer powered by Google Antigravity. "
                "Your objective is to investigate the reported GitHub issue, find the bug using tools, "
                "synthesize a reproduction test (RED), generate a secure patch (GREEN), and verify "
                "that all tests pass without modifying protected paths."
            )

            prompt = (
                f"### Target Issue:\nTitle: {issue_title}\n\nDescription:\n{issue_body}\n\n"
                "1. Use `scan_codebase_symbols` to inspect the code context.\n"
                "2. Formulate a minimal unified git diff.\n"
                "3. Use `audit_diff_security` to verify safety.\n"
                "4. Produce the final verified solution."
            )

            reasoning_chunks = []
            async with Agent(config) as agent:
                resp = await agent.chat(prompt)
                async for chunk in resp:
                    reasoning_chunks.append(str(chunk))

            full_reasoning = "".join(reasoning_chunks)
            diff = self.git_manager.get_diff(worktree_path)

            return AntigravitySolveResult(
                success=True,
                iterations=1,
                final_diff=diff,
                reproduction_test="",
                agent_reasoning=full_reasoning,
            )
        finally:
            self.git_manager.remove_worktree(branch_name)
