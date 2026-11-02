"""OpenAI and Codex API provider for PatchPilot supporting GPT-6.1 Sol/Terra and o-series."""

from __future__ import annotations

import os
import re
from typing import Optional
import httpx
from patchpilot.llm.base import BaseLLMClient


class OpenAILLMClient(BaseLLMClient):
    """Client for frontier OpenAI models (GPT-6.1 Sol, GPT-6.1 Terra, o3, Codex)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-6.1-sol",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url

    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set it in your environment or pass --api-key."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        with httpx.Client(timeout=90.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def generate_reproduction_test(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
    ) -> str:
        system_prompt = (
            "You are an expert Python test engineer. Write a self-contained pytest reproduction "
            "file for the reported bug. Output ONLY the raw Python code block enclosed in ```python."
        )
        user_prompt = (
            f"### Bug Issue:\nTitle: {issue_title}\n\nDescription:\n{issue_body}\n\n"
            f"### Repository Context:\n{repo_context}\n\n"
            "Generate a pytest file that faithfully asserts the expected correct behavior "
            "and will FAIL on the current buggy code."
        )
        content = self._call_api(system_prompt, user_prompt)
        return self._extract_code(content)

    def generate_patch(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
        failing_test_code: str,
        failing_output: str,
    ) -> str:
        system_prompt = (
            "You are an autonomous software engineering agent. Generate a minimal, clean unified git diff "
            "patch to fix the bug. Output ONLY the raw unified diff patch (starting with `--- a/` and `+++ b/`)."
        )
        user_prompt = (
            f"### Bug Issue:\nTitle: {issue_title}\n\nDescription:\n{issue_body}\n\n"
            f"### Repository Context:\n{repo_context}\n\n"
            f"### Failing Reproduction Test:\n{failing_test_code}\n\n"
            f"### Test Failure Traceback:\n{failing_output}\n\n"
            "Generate a clean unified git diff patch that resolves the failure without introducing regressions."
        )
        content = self._call_api(system_prompt, user_prompt)
        return self._extract_diff(content)

    def refine_patch(
        self,
        previous_patch: str,
        error_output: str,
        repo_context: str,
    ) -> str:
        system_prompt = (
            "You are an autonomous software engineering agent. The previous patch failed tests. "
            "Refine the unified git diff to resolve the error. Output ONLY the raw unified diff."
        )
        user_prompt = (
            f"### Previous Patch Attempt:\n{previous_patch}\n\n"
            f"### Verification Error / Failure:\n{error_output}\n\n"
            f"### Repository Context:\n{repo_context}\n\n"
            "Provide the corrected unified git diff patch."
        )
        content = self._call_api(system_prompt, user_prompt)
        return self._extract_diff(content)

    @staticmethod
    def _extract_code(text: str) -> str:
        match = re.search(r"```(?:python|py)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    @staticmethod
    def _extract_diff(text: str) -> str:
        match = re.search(r"```(?:diff|patch)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()
