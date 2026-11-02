"""Polyglot test execution runner supporting Python (pytest), Node.js (jest/vitest), Rust (cargo), and Go."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class MultiRunnerResult(BaseModel):
    success: bool
    ecosystem: str
    command: List[str]
    stdout: str
    stderr: str
    returncode: int


class PolyglotTestRunner:
    """Detects project build files and executes native test suites in isolated sandboxes."""

    @classmethod
    def detect_ecosystem(cls, workdir: Path) -> str:
        if (workdir / "Cargo.toml").exists():
            return "rust"
        if (workdir / "go.mod").exists():
            return "go"
        if (workdir / "package.json").exists():
            return "nodejs"
        return "python"

    @classmethod
    def run(cls, workdir: Path, timeout: int = 120) -> MultiRunnerResult:
        ecosystem = cls.detect_ecosystem(workdir)

        if ecosystem == "rust":
            cmd = ["cargo", "test"]
        elif ecosystem == "go":
            cmd = ["go", "test", "./..."]
        elif ecosystem == "nodejs":
            cmd = ["npm", "test", "--", "--passWithNoTests"]
        else:
            cmd = ["python", "-m", "pytest", "-v"]

        try:
            res = subprocess.run(
                cmd,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return MultiRunnerResult(
                success=(res.returncode == 0),
                ecosystem=ecosystem,
                command=cmd,
                stdout=res.stdout,
                stderr=res.stderr,
                returncode=res.returncode,
            )
        except Exception as exc:
            return MultiRunnerResult(
                success=False,
                ecosystem=ecosystem,
                command=cmd,
                stdout="",
                stderr=str(exc),
                returncode=-1,
            )
