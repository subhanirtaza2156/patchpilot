"""Local Ollama model provider for PatchPilot supporting DeepSeek-V4.1 and Qwen."""

from __future__ import annotations

import re
from typing import Optional
import httpx
from patchpilot.llm.base import BaseLLMClient


class OllamaLLMClient(BaseLLMClient):
    """Client for locally running models via Ollama (DeepSeek-V4.1-Flash, Qwen 2.5 Coder)."""

    def __init__(
        self,
        model: str = "deepseek-v4.1-flash",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _call_api(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["response"]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. Please ensure Ollama is running."
            )

    def generate_reproduction_test(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
    ) -> str:
        prompt = (
            "Write a self-contained pytest reproduction file for the reported bug. "
            "Output ONLY the raw Python code block enclosed in ```python.\n\n"
            f"Bug Title: {issue_title}\n\nDescription:\n{issue_body}\n\nContext:\n{repo_context}\n"
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
            "Generate a unified git diff patch to fix the bug. "
            "Output ONLY the unified diff patch enclosed in ```diff.\n\n"
            f"Bug: {issue_title}\n\nTraceback:\n{failing_output}\n\nContext:\n{repo_context}\n"
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
            "The previous patch failed tests. Provide a corrected unified git diff patch enclosed in ```diff.\n\n"
            f"Attempt:\n{previous_patch}\n\nError:\n{error_output}\n"
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
