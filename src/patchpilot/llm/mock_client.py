"""Mock LLM client for deterministic testing, offline dry-runs, and CI pipelines."""

from __future__ import annotations

from patchpilot.llm.base import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Deterministic offline client simulating synthesis outputs for testing."""

    def __init__(self, canned_patch: str = "", canned_test: str = "") -> None:
        self.canned_patch = canned_patch
        self.canned_test = canned_test or (
            "import pytest\n\n"
            "def test_reproduction():\n"
            "    # Simulated reproduction test\n"
            "    assert True\n"
        )

    def generate_reproduction_test(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
    ) -> str:
        return self.canned_test

    def generate_patch(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
        failing_test_code: str,
        failing_output: str,
    ) -> str:
        if self.canned_patch:
            return self.canned_patch
        return (
            "--- a/target.py\n"
            "+++ b/target.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-def calculate(x): return x / 0\n"
            "+def calculate(x): return x\n"
        )

    def refine_patch(
        self,
        previous_patch: str,
        error_output: str,
        repo_context: str,
    ) -> str:
        return self.generate_patch("", "", repo_context, "", error_output)
