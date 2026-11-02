"""Security Guardrails, Prompt Injection Defense, and Diff Boundary Enforcement for PatchPilot."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple
from pydantic import BaseModel


class SecurityScanResult(BaseModel):
    is_safe: bool
    violations: List[str] = []
    sanitized_text: str = ""


class SecurityGuard:
    """Enterprise-grade security gatekeeper protecting against prompt injection, RCE, and secret leakage."""

    # Sensitive paths that NO automated patch is ever allowed to touch
    BLOCKED_PATH_PATTERNS = [
        re.compile(r"^\.github/.*", re.IGNORECASE),
        re.compile(r"^.*(?:\.env|\.secrets|credentials|id_rsa|id_ed25519|.*\.pem|.*\.key)$", re.IGNORECASE),
        re.compile(r"^.*(?:\.git/|passwd|shadow|\.bashrc|\.zshrc).*$", re.IGNORECASE),
    ]

    # Malicious injection signatures in issues
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"disregard\s+(?:all\s+)?(?:system|developer)\s+prompts", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(?:an?\s+)?unrestricted", re.IGNORECASE),
        re.compile(r"printenv|env\s*\|\s*curl|curl\s+.*-(?:d|F)\s+.*KEY", re.IGNORECASE),
        re.compile(r"(?:rm\s+-rf\s+[/~]|mkfs|dd\s+if=)", re.IGNORECASE),
    ]

    # Dangerous syscalls inside generated reproduction test files
    DANGEROUS_CODE_PATTERNS = [
        re.compile(r"\b(?:os\.system|subprocess\.Popen|subprocess\.call|subprocess\.run)\b"),
        re.compile(r"\b(?:eval|exec|__import__)\b"),
        re.compile(r"\b(?:socket\.socket|urllib\.request|requests\.post|httpx\.post)\b"),
        re.compile(r"\b(?:pty\.spawn|shutil\.rmtree\s*\(\s*['\"]/['\"])"),
    ]

    @classmethod
    def sanitize_issue_input(cls, title: str, body: str) -> SecurityScanResult:
        """Inspect issue input for indirect prompt injection and destructive payloads."""
        combined = f"{title}\n{body}"
        violations = []

        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if pattern.search(combined):
                violations.append(f"Prompt Injection detected: matches `{pattern.pattern}`")

        # Sanitize zero-width characters and control codes
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", combined)

        return SecurityScanResult(
            is_safe=(len(violations) == 0),
            violations=violations,
            sanitized_text=sanitized,
        )

    @classmethod
    def validate_reproduction_test(cls, test_code: str) -> Tuple[bool, List[str]]:
        """Block tests attempting network exfiltration, arbitrary shell execution, or destructive filesystem calls."""
        violations = []

        for pattern in cls.DANGEROUS_CODE_PATTERNS:
            match = pattern.search(test_code)
            if match:
                violations.append(f"Dangerous call forbidden in reproduction test: `{match.group(0)}`")

        return (len(violations) == 0), violations

    @classmethod
    def validate_patch_diff(cls, diff_text: str) -> Tuple[bool, List[str]]:
        """Ensure unified git diff does not modify sensitive workflows, secrets, or configuration files."""
        violations = []
        # Extract target filenames from diff (e.g. +++ b/path/to/file)
        target_files = re.findall(r"^\+\+\+\s+b/(.*)$", diff_text, re.MULTILINE)

        if not target_files:
            # Check for standard diff markers
            target_files = re.findall(r"^---\s+a/(.*)$", diff_text, re.MULTILINE)

        for filepath in target_files:
            clean_path = filepath.strip().replace("\\", "/")

            # Check directory traversal attempts
            if ".." in clean_path:
                violations.append(f"Path traversal detected in patch diff: `{clean_path}`")

            # Check sensitive/privileged paths
            for pattern in cls.BLOCKED_PATH_PATTERNS:
                if pattern.match(clean_path):
                    violations.append(f"Modification to protected path strictly forbidden: `{clean_path}`")

        # Cap max lines modified to prevent Denial-of-Service / Code Bloat
        diff_lines = diff_text.splitlines()
        if len(diff_lines) > 500:
            violations.append(f"Patch diff exceeds maximum allowed safety threshold (500 lines). Length: {len(diff_lines)}")

        return (len(violations) == 0), violations
