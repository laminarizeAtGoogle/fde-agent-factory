---
okf_version: "1.0"
entry_id: "fde-agent-factory-plugin"
entry_name: "Cloud AI FDE Agent Software Factory Plugin & Harness"
category: "cloudtop_env"
sub_category: "skills"
tier: "Tier 1 - Critical Path"
status: "active"
owner: "Cloud AI FDE / Agent Engineering"
dendrite_node_id: "plugin_manifest"
discovered_by: "static_analysis"
last_verified: "2026-10-01"
---

# OKF (Cloudtop Env): Cloud AI FDE Agent Software Factory Plugin & Harness

## 1. Executive Summary & Purpose
- **Primary Function**: Packages the reusable meta-configuration of the Agentic Software Factory—including 25 pre-loaded core skills (`adk-*`, `fde-*`, `openspec-*`), 13 on-demand `/fde-*` workflow skills, 20 Gemini CLI slash-command TOMLs, `PreToolUse` credential/OSPO sanitization and Mermaid/OKF architecture gates, and supporting OKF/Mermaid/OpenSpec templates—into a portable Jetski plugin and workspace installer.
- **Target Audience / Consumer**: Cloud AI Field Deployment Engineers (FDEs), software engineers, and AI coding agents (Antigravity / Jetski / Gemini CLI).
- **Key Outcome**: Enables any repository to adopt the full Software Factory governance, skill catalog, slash commands, and pre-push security/documentation gates either by linking directly to a local clone (`install.sh --link`) or bootstrapping standalone files (`install.sh --copy`).

## 2. Cloudtop Environment Context
- **Sub-Category**: `skills`
- **File / Directory Path**: `plugin.json`, `hooks.json`, `install.sh`, `scripts/`, `skills/`, `skill-library/`, `workflows/`, `commands/`, `rules/AGENTS.md`, `docs/`, `templates/`
- **Invocation Command / Syntax**:
  ```bash
  # Link into an existing repo so local edits update the plugin repo directly:
  ./install.sh --link /path/to/target-repo

  # Or copy/bootstrap into a brand-new repo:
  ./install.sh --copy /path/to/new-repo
  ```
- **Runtime Environment & Dependencies**: `Bash 5+`, `Python 3.10+`, `git`, `jq` (optional fast-path filter).
- **Isolation Scope**: Operates strictly within the developer's repository workspace and `.agents/` / `.gemini/` customization directories.

## 3. Technical Specifications & Configuration
- **Configuration Files**: `plugin.json`, `hooks.json`, `scripts/pre-command-config.json`, `scripts/check-architecture-docs-config.json`, `templates/openspec/config.yaml`.
- **Inputs & Options / Arguments**:
  | Flag / Arg | Type | Required | Description |
  |---|---|---|---|
  | `--link` | `flag` | No (Default) | Symlinks `.agents/`, `.gemini/commands/`, `AGENTS.md`, `.gitmessage.txt`, and OKF templates to the plugin clone so local edits update the plugin git repo. |
  | `--copy` | `flag` | No | Copies all plugin files and starter templates into the target workspace as standalone files. |
  | `--force` | `flag` | No | Overwrites existing starter files (`openspec/config.yaml`, `docs/architecture.md`, `docs/architecture_diagram.mmd`). |
  | `--verify` | `flag` | No | Runs the automated `unittest`/`pytest` suites for `pre_command_hook.py` and `check_architecture_docs.py`. |
- **Security & Permissions**:
  - Enforces pre-push credential and OSPO compliance scanning before any `git push` tool call executes.
  - Enforces Mermaid architecture diagram and Google OKF Knowledge Base completeness before any `git push` tool call executes.

## 4. Operational Runbook & Lifecycle
- **Step 1: Usage / Execution**:
  ```bash
  # Clone directly into an existing repo's .agents directory and wire symlinks:
  rm -rf .agents
  git clone <REPO_URL> .agents
  ./.agents/install.sh --link
  ```
- **Step 2: Verification & Output Validation**:
  ```bash
  python3 -m unittest discover -s scripts -p "test_*.py" -v
  ```
- **Step 3: Troubleshooting & Failure Modes**:
  - *Symptom*: `PreToolUse` hook denies `git push` due to unsynchronized `./docs/` or detected credentials.
  - *Remediation*: Run `/update-architecture-docs` or `/git-push-sanitization-check`, commit the resulting fixes, and retry `git push`.

## 5. References & Cross-Links
- **Mermaid Architecture Diagram**: [`docs/architecture_diagram.mmd`](../../architecture_diagram.mmd)
- **Architecture Overview**: [`docs/architecture.md`](../../architecture.md)
- **OKF Catalog Index**: [`README.md`](../../README.md)
