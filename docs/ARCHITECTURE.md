# PatchPilot Architecture & Internal Design

PatchPilot is engineered to solve a core problem in autonomous software engineering: **bridging the gap between raw natural-language issue reports and deterministic, verified code patches.**

---

## High-Level System Architecture

```text
+-------------------------------------------------------------------------------+
|                                  USER / CLI                                   |
|               (patchpilot triage / patchpilot solve / CI Trigger)             |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                             CORE ORCHESTRATOR                                 |
|                       (src/patchpilot/core/orchestrator.py)                   |
+-------------------------------------------------------------------------------+
        |                                       |                      |
        v                                       v                      v
+------------------+                   +------------------+   +------------------+
|   ISSUE PARSER   |                   |  AST REPO MAP    |   |  GIT WORKTREE    |
| (issue_parser.py)|                   |  (repo_map.py)   |   |  (worktree.py)   |
| - Stack traces   |                   | - Symbol trees   |   | - Clean sandbox  |
| - Reproductions  |                   | - Dep graphs     |   | - Zero branch    |
| - Expected state |                   | - Token pruning  |   |   pollution      |
+------------------+                   +------------------+   +------------------+
        |                                       |                      |
        +-------------------+-------------------+                      |
                            |                                          |
                            v                                          v
+-------------------------------------------------------+   +------------------+
|                   LLM REASONING LAYER                 |   | VERIFIER RUNNER  |
|                 (src/patchpilot/llm/)                 |   | (verifier/loop.py|
| - OpenAI / Codex Client (BYOK)                        |-->| - Execute RED    |
| - Google Gemini Client (BYOK)                         |   | - Execute GREEN  |
| - Local Ollama Client (Offline)                       |   | - Check regression
+-------------------------------------------------------+   +------------------+
                            |                                          |
                            +-------------------+----------------------+
                                                v
+-------------------------------------------------------------------------------+
|                           VERIFIED PR ARTIFACT                                |
|        (Unified Git Diff + Reproduction Test + Explanation Markdown)          |
+-------------------------------------------------------------------------------+
```

---

## 1. Context Pruning via AST (Abstract Syntax Tree)
Standard AI coding agents fail on medium-to-large codebases because they either:
1. Dump the entire codebase into the LLM context, exhausting token limits and causing hallucinations.
2. Rely on naive grep/keyword search, missing underlying object references and class hierarchies.

`PatchPilot`'s **RepoMap** parses Python files into ASTs, extracting:
- Top-level classes, functions, and their signatures.
- Type annotations and docstring summaries.
- Import dependency trees.

When an issue mentions a function or error location, PatchPilot builds a focused **Context Subgraph**, reducing token overhead by **60% to 75%** while retaining critical type definitions.

---

## 2. The Deterministic Verification Loop (Red-to-Green)
A patch cannot be trusted simply because an LLM claims it fixed the problem. PatchPilot enforces a strict test verification loop:

1. **Reproduction Phase (RED):**
   The engine extracts the bug behavior and writes a reproduction test (`test_reproduce_<issue_id>.py`). It executes the test suite. If the test does not fail, the reproduction is considered invalid and refined.
2. **Patch Synthesis (GREEN):**
   Given the failing test and AST context, the LLM generates a targeted unified diff.
3. **Execution & Regression Check:**
   The patch is applied inside an isolated Git worktree. Both the reproduction test and the existing test suite are executed.
   - If reproduction passes AND full suite passes: **Verified Patch Generated**.
   - If tests fail: The failure traceback is fed back to the LLM for iterative refinement (up to max iterations).

---

## 3. Sandboxed Git Worktrees
To prevent corrupting the user's working directory or uncommitted changes, PatchPilot leverages native `git worktree`.
- A temporary worktree is created under `.patchpilot_worktrees/<branch-name>`.
- Code changes, test executions, and diff generations occur strictly in this isolated path.
- Upon completion or cancellation, the worktree is cleanly pruned.
