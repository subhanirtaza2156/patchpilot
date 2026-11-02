"""Tests for RepoMap AST parsing and ranking."""

from pathlib import Path
from patchpilot.core.repo_map import RepoMap


def test_repo_map_scan(temp_git_repo: Path):
    mapper = RepoMap(temp_git_repo)
    files_map = mapper.scan()

    assert "src/calculator.py" in files_map
    calc_meta = files_map["src/calculator.py"]
    assert calc_meta.total_lines > 0
    symbols = {s.name for s in calc_meta.symbols}
    assert "add" in symbols
    assert "divide" in symbols


def test_repo_map_rank_relevance(temp_git_repo: Path):
    mapper = RepoMap(temp_git_repo)
    mapper.scan()

    ranked = mapper.rank_relevance(
        query_terms=["divide", "ZeroDivisionError"],
        file_hints=["src/calculator.py"],
    )

    assert len(ranked) > 0
    top_file = ranked[0]
    assert top_file.rel_path == "src/calculator.py"
    assert top_file.relevance_score > 0


def test_repo_map_generate_context_prompt(temp_git_repo: Path):
    mapper = RepoMap(temp_git_repo)
    mapper.scan()
    ranked = mapper.rank_relevance(query_terms=["add"], file_hints=[])
    prompt = mapper.generate_context_prompt(ranked)

    assert "Repository Map & Symbols" in prompt
    assert "calculator.py" in prompt
    assert "add(a, b)" in prompt
