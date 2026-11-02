"""Universal multi-language structural code scanner supporting Python, JS/TS, Go, Rust, and C/C++."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class UniversalSymbol(BaseModel):
    name: str
    kind: str  # function, class, struct, interface, method
    line_number: int
    signature: Optional[str] = None


class UniversalFileMetadata(BaseModel):
    rel_path: str
    language: str
    symbols: List[UniversalSymbol] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    total_lines: int = 0
    relevance_score: float = 0.0


class UniversalCodeScanner:
    """Multi-language parser extracting functions, structs, classes, and imports across polyglot repos."""

    EXTENSION_MAP = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c_header",
    }

    # Language Pattern Matchers
    PATTERNS = {
        "python": {
            "function": re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)", re.MULTILINE),
            "class": re.compile(r"^\s*class\s+([a-zA-Z0-9_]+)(?:\((.*?)\))?:", re.MULTILINE),
            "import": re.compile(r"^\s*(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+))", re.MULTILINE),
        },
        "typescript": {
            "function": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)", re.MULTILINE),
            "class": re.compile(r"(?:export\s+)?(?:abstract\s+)?class\s+([a-zA-Z0-9_]+)", re.MULTILINE),
            "interface": re.compile(r"(?:export\s+)?interface\s+([a-zA-Z0-9_]+)", re.MULTILINE),
            "import": re.compile(r"import\s+.*?from\s+['\"](.*?)['\"]", re.MULTILINE),
        },
        "javascript": {
            "function": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)", re.MULTILINE),
            "class": re.compile(r"(?:export\s+)?class\s+([a-zA-Z0-9_]+)", re.MULTILINE),
            "import": re.compile(r"(?:import\s+.*?from\s+['\"](.*?)['\"]|require\(['\"](.*?)['\"]\))", re.MULTILINE),
        },
        "go": {
            "function": re.compile(r"^func\s+(?:\(.*?\)\s+)?([a-zA-Z0-9_]+)\s*\(", re.MULTILINE),
            "struct": re.compile(r"^type\s+([a-zA-Z0-9_]+)\s+struct\b", re.MULTILINE),
            "interface": re.compile(r"^type\s+([a-zA-Z0-9_]+)\s+interface\b", re.MULTILINE),
            "import": re.compile(r"\"([a-zA-Z0-9_./-]+)\"", re.MULTILINE),
        },
        "rust": {
            "function": re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)\s*\(", re.MULTILINE),
            "struct": re.compile(r"^\s*(?:pub\s+)?struct\s+([a-zA-Z0-9_]+)", re.MULTILINE),
            "enum": re.compile(r"^\s*(?:pub\s+)?enum\s+([a-zA-Z0-9_]+)", re.MULTILINE),
            "import": re.compile(r"use\s+([a-zA-Z0-9_:]+);", re.MULTILINE),
        },
    }

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.ignore_dirs = {
            ".git", "node_modules", "target", "vendor", ".venv", "venv",
            "__pycache__", ".pytest_cache", "dist", "build", ".patchpilot_worktrees"
        }
        self.files_map: Dict[str, UniversalFileMetadata] = {}

    def scan(self) -> Dict[str, UniversalFileMetadata]:
        self.files_map.clear()

        for ext, lang in self.EXTENSION_MAP.items():
            for file_path in self.root_dir.rglob(f"*{ext}"):
                if any(ignored in file_path.parts for ignored in self.ignore_dirs):
                    continue

                rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
                meta = self._parse_file(file_path, rel_path, lang)
                if meta:
                    self.files_map[rel_path] = meta

        return self.files_map

    def _parse_file(self, file_path: Path, rel_path: str, lang: str) -> Optional[UniversalFileMetadata]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        symbols: List[UniversalSymbol] = []
        imports: List[str] = []
        lang_patterns = self.PATTERNS.get(lang, self.PATTERNS.get("javascript", {}))

        lines = content.splitlines()

        for kind, pattern in lang_patterns.items():
            if kind == "import":
                for match in pattern.finditer(content):
                    imp = match.group(1) or (match.group(2) if match.lastindex and match.lastindex >= 2 else None)
                    if imp:
                        imports.append(imp)
            else:
                for match in pattern.finditer(content):
                    sym_name = match.group(1)
                    line_no = content[:match.start()].count("\n") + 1
                    sig = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
                    symbols.append(
                        UniversalSymbol(
                            name=sym_name,
                            kind=kind,
                            line_number=line_no,
                            signature=sig,
                        )
                    )

        return UniversalFileMetadata(
            rel_path=rel_path,
            language=lang,
            symbols=symbols,
            imports=list(set(imports)),
            total_lines=len(lines),
        )

    def rank_relevance(self, query_terms: List[str], file_hints: List[str]) -> List[UniversalFileMetadata]:
        ranked: List[UniversalFileMetadata] = []
        terms_lower = [t.lower() for t in query_terms if len(t) > 2]

        for rel_path, meta in self.files_map.items():
            score = 0.0
            path_lower = rel_path.lower()

            for hint in file_hints:
                hint_clean = hint.replace("\\", "/").lower()
                if hint_clean in path_lower or path_lower in hint_clean:
                    score += 50.0

            for sym in meta.symbols:
                sym_lower = sym.name.lower()
                for term in terms_lower:
                    if term == sym_lower:
                        score += 20.0
                    elif term in sym_lower:
                        score += 6.0

            for imp in meta.imports:
                for term in terms_lower:
                    if term in imp.lower():
                        score += 2.0

            meta.relevance_score = score
            ranked.append(meta)

        ranked.sort(key=lambda m: m.relevance_score, reverse=True)
        return ranked

    def generate_context_prompt(self, top_files: List[UniversalFileMetadata], max_files: int = 5) -> str:
        lines = ["### Multi-Language Codebase Context:"]
        for meta in top_files[:max_files]:
            lines.append(f"\nFile: `{meta.rel_path}` (Language: {meta.language}, Lines: {meta.total_lines})")
            for sym in meta.symbols[:10]:
                sig_str = f"({sym.signature})" if sym.signature else ""
                lines.append(f"  - [{sym.kind}] {sym.name}{sig_str} at line {sym.line_number}")
        return "\n".join(lines)
