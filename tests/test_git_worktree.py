"""Tests for GitWorktreeManager."""

from pathlib import Path
from patchpilot.git.worktree import GitWorktreeManager


def test_is_git_repo(temp_git_repo: Path):
    manager = GitWorktreeManager(temp_git_repo)
    assert manager.is_git_repo() is True


def test_create_and_remove_worktree(temp_git_repo: Path):
    manager = GitWorktreeManager(temp_git_repo)
    branch = "patchpilot/test-branch-1"

    worktree_path = manager.create_worktree(branch)
    assert worktree_path.exists()
    assert (worktree_path / "src" / "calculator.py").exists()

    manager.remove_worktree(branch)
    assert not worktree_path.exists()
