---
name: fde-git-push
description: "Governing version control operations: audits git diffs, enforces zero-trust security gates on staged files, checks README alignment, and drafts professional Conventional Commit messages."
---

# Git Push Skill (`fde-git-push`)

Use this skill to guide the agent in safely, cleanly, and professionally staging, committing, and pushing code changes in the workspace.

---

## 1. Zero-Trust Security Gate (Pre-Commit Audit)

Before staging or committing any files, the agent **MUST** execute a strict security audit:
1. **Block List**: Under no circumstances should the following files be staged or committed:
   - `.env` or `.env.local` (active local configurations).
   - Any file containing raw credentials, API keys (`AIzaSy...`), OAuth tokens (`ya29...`), GitHub PATs (`ghp_...`), private keys, or OAuth client secrets.
   - Temporary logs, diagnostic dumps, scratch scripts, or build artifacts (e.g., under `scratch/`, `tmp/`, `dist/`, or `build/` folders).
   - Googler-exclusive AI skills or agent configurations (`.gemini/`, `.agents/`, `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`) when committing to an **external client delivery repository**.
2. **Audit Command**: Run `git status --porcelain` to review all modified and untracked files. If any blocked file is listed as staged (marked with `A` or `M` in the first column), immediately unstage it using `git restore --staged <file>` and warn the user.
3. **Gitignore Check**: Ensure that `.gitignore` is active and correctly lists `.env` and `scratch/`.
4. **Client Delivery & OSPO Compliance Gate (`/fde-cross-compliance`)**: When preparing commits for external client handoff or open-source release, run `bash .agents/skills/fde-cross-compliance/scripts/sanitize_repo.sh --check .` (or invoke `/fde-cross-compliance`) to verify:
   - Root OSPO files (`LICENSE`, `CONTRIBUTING.md`, `README.md`) and Apache 2.0 source headers (`addlicense`).
   - Zero internal Google links (`go/`, `b/`, `cl/`, `google3/`, `piper://`, `g3doc`) or hardcoded GCP project/bucket identifiers.
   - Clean OSPO `cross` compliance scan (`/google/bin/releases/opensource/thirdparty/cross/cross`).

---

## 2. README Alignment Audit

Before staging or committing any files, the agent **MUST** verify that all custom agent skills in the workspace are documented in the root `README.md`:
1. **Audit Workspace**: List all active subdirectories under `.agents/skills/`.
2. **Verify README**:
   - Ensure the repository structure diagram in `README.md` includes all active skill directories.
   - Ensure the **Skills Catalog** contains every active skill directory with its slash command and description (parsed from its `SKILL.md` frontmatter).
3. **Auto-Update**: If any skill is undocumented or out of sync, update `README.md` to align with the active files before staging.

---

## 3. Diff Analysis & Technical Synthesis

To draft a meaningful commit message, the agent must analyze the exact technical changes:
1. **Auditing Diffs**: Run `git diff --cached` (for already staged files) or `git diff` (for modified unstaged files) to review the code and markdown changes.
2. **Change Extraction**: Identify:
   - *What* files were added, modified, or deleted.
   - *What* specific behaviors, workflows, or skills were introduced or modified.
   - *Why* the changes were made (e.g., compliance, user request, refactoring).

---

## 4. Conventional Commits Standard

All commit messages **MUST** conform to the Conventional Commits specification. The format is:

```
<type>(<scope>): <description>

[optional body containing bullet points detailing major changes]
```

### A. Commit Types
- **`feat`**: A new workflow, skill, script, or major feature (e.g., `feat(triage): add meeting-minutes automation`).
- **`fix`**: A bug fix, path repair, or security vulnerability remediation (e.g., `fix(skills): remove hardcoded component IDs in buganizer search`).
- **`docs`**: Documentation updates only (e.g., `docs(readme): update tree diagram and workflow catalog`).
- **`style`**: Visual layout, formatting, or diagram improvements that do not affect logic (e.g., `style(readme): update mermaid architecture diagram`).
- **`refactor`**: Code restructuring that neither fixes a bug nor adds a feature (e.g., `refactor(skills): rename spec-architect to scoping-skill`).
- **`test`**: Adding or modifying test suites, mock datasets, or evaluation scripts (e.g., `test(eval): add golden set for requirements parser`).
- **`chore`**: Maintenance tasks, `.gitignore` updates, or dependency changes (e.g., `chore(git): add scratch directory to gitignore`).

### B. Determining Scope
The scope should represent the specific module, package, or functional area being modified:
- The agent should **determine the scope dynamically** by looking at the directory structure of the modified files.
- Example scopes:
  - `docs`: For changes to markdown files, guides, or READMEs.
  - `config`: For changes to settings, `.gitignore`, or environment templates.
  - `harness` / `<module_name>`: For changes to core skills, subagents, or package directories.

---

## 5. Human-in-the-Loop Approval Gate

The agent **MUST NEVER** execute `git commit` or `git push` autonomously without explicit user sign-off.
1. **The Pitch**: Present a structured report in the chat:
   - **Staged Files**: A bulleted list of files ready to be committed.
   - **Proposed Commit Message**: The drafted Conventional Commit message.
   - **Risk/Security Status**: A confirmation that no sensitive files are staged.
2. **The Prompt**: Ask the user: *"Would you like me to commit these changes with the message above and push them to the remote repository?"*
3. **Action**: Only execute the commit and push commands after the user replies with approval (e.g., "Yes", "Proceed", or "Looks good").
