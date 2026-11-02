"""Google Gemini API provider for PatchPilot supporting Gemini 4 Argon & Carbon."""

from __future__ import annotations

import os
import re
from typing import Optional
import httpx
from patchpilot.llm.base import BaseLLMClient


class GeminiLLMClient(BaseLLMClient):
    """Client for frontier Google Gemini models (Gemini 4 Argon, Gemini 4 Carbon, Gemini 2.5)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-4-argon",
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model

    def _call_api(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your environment or pass --api-key."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }

        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def generate_reproduction_test(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
    ) -> str:
        prompt = (
            "You are an expert Python test engineer. Write a self-contained pytest reproduction "
            "file for the reported bug. Output ONLY the raw Python code block enclosed in ```python.\n\n"
            f"### Bug Issue:\nTitle: {issue_title}\n\nDescription:\n{issue_body}\n\n"
            f"### Repository Context:\n{repo_context}\n"
        )
        content = self._call_api(prompt)
        return self._extract_code(content)

    def generate_patch(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
        failing_test_code: str,
        failing_output: str,
    ) -> str:
        prompt = (
            "You are an autonomous software engineering agent. Generate a minimal, clean unified git diff "
            "patch to fix the bug. Output ONLY the raw unified diff patch (starting with `--- a/` and `+++ b/`).\n\n"
            f"### Bug Issue:\nTitle: {issue_title}\n\nDescription:\n{issue_body}\n\n"
            f"### Repository Context:\n{repo_context}\n\n"
            f"### Failing Reproduction Test:\n{failing_test_code}\n\n"
            f"### Test Failure Traceback:\n{failing_output}\n"
        )
        content = self._call_api(prompt)
        return self._extract_diff(content)

    def refine_patch(
        self,
        previous_patch: str,
        error_output: str,
        repo_context: str,
    ) -> str:
        prompt = (
            "The previous patch failed tests. Refine the unified git diff to resolve the error. "
            "Output ONLY the raw unified diff patch.\n\n"
            f"### Previous Patch Attempt:\n{previous_patch}\n\n"
            f"### Verification Error:\n{error_output}\n\n"
            f"### Repository Context:\n{repo_context}\n"
        )
        content = self._call_api(prompt)
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
