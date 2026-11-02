"""Pytest configuration and shared fixtures for PatchPilot tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
import pytest


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Creates a temporary, fully initialized Git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(repo_dir),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(repo_dir),
        check=True,
        capture_output=True,
    )

    # Create a sample python file
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    calc_file = src_dir / "calculator.py"
    calc_file.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    \"\"\"Add two numbers.\"\"\"\n"
        "    return a + b\n\n"
        "def divide(a: int, b: int) -> float:\n"
        "    \"\"\"Divide two numbers.\"\"\"\n"
        "    return a / b\n",
        encoding="utf-8",
    )

    # Create a tests directory with a passing test
    test_dir = repo_dir / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_calculator.py"
    test_file.write_text(
        "from src.calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo_dir),
        check=True,
        capture_output=True,
    )

    return repo_dir
