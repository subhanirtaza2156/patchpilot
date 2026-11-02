"""Tests for PatchPilot CLI commands."""

from pathlib import Path
from typer.testing import CliRunner
from patchpilot.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "PatchPilot" in result.stdout


def test_cli_scan(temp_git_repo: Path):
    result = runner.invoke(app, ["scan", str(temp_git_repo)])
    assert result.exit_code == 0
    assert "AST Repository Index" in result.stdout


def test_cli_triage(temp_git_repo: Path):
    result = runner.invoke(
        app,
        [
            "triage",
            "Fix ZeroDivisionError in calculator.py",
            "-b",
            "Crashing on zero",
            "-p",
            str(temp_git_repo),
        ],
    )
    assert result.exit_code == 0
    assert "Top Relevant Code Files" in result.stdout
