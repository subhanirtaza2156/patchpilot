"""Tests for TestRunner and VerificationLoop."""

from pathlib import Path
from patchpilot.git.worktree import GitWorktreeManager
from patchpilot.llm.mock_client import MockLLMClient
from patchpilot.verifier.loop import VerificationLoop
from patchpilot.verifier.runner import TestRunner


def test_test_runner_success(temp_git_repo: Path):
    result = TestRunner.run_tests(temp_git_repo)
    assert result.success is True
    assert result.passed_count >= 1
    assert result.failed_count == 0


def test_verification_loop_with_mock_client(temp_git_repo: Path):
    manager = GitWorktreeManager(temp_git_repo)
    branch = "patchpilot/verify-loop-test"
    worktree = manager.create_worktree(branch)

    try:
        # Mock LLM that provides a passing reproduction test and no-op patch
        passing_test = (
            "def test_simple_check():\n"
            "    assert 1 + 1 == 2\n"
        )
        mock_llm = MockLLMClient(canned_test=passing_test)

        loop = VerificationLoop(
            worktree_path=worktree,
            worktree_manager=manager,
            llm_client=mock_llm,
            max_iterations=1,
        )

        outcome = loop.execute(
            issue_title="Sample issue",
            issue_body="Description",
            repo_context="Context",
            initial_reproduction_test=passing_test,
        )

        assert outcome.iterations >= 1
    finally:
        manager.remove_worktree(branch)
