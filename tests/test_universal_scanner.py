"""Tests for UniversalCodeScanner supporting polyglot codebases."""

from pathlib import Path
from patchpilot.core.universal_scanner import UniversalCodeScanner


def test_universal_scanner_multi_language(tmp_path: Path):
    # Python file
    py_file = tmp_path / "app.py"
    py_file.write_text("def solve_problem(x: int):\n    return x * 2\n", encoding="utf-8")

    # TypeScript file
    ts_file = tmp_path / "handler.ts"
    ts_file.write_text(
        "export async function processRequest(req: Request) {\n"
        "    return true;\n"
        "}\n",
        encoding="utf-8",
    )

    # Go file
    go_file = tmp_path / "main.go"
    go_file.write_text(
        "package main\n\n"
        "type UserConfig struct {\n"
        "    Name string\n"
        "}\n\n"
        "func StartServer() {\n}\n",
        encoding="utf-8",
    )

    scanner = UniversalCodeScanner(tmp_path)
    files_map = scanner.scan()

    assert "app.py" in files_map
    assert files_map["app.py"].language == "python"
    assert any(s.name == "solve_problem" for s in files_map["app.py"].symbols)

    assert "handler.ts" in files_map
    assert files_map["handler.ts"].language == "typescript"
    assert any(s.name == "processRequest" for s in files_map["handler.ts"].symbols)

    assert "main.go" in files_map
    assert files_map["main.go"].language == "go"
    assert any(s.name == "UserConfig" for s in files_map["main.go"].symbols)
    assert any(s.name == "StartServer" for s in files_map["main.go"].symbols)
