"""Isolated Git Worktree manager to guarantee zero side-effects during patch testing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class GitWorktreeManager:
    """Manages temporary Git worktrees so changes, tests, and diffs run in isolation."""

    def __init__(self, repo_dir: Path | str) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        self.worktree_base = self.repo_dir / ".patchpilot_worktrees"

    def is_git_repo(self) -> bool:
        """Check if target directory is a valid git repository."""
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )
        return res.returncode == 0

    def create_worktree(self, branch_name: str) -> Path:
        """Create a dedicated, isolated git worktree branch."""
        self.worktree_base.mkdir(parents=True, exist_ok=True)
        worktree_path = self.worktree_base / branch_name

        # Clean existing directory if leftover
        if worktree_path.exists():
            self.remove_worktree(branch_name)

        # Run git worktree add
        cmd = ["git", "worktree", "add", "-b", branch_name, str(worktree_path)]
        res = subprocess.run(
            cmd,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            # If branch already exists, checkout without -b
            cmd_existing = ["git", "worktree", "add", str(worktree_path), branch_name]
            res_existing = subprocess.run(
                cmd_existing,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
            )
            if res_existing.returncode != 0:
                raise RuntimeError(
                    f"Failed to create git worktree: {res.stderr}\n{res_existing.stderr}"
                )

        return worktree_path

    def remove_worktree(self, branch_name: str) -> None:
        """Prune and remove an isolated worktree and its directory."""
        worktree_path = self.worktree_base / branch_name

        # Git worktree remove
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )

        # Clean up directory if still present
        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

        # Delete temporary branch
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )

        # Prune worktrees metadata
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )

    def get_diff(self, worktree_path: Path) -> str:
        """Retrieve the git diff within the worktree."""
        res = subprocess.run(
            ["git", "diff"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
        )
        return res.stdout

    def apply_patch(self, worktree_path: Path, patch_text: str) -> Tuple[bool, str]:
        """Apply a unified diff patch to the worktree."""
        res = subprocess.run(
            ["git", "apply", "--ignore-whitespace", "-"],
            input=patch_text,
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return True, "Patch applied successfully."
        return False, res.stderr
