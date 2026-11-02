"""Red-to-Green deterministic verification loop with Security Guardrails."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from patchpilot.git.worktree import GitWorktreeManager
from patchpilot.llm.base import BaseLLMClient
from patchpilot.security.guardrails import SecurityGuard
from patchpilot.verifier.runner import TestRunner


class VerificationOutcome(BaseModel):
    success: bool
    iterations: int
    final_diff: str = ""
    reproduction_test: str = ""
    error_message: Optional[str] = None
    step_logs: List[str] = []


class VerificationLoop:
    """Orchestrates iterative Red-to-Green testing against an isolated git worktree with strict security bounds."""

    def __init__(
        self,
        worktree_path: Path,
        worktree_manager: GitWorktreeManager,
        llm_client: BaseLLMClient,
        max_iterations: int = 3,
    ) -> None:
        self.worktree_path = Path(worktree_path)
        self.git_manager = worktree_manager
        self.llm = llm_client
        self.max_iterations = max_iterations

    def execute(
        self,
        issue_title: str,
        issue_body: str,
        repo_context: str,
        initial_reproduction_test: str,
    ) -> VerificationOutcome:
        logs: List[str] = []
        logs.append("Security Check: Validating reproduction test safety")

        # 0. AppSec Gate: Validate reproduction test for dangerous syscalls
        is_safe_test, test_violations = SecurityGuard.validate_reproduction_test(initial_reproduction_test)
        if not is_safe_test:
            error_msg = f"Security Violation in test code: {', '.join(test_violations)}"
            logs.append(f"CRITICAL: {error_msg}")
            return VerificationOutcome(
                success=False,
                iterations=0,
                error_message=error_msg,
                step_logs=logs,
            )

        logs.append("Phase 1: Establishing RED baseline (reproduction verification)")

        # 1. Place the reproduction test in the worktree
        test_file_name = "test_patchpilot_repro.py"
        test_file_path = self.worktree_path / "tests" / test_file_name
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text(initial_reproduction_test, encoding="utf-8")

        # 2. Run reproduction test — it should fail on buggy code
        baseline_result = TestRunner.run_tests(self.worktree_path, test_file=f"tests/{test_file_name}")
        if baseline_result.success:
            logs.append("Warning: Initial reproduction test passed unexpectedly. Proceeding with caution.")
        else:
            logs.append(f"Confirmed RED state: {baseline_result.error_summary or 'Test failed as expected'}")

        # 3. Iterative Patch Synthesis & Verification Loop
        current_patch = ""
        current_error = baseline_result.error_summary or baseline_result.stdout

        for attempt in range(1, self.max_iterations + 1):
            logs.append(f"Phase 2 [Attempt {attempt}/{self.max_iterations}]: Synthesizing patch diff")

            if attempt == 1:
                current_patch = self.llm.generate_patch(
                    issue_title=issue_title,
                    issue_body=issue_body,
                    repo_context=repo_context,
                    failing_test_code=initial_reproduction_test,
                    failing_output=current_error,
                )
            else:
                logs.append("Refining patch based on previous failure...")
                current_patch = self.llm.refine_patch(
                    previous_patch=current_patch,
                    error_output=current_error,
                    repo_context=repo_context,
                )

            # Security Gate: Validate patch diff does NOT touch sensitive paths (.github, .env, etc.)
            is_safe_diff, diff_violations = SecurityGuard.validate_patch_diff(current_patch)
            if not is_safe_diff:
                error_msg = f"Security Violation: {', '.join(diff_violations)}"
                logs.append(f"SECURITY BLOCKED: {error_msg}")
                current_error = error_msg
                continue

            # Apply patch
            applied, apply_msg = self.git_manager.apply_patch(self.worktree_path, current_patch)
            if not applied:
                logs.append(f"Patch apply failed: {apply_msg}")
                current_error = f"Git apply failed: {apply_msg}"
                continue

            # Run reproduction test
            repro_run = TestRunner.run_tests(self.worktree_path, test_file=f"tests/{test_file_name}")
            if not repro_run.success:
                logs.append(f"Reproduction test failed with attempt {attempt}")
                current_error = repro_run.error_summary or repro_run.stdout
                continue

            # Run full test suite for regression verification
            full_suite_run = TestRunner.run_tests(self.worktree_path)
            if full_suite_run.success:
                logs.append("Phase 3: GREEN state achieved! All tests passed and security bounds verified.")
                final_diff = self.git_manager.get_diff(self.worktree_path)
                return VerificationOutcome(
                    success=True,
                    iterations=attempt,
                    final_diff=final_diff,
                    reproduction_test=initial_reproduction_test,
                    step_logs=logs,
                )
            else:
                logs.append(f"Regression detected in full test suite: {full_suite_run.error_summary}")
                current_error = f"Regression: {full_suite_run.error_summary}"

        logs.append(f"Exhausted {self.max_iterations} attempts without reaching clean GREEN state.")
        return VerificationOutcome(
            success=False,
            iterations=self.max_iterations,
            final_diff=self.git_manager.get_diff(self.worktree_path),
            reproduction_test=initial_reproduction_test,
            error_message="Verification loop exhausted maximum iterations.",
            step_logs=logs,
        )
