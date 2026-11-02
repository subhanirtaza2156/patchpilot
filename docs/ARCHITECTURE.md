# PatchPilot Architecture & Headless Bot Design

PatchPilot is an asynchronous, headless co-maintainer packaged as a native GitHub Action. It transforms raw natural-language issue reports into verified, test-backed Pull Requests without requiring the maintainer to open an editor or run local commands.

---

## Autonomous Asynchronous Sequence

```text
+-----------------------------------------------------------------------------------+
|                           EXTERNAL USER / CONTRIBUTOR                             |
|                        Opens GitHub Issue on Repository                           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v (Trigger: issues [opened, labeled])
+-----------------------------------------------------------------------------------+
|                        PATCHPILOT GITHUB ACTION RUNNER                            |
|                          (src/patchpilot/bot/github_bot.py)                       |
+-----------------------------------------------------------------------------------+
             |                                                  |
             v                                                  v
+--------------------------+                       +--------------------------------+
|  ISSUE PARSER & TRIAGE   |                       |  UNIVERSAL POLYGLOT SCANNER    |
| - Extracts tracebacks    |                       | (Python, TS/JS, Go, Rust, C++) |
| - Detects exception types|                       | - Maps symbols & signatures    |
| - Identifies target files|                       | - Ranks relevant source files  |
+--------------------------+                       +--------------------------------+
             \                                                 /
              \-----------------------+-----------------------/
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                              FRONTIER REASONING LAYER                             |
|          (OpenAI GPT-6.1 Sol / Google Gemini 4 Argon / DeepSeek-V4.1-Flash)       |
+-----------------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                         POLYGLOT TEST EXECUTION & SANDBOX                         |
|                 (pytest / jest / cargo test / go test in isolated branch)         |
| 1. Execute Reproduction Test -> MUST FAIL (RED baseline)                          |
| 2. Apply Unified Diff Patch -> Execute Test -> MUST PASS (GREEN state)            |
| 3. Execute Full Regression Suite -> MUST PASS (Zero side-effects)                 |
+-----------------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                           AUTOMATED PR & ISSUE COMMENT                            |
| 1. Pushes branch `patchpilot/fix-issue-#<id>`                                     |
| 2. Opens Pull Request: "fix: autonomously resolve issue #<id>"                    |
| 3. Comments on Issue with direct link to ready-to-merge PR                        |
+-----------------------------------------------------------------------------------+
```

---

## 1. Universal Polyglot Parsing
Rather than being limited to single-language ASTs, PatchPilot's `UniversalCodeScanner` parses structural declarations across:
- **Python:** `def`, `class`, `import`, type signatures.
- **TypeScript & JavaScript:** `function`, `class`, `interface`, `type`, ES imports, CommonJS requires.
- **Go:** `func`, `type ... struct`, `type ... interface`, module imports.
- **Rust:** `fn`, `struct`, `enum`, `impl`, `use` declarations.
- **C/C++:** Functions, structs, `#include` headers.

This gives PatchPilot the ability to triage mixed-language repositories (e.g. fullstack apps with Next.js frontend and Python/Go backend) with a unified relevance ranker.

---

## 2. Headless GitHub Actions Integration
Unlike local CLI tools that require active human steering, PatchPilot executes headlessly on GitHub compute:
- Uses `GITHUB_EVENT_PATH` to extract real-time issue payloads.
- Uses standard GitHub REST APIs via `httpx` to comment on issues and open verified PRs.
- Zero local dependencies or manual commands required from the maintainer.
