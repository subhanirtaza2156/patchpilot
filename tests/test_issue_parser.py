"""Tests for IssueParser."""

from patchpilot.core.issue_parser import IssueParser


def test_parse_simple_issue():
    title = "Fix ZeroDivisionError in calculator"
    body = "When passing 0 to divide(), it crashes with ZeroDivisionError."
    parsed = IssueParser.parse_text(title, body)

    assert parsed.title == title
    assert parsed.body == body
    assert "ZeroDivisionError" in parsed.error_types


def test_parse_stack_trace_and_file_mention():
    title = "Crash in data processing"
    body = (
        "Traceback (most recent call last):\n"
        '  File "src/math/solver.py", line 42, in solve\n'
        "    return 1 / value\n"
        "ZeroDivisionError: division by zero\n"
    )
    parsed = IssueParser.parse_text(title, body)

    assert len(parsed.stack_traces) == 1
    st = parsed.stack_traces[0]
    assert st.file_path == "src/math/solver.py"
    assert st.line_number == 42
    assert st.function_name == "solve"
    assert "src/math/solver.py" in parsed.referenced_files


def test_parse_code_blocks():
    title = "Incorrect behavior"
    body = (
        "Here is the reproduction code:\n"
        "```python\n"
        "import math\n"
        "assert math.sqrt(4) == 2\n"
        "```\n"
    )
    parsed = IssueParser.parse_text(title, body)

    assert len(parsed.code_snippets) == 1
    assert "assert math.sqrt(4) == 2" in parsed.code_snippets[0]
