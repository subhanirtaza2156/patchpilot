# Contributing to PatchPilot

First off, thank you for considering contributing to PatchPilot! It's people like you that make open source such a wonderful place to build.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/patchpilot.git
   cd patchpilot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install editable package with development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify the test suite passes:**
   ```bash
   pytest
   ```

## Pull Request Guidelines

1. **Branch Naming:**
   - `feat/feature-name`
   - `fix/bug-fix-name`
   - `docs/documentation-update`

2. **Commit Conventions:**
   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add AST symbol dependency mapper`
   - `fix: resolve git worktree path conflict on Windows`
   - `test: add unit test for verifier retry loop`
   - `docs: update architecture diagram in README`

3. **Code Style & Quality:**
   Run Ruff before submitting your PR:
   ```bash
   ruff check .
   ruff format .
   ```

4. **Testing:**
   Every new feature or bug fix must include corresponding tests in `tests/`.
