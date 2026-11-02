"""Autonomous GitHub Action Bot handling asynchronous issue triggers and PR creation."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional
import httpx

from patchpilot.core.issue_parser import IssueParser
from patchpilot.core.orchestrator import PatchPilotOrchestrator
from patchpilot.core.universal_scanner import UniversalCodeScanner


class GitHubActionBot:
    """Headless worker executing in GitHub Actions to autonomously triage issues and open verified PRs."""

    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.repo = os.getenv("GITHUB_REPOSITORY", "")  # e.g. "owner/repo"
        self.event_path = os.getenv("GITHUB_EVENT_PATH", "")
        self.api_base = "https://api.github.com"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PatchPilot-Autonomous-Bot",
        }

    def run(self) -> None:
        """Main entry point triggered by GitHub Action on `issues: [opened, labeled]`."""
        if not self.event_path or not Path(self.event_path).exists():
            print("No GITHUB_EVENT_PATH detected. Ensure this runs inside GitHub Actions.")
            return

        with open(self.event_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        issue_data = payload.get("issue", {})
        issue_number = issue_data.get("number")
        issue_title = issue_data.get("title", "")
        issue_body = issue_data.get("body", "")

        if not issue_number or not issue_title:
            print("Event does not contain an issue payload. Skipping.")
            return

        print(f"🤖 PatchPilot Bot activated for Issue #{issue_number}: {issue_title}")

        # 1. Post initial thinking comment on GitHub Issue
        self.post_issue_comment(
            issue_number,
            "🔍 **PatchPilot Autonomous Bot** has picked up this issue. "
            "Scanning codebase, running reproduction tests, and synthesizing verified patch in background...",
        )

        # 2. Universal Scanner
        scanner = UniversalCodeScanner(Path("."))
        scanner.scan()
        parsed = IssueParser.parse_text(issue_title, issue_body)
        ranked = scanner.rank_relevance(parsed.title.split() + parsed.error_types, parsed.referenced_files)
        context_prompt = scanner.generate_context_prompt(ranked, max_files=5)

        # 3. Autonomous Solver
        provider = os.getenv("LLM_PROVIDER", "openai")
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        model = os.getenv("LLM_MODEL")

        orchestrator = PatchPilotOrchestrator(
            repo_dir=Path("."),
            provider=provider,
            api_key=api_key,
            model=model,
        )

        try:
            result = orchestrator.solve(
                title=issue_title,
                body=issue_body,
                max_iterations=3,
            )
        except Exception as exc:
            self.post_issue_comment(
                issue_number,
                f"⚠️ **PatchPilot Notice:** Could not complete automated patch verification.\n\n"
                f"**Reason:** `{exc}`\n\n"
                f"**Top Relevant Files Identified:**\n"
                + "\n".join([f"- `{f.rel_path}` ({f.language})" for f in ranked[:3]]),
            )
            return

        outcome = result.outcome
        if outcome.success:
            branch_name = f"patchpilot/fix-issue-{issue_number}"

            # Create branch, commit, and push
            subprocess.run(["git", "config", "user.name", "patchpilot-bot[bot]"], check=True)
            subprocess.run(["git", "config", "user.email", "patchpilot-bot@users.noreply.github.com"], check=True)
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            subprocess.run(["git", "apply", "-"], input=outcome.final_diff, text=True, check=True)
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"fix(autonomously-verified): resolve issue #{issue_number}"],
                check=True,
            )
            subprocess.run(["git", "push", "origin", branch_name], check=True)

            # Open Pull Request
            pr_body = (
                f"## 🛠️ Autonomous Verified Fix for #{issue_number}\n\n"
                f"This pull request was autonomously generated and verified by **PatchPilot**.\n\n"
                f"### Verification Details:\n"
                f"- **Iterations Required:** {outcome.iterations}\n"
                f"- **Reproduction Test Status:** Passed\n"
                f"- **Regression Test Suite:** Passed\n\n"
                f"Closes #{issue_number}"
            )
            pr_url = self.create_pull_request(
                title=f"fix: autonomously resolve issue #{issue_number}",
                body=pr_body,
                head=branch_name,
                base="main",
            )

            # Final comment on issue
            self.post_issue_comment(
                issue_number,
                f"✅ **PatchPilot Resolution:** A verified fix has been synthesized and tested!\n\n"
                f"Pull Request created: **[{pr_url}]({pr_url})**\n\n"
                f"*Maintainer can review and merge with 1 click.*",
            )
        else:
            self.post_issue_comment(
                issue_number,
                f"⚠️ **PatchPilot Triage Summary:**\n"
                f"Attempted automated patch synthesis, but the verification loop did not reach a clean passing state.\n\n"
                f"**Flagged Files for Human Review:**\n"
                + "\n".join([f"- `{f.rel_path}` ({f.language})" for f in ranked[:4]]),
            )

    def post_issue_comment(self, issue_number: int, comment: str) -> None:
        if not self.token or not self.repo:
            return
        url = f"{self.api_base}/repos/{self.repo}/issues/{issue_number}/comments"
        try:
            with httpx.Client(timeout=30.0) as client:
                client.post(url, headers=self._headers(), json={"body": comment})
        except Exception as exc:
            print(f"Failed to post GitHub comment: {exc}")

    def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> str:
        url = f"{self.api_base}/repos/{self.repo}/pulls"
        payload = {"title": title, "body": body, "head": head, "base": base}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json().get("html_url", "")
