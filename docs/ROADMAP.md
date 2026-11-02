# PatchPilot Roadmap & Milestones

This document tracks upcoming releases, technical milestones, and our long-term vision to build the definitive autonomous co-maintainer for open source.

---

## 🎯 v0.1.0 — Foundation & CLI Core (Current Release)
- [x] Modern PEP 621 Python architecture with Hatchling.
- [x] AST-based symbol indexing and dependency mapping.
- [x] Structured issue parsing (stack traces, reproduction steps, expected behavior).
- [x] Git Worktree isolation for zero-side-effect patching.
- [x] Deterministic Red-to-Green test verification loop.
- [x] Multi-provider LLM interface (OpenAI/Codex, Gemini, Ollama, Mock test engine).
- [x] Rich terminal interface with progress bars and tables.

---

## 🚀 v0.2.0 — GitHub Actions & Automated PR Bot
- [ ] Native GitHub Action container: runs on `issues: [opened, labeled]`.
- [ ] Automatic comment generation on issues with reproduction tests.
- [ ] One-click Draft PR creation with test and patch.
- [ ] Token budgeting and smart context compression cache.

---

## 🧠 v0.3.0 — SWE-bench Verified Benchmark Suite
- [ ] Automated SWE-bench Lite evaluation runner.
- [ ] Dockerized micro-sandboxes for safe execution of arbitrary test suites.
- [ ] Support for JavaScript/TypeScript (via Tree-sitter) and Rust codebases.
- [ ] Fine-tuned prompt harnesses for OpenAI o-series & Codex models.

---

## 🌐 v0.4.0 — Community Hub & Collaborative Review
- [ ] Webhook integration for self-hosted GitLab and Gitea instances.
- [ ] Interactive terminal debugger (`patchpilot debug <patch-id>`).
- [ ] Automated regression risk scoring.
