"""Tests for Google Antigravity Agent Engine."""

from pathlib import Path
from patchpilot.agents.antigravity_engine import AntigravityAgentEngine


def test_antigravity_engine_availability(temp_git_repo: Path):
    engine = AntigravityAgentEngine(temp_git_repo)
    assert engine.is_available() is True


def test_antigravity_tools_construction(temp_git_repo: Path):
    engine = AntigravityAgentEngine(temp_git_repo)
    tools = engine.build_tools(temp_git_repo)

    assert len(tools) == 3
    tool_names = {t.__name__ for t in tools}
    assert "scan_codebase_symbols" in tool_names
    assert "run_isolated_test" in tool_names
    assert "audit_diff_security" in tool_names

    # Test audit_diff_security directly
    audit_func = next(t for t in tools if t.__name__ == "audit_diff_security")
    safe_res = audit_func("--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1 +1 @@\n+x = 1")
    assert "SECURITY PASSED" in safe_res

    hacked_res = audit_func("--- a/.github/workflows/ci.yml\n+++ b/.github/workflows/ci.yml\n+hacked")
    assert "SECURITY BLOCKED" in hacked_res
