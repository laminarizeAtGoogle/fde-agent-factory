# Repository Guidelines & Agent Instructions

This document defines repository-level standards and conventions for engineers and AI agents working in this workspace.

---

## 1. Git Commit & PR Message Guidelines (Context Preservation)

To ensure full context is preserved across pull request merges and permanently retained in `main`'s git history:

### A. Multi-Line Commits (No Single-Line Commits)
Never create single-line commits for non-trivial changes. Every commit must have an informative subject line AND an extended body (commit comments) formatted as follows:

```bash
git commit -m "<type>(<scope>): <concise subject>" \
  -m "Why:
- Provide the motivation, problem statement, or requirement.

What:
- Bulleted list of specific files, components, and changes made.

Verification:
- How this change was tested and validated (unit tests, manual testing, hook passes)."
```

### B. Pull Request Context Preservation
- The repository merge settings are configured with:
  - `merge_commit_title: "PR_TITLE"`
  - `merge_commit_message: "PR_BODY"`
  - `squash_merge_commit_title: "PR_TITLE"`
  - `squash_merge_commit_message: "PR_BODY"`
- Because GitHub embeds the pull request body (`PR_BODY`) directly into the merge commit on `main`, every PR description **must** be comprehensive and contain:
  - **Summary**: High-level intent.
  - **Changes Included**: Itemized technical breakdown.
  - **Review & Discussion Decisions**: Any key decisions or comments discussed during review.
  - **Test Coverage**: Explicit test results.

---

## 2. Architecture Documentation & Google OKF Standard

- **Canonical Architecture Platform**: All system designs and infrastructure topologies must use **Mermaid** diagrams (`mermaid` code blocks in [`docs/architecture.md`](docs/architecture.md) and [`docs/architecture_diagram.mmd`](docs/architecture_diagram.mmd)).
- **Declarative Models**: The source of truth is [`docs/architecture.md`](docs/architecture.md) and [`docs/architecture_diagram.mmd`](docs/architecture_diagram.mmd).
- **Prohibited**: Markdown ASCII box drawings (`+---+`, `|   |`) are strictly banned in architecture documentation.
- **Google OKF Knowledge Base**: Every architectural component must have an entry in [`docs/knowledge_base/`](docs/knowledge_base/) conforming to [`docs/knowledge_base/OKF_SPEC.md`](docs/knowledge_base/OKF_SPEC.md).

---

## 3. Pre-Push Lifecycle Hooks

- Prior to `git push`, the repository runs:
  1. `git-push-sanitization-gate`: Scans for leaked credentials, cookies, JWTs, and API keys.
  2. `git-push-architecture-docs-gate`: Executes `/update-architecture-docs` subagent to synchronize the Mermaid diagram and OKF Knowledge Base before pushing.
