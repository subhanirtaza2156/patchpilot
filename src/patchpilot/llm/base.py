"""Base interface for LLM synthesis engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class LLMSynthesisResult(BaseModel):
    content: str
    model_name: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract interface defining required generation capabilities for autonomous patching."""

    @abstractmethod
    def generate_reproduction_test(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
    ) -> str:
        """Synthesize a standalone pytest file that reproduces the reported bug."""
        pass

    @abstractmethod
    def generate_patch(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
        failing_test_code: str,
        failing_output: str,
    ) -> str:
        """Generate a unified git diff patch addressing the failure."""
        pass

    @abstractmethod
    def refine_patch(
        self,
        previous_patch: str,
        error_output: str,
        repo_context: str,
    ) -> str:
        """Refine a previously attempted patch that failed verification."""
        pass
