"""Abstract Syntax Tree (AST) symbol mapping and context pruning."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SymbolInfo(BaseModel):
    name: str
    kind: str  # "class", "function", "async_function"
    line_number: int
    docstring: Optional[str] = None
    args: List[str] = Field(default_factory=list)


class FileMetadata(BaseModel):
    rel_path: str
    symbols: List[SymbolInfo] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    total_lines: int = 0
    relevance_score: float = 0.0


class RepoMap:
    """Extracts structural AST signatures from repository files for LLM context optimization."""

    def __init__(self, root_dir: Path | str, ignore_dirs: Optional[List[str]] = None) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.ignore_dirs = set(ignore_dirs or [
            ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
            "build", "dist", ".egg-info", ".patchpilot_worktrees"
        ])
        self.files_map: Dict[str, FileMetadata] = {}

    def scan(self) -> Dict[str, FileMetadata]:
        """Scan all Python files in the repository and parse AST definitions."""
        self.files_map.clear()

        for py_path in self.root_dir.rglob("*.py"):
            # Check if inside ignored directories
            if any(ignored in py_path.parts for ignored in self.ignore_dirs):
                continue

            rel_path = str(py_path.relative_to(self.root_dir)).replace("\\", "/")
            metadata = self._parse_file(py_path, rel_path)
            if metadata:
                self.files_map[rel_path] = metadata

        return self.files_map

    def _parse_file(self, file_path: Path, rel_path: str) -> Optional[FileMetadata]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            # Skip invalid syntax files
            return None

        symbols: List[SymbolInfo] = []
        imports: List[str] = []

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                        args=args,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="class",
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
                # Methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_args = [a.arg for a in item.args.args]
                        symbols.append(
                            SymbolInfo(
                                name=f"{node.name}.{item.name}",
                                kind="method",
                                line_number=item.lineno,
                                docstring=ast.get_docstring(item),
                                args=m_args,
                            )
                        )
            elif isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        total_lines = len(content.splitlines())
        return FileMetadata(
            rel_path=rel_path,
            symbols=symbols,
            imports=imports,
            total_lines=total_lines,
        )

    def rank_relevance(self, query_terms: List[str], file_hints: List[str]) -> List[FileMetadata]:
        """Rank repository files based on query matches and direct file mentions."""
        ranked: List[FileMetadata] = []
        terms_lower = [t.lower() for t in query_terms if len(t) > 2]

        for rel_path, meta in self.files_map.items():
            score = 0.0
            path_lower = rel_path.lower()

            # Exact or partial file hint match
            for hint in file_hints:
                hint_clean = hint.replace("\\", "/").lower()
                if hint_clean in path_lower or path_lower in hint_clean:
                    score += 50.0

            # Symbol name matches
            for sym in meta.symbols:
                sym_lower = sym.name.lower()
                for term in terms_lower:
                    if term == sym_lower:
                        score += 15.0
                    elif term in sym_lower:
                        score += 5.0

            # Import matches
            for imp in meta.imports:
                for term in terms_lower:
                    if term in imp.lower():
                        score += 2.0

            meta.relevance_score = score
            ranked.append(meta)

        ranked.sort(key=lambda m: m.relevance_score, reverse=True)
        return ranked

    def generate_context_prompt(self, top_files: List[FileMetadata], max_files: int = 5) -> str:
        """Render a concise AST summary for the top relevant files."""
        lines = ["### Repository Map & Symbols:"]
        for meta in top_files[:max_files]:
            lines.append(f"\nFile: `{meta.rel_path}` (Total lines: {meta.total_lines})")
            for sym in meta.symbols:
                args_str = ", ".join(sym.args)
                lines.append(f"  - [{sym.kind}] {sym.name}({args_str}) at line {sym.line_number}")
        return "\n".join(lines)
