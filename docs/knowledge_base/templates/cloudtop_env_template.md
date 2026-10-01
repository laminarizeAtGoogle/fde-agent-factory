---
okf_version: "1.0"
entry_id: "<unique-kebab-case-slug>"
entry_name: "<Tool / Script / Skill / Command / Package Manager Name>"
category: "cloudtop_env"
sub_category: "<scripts | skills | slash_commands | package_managers>"
tier: "Tier 3 - Dev/Tooling"
status: "active"
owner: "Developer Productivity / Cloudtop Engineering"
dendrite_node_id: "n/a"
discovered_by: "static_analysis"
last_verified: "YYYY-MM-DD"
---

# OKF (Cloudtop Env): [Tool / Capability Name]

## 1. Executive Summary & Purpose
- **Primary Function**: [What this script, skill, command, or package manager does]
- **Target Audience / Consumer**: [Cloudtop developers, Antigravity AI agents]
- **Key Outcome**: [Operational result or capability enabled]

## 2. Cloudtop Environment Context
- **Sub-Category**: `[scripts | skills | slash_commands | package_managers]`
- **File / Directory Path**: `[e.g., ./scripts/<name>.sh | .agents/skills/<name> | .gemini/commands/ | ./bin/<bin>]`
- **Invocation Command / Syntax**:
  ```bash
  # Example command invocation
  ```
- **Runtime Environment & Dependencies**: `[Bash 5.2, Python 3.12, Node 22, Airlock Proxy, jq, curl]`
- **Isolation Scope**: `[Local Cloudtop workstation; zero host-level pollution]`

## 3. Technical Specifications & Configuration
- **Configuration Files**: `[e.g., .env, uv.toml, .npmrc, pre-command-config.json]`
- **Inputs & Options / Arguments**:
  | Flag / Arg | Type | Required | Description |
  |---|---|---|---|
  | `--example` | `string` | Yes | `Controls behavior` |
- **Security & Permissions**:
  - Execution mode: User space (`primarygroup`), no `sudo` required.
  - Proxy routing: Uses internal Corp Airlock proxy (`http://airlock-proxy.uplink.goog:999`).

## 4. Operational Runbook & Lifecycle
- **Step 1: Usage / Execution**:
  ```bash
  # Step by step execution instructions
  ```
- **Step 2: Verification & Output Validation**:
  ```bash
  # How to confirm success
  ```
- **Step 3: Troubleshooting & Failure Modes**:
  - *Symptom*: `[e.g. Permission denied, package resolution error]`
  - *Remediation*: `[e.g. chmod +x, verify airlock proxy connectivity]`

## 5. References & Cross-Links
- **Related OKF Entries**: `[Links to related Cloudtop tools or Codebase components]`
- **Workspace Paths**: `[Link to source files in repository]`
