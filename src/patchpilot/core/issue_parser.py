"""Issue parser for extracting reproduction hints, stack traces, and target files."""

from __future__ import annotations

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class StackTraceFrame(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    code_context: Optional[str] = None


class ParsedIssue(BaseModel):
    title: str
    body: str
    issue_number: Optional[int] = None
    url: Optional[str] = None
    stack_traces: List[StackTraceFrame] = Field(default_factory=list)
    code_snippets: List[str] = Field(default_factory=list)
    referenced_files: List[str] = Field(default_factory=list)
    error_types: List[str] = Field(default_factory=list)


class IssueParser:
    """Parses bug reports and issues into structured metadata for autonomous patching."""

    # Traceback regex pattern matching: File ".../file.py", line 123, in func_name
    TRACEBACK_PATTERN = re.compile(
        r'File\s+["\'](?P<file>[^"\']+\.py)["\'],\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>\w+))?',
        re.MULTILINE,
    )

    # Markdown code blocks
    CODE_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

    # Python exception names: ValueError, KeyError, ZeroDivisionError, etc.
    EXCEPTION_PATTERN = re.compile(
        r"\b([A-Z][a-zA-Z0-9]*(?:Error|Exception|Warning|Fault))\b"
    )

    # File mentions: e.g. path/to/module.py
    FILE_MENTION_PATTERN = re.compile(
        r"\b(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_-]+\.py\b"
    )

    @classmethod
    def parse_text(cls, title: str, body: str, url: Optional[str] = None) -> ParsedIssue:
        """Parse raw issue title and markdown body into structured metadata."""
        full_text = f"{title}\n{body}"

        # 1. Extract Stack Traces
        stack_traces: List[StackTraceFrame] = []
        for match in cls.TRACEBACK_PATTERN.finditer(full_text):
            stack_traces.append(
                StackTraceFrame(
                    file_path=match.group("file"),
                    line_number=int(match.group("line")),
                    function_name=match.group("func"),
                )
            )

        # 2. Extract Code Snippets
        code_snippets: List[str] = []
        for match in cls.CODE_BLOCK_PATTERN.finditer(body):
            snippet = match.group(1).strip()
            if snippet:
                code_snippets.append(snippet)

        # 3. Extract Referenced Files
        referenced_files: set[str] = set()
        for match in cls.FILE_MENTION_PATTERN.finditer(full_text):
            referenced_files.add(match.group(0))
        for st in stack_traces:
            referenced_files.add(st.file_path)

        # 4. Extract Exception Types
        error_types = list(set(cls.EXCEPTION_PATTERN.findall(full_text)))

        # Extract issue number from title/url if available
        issue_number = None
        if url:
            num_match = re.search(r"/issues/(\d+)", url)
            if num_match:
                issue_number = int(num_match.group(1))

        return ParsedIssue(
            title=title.strip(),
            body=body.strip(),
            issue_number=issue_number,
            url=url,
            stack_traces=stack_traces,
            code_snippets=code_snippets,
            referenced_files=sorted(list(referenced_files)),
            error_types=sorted(error_types),
        )
