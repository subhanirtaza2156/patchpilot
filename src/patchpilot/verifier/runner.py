"""Test runner for executing pytest or unittest suites in isolated environments."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class TestExecutionResult(BaseModel):
    success: bool
    returncode: int
    stdout: str
    stderr: str
    passed_count: int = 0
    failed_count: int = 0
    error_summary: Optional[str] = None


class TestRunner:
    """Executes tests inside a target directory or worktree and parses outcomes."""

    @staticmethod
    def run_tests(
        workdir: Path | str,
        test_file: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> TestExecutionResult:
        """Run pytest on the target directory or specific test file."""
        workdir_path = Path(workdir).resolve()

        cmd = [sys.executable, "-m", "pytest", "-v"]
        if test_file:
            cmd.append(test_file)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(workdir_path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            return TestExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Test run timed out after {timeout_seconds} seconds.",
                error_summary="TimeoutExpired",
            )
        except Exception as exc:
            return TestExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                error_summary=str(exc),
            )

        # Parse test outcomes: e.g. "2 passed, 1 failed in 0.12s"
        passed_count = 0
        failed_count = 0

        pass_match = re.search(r"(\d+)\s+passed", stdout)
        if pass_match:
            passed_count = int(pass_match.group(1))

        fail_match = re.search(r"(\d+)\s+failed", stdout)
        if fail_match:
            failed_count = int(fail_match.group(1))

        # Extract failure section
        error_summary = None
        if "=== FAILURES ===" in stdout:
            parts = stdout.split("=== FAILURES ===")
            if len(parts) > 1:
                error_summary = parts[1].split("=== short test summary info ===")[0].strip()

        return TestExecutionResult(
            success=(returncode == 0),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            passed_count=passed_count,
            failed_count=failed_count,
            error_summary=error_summary,
        )
