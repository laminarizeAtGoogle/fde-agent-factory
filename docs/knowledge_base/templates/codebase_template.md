---
okf_version: "1.0"
entry_id: "<unique-kebab-case-slug>"
entry_name: "<Code Module / Subsystem / CI/CD Pipeline Name>"
category: "codebase"
sub_category: "<terraform | agent_runtime | cicd | core_library>"
tier: "<Tier 1 - Critical Path | Tier 2 - Operational | Tier 3 - Dev/Tooling>"
status: "active"
owner: "<Responsible Team or Engineering Function>"
dendrite_node_id: "<exact node id in docs/architecture_diagram.mmd>"
discovered_by: "static_analysis"
last_verified: "YYYY-MM-DD"
---

# OKF (Codebase): [Component / Module Name]

## 1. Executive Summary & Purpose
- **Primary Function**: [Brief 1-sentence statement of core capability]
- **Target Audience / Consumer**: [Who or what invokes/uses this: e.g. Cloudtop developers, Antigravity AI agents, GitHub Actions]
- **Key Outcome**: [What goal or state is achieved when this code executes]

## 2. Codebase & Architectural Context
- **Mermaid Diagram Backing**:
  - Authoritative Platform: **Mermaid** (`docs/architecture_diagram.mmd`)
  - Node ID: `[Matching ID in docs/architecture_diagram.mmd]`
  - Architectural Boundary: `[developer_workstation | github_platform | gcp_cloud_boundary | application_runtime]`
- **Source Code Paths**: `[e.g., terraform/, .github/workflows/, main.py]`
- **Inbound Connections**: `[Upstream callers, workflows, or events triggering this module]`
- **Outbound Connections**: `[Downstream dependencies, GCP APIs, storage sinks, or compute targets]`
- **Data & Control Flow**: `[Protocol (HTTPS/gRPC/STS), Auth method (OIDC/ADC/SA), Flow Direction]`

## 3. Technical Specifications & Configuration
- **Configuration Files / Manifests**: `[File paths where settings are declared, e.g. terraform.tfvars, uv.toml, .env]`
- **Parameters & Variables**:
  | Name | Type | Default | Description |
  |---|---|---|---|
  | `example_var` | `string` | `""` | `Description of variable` |
- **Security & Permissions**:
  - Minimum IAM Roles: `[e.g., roles/viewer, roles/compute.admin]`
  - Authentication Method: `[Workload Identity Federation / ADC / SA impersonation]`
  - Isolation Scope: `[Zero static keys; strict parameter validation]`

## 4. Operational Runbook & Lifecycle
- **Step 1: Build / Provision / Run**:
  ```bash
  # Step by step execution instructions
  ```
- **Step 2: Verification & Health Check**:
  ```bash
  # Commands to verify correct behavior and outputs
  ```
- **Step 3: Failure Modes & Blast Radius**:
  - *Failure Scenario*: `[What occurs when this component fails]`
  - *Blast Radius*: `[Isolated to local developer / blocks CI/CD / impacts live GCP resources]`
- **Step 4: Recovery & Troubleshooting**:
  ```bash
  # Diagnostic commands and remediation steps
  ```

## 5. References & Cross-Links
- **Mermaid Architecture Diagram**: [`docs/architecture_diagram.mmd`](../../architecture_diagram.mmd)
- **Architecture Overview**: [`docs/architecture.md`](../../architecture.md)
- **Related OKF Entries**:
  - Related Modules: `[Link to corresponding OKF entry in docs/knowledge_base/{cloudtop_env,codebase,deployed_gcp_assets}/]`
  - Upstream / Downstream: `[Link to related OKF entries]`
- **External Links**: `[Official documentation]`
