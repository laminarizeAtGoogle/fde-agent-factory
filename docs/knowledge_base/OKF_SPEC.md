# Google Operational Knowledge Framework (OKF) Specification

This specification defines the standard structure, schema, and quality criteria for component entries within the `./docs/knowledge_base/` catalog.

---

## Purpose & Scope

The **Operational Knowledge Framework (OKF)** standardizes architectural and operational knowledge for enterprise and Google Cloud systems. In this repository, every architectural component represented in the [Mermaid Architecture Diagram](../architecture.md) possesses a formal, structured OKF entry organized across three primary architectural pillars:

1. **Cloudtop Environment** (`docs/knowledge_base/cloudtop_env/`): Workstation shell, hermetic package managers, automation scripts, and agent skills.
2. **Codebase Modules** (`docs/knowledge_base/codebase/`): Application code, ADK agent runtime, CI/CD pipelines, and Terraform IaC manifests.
3. **Deployed GCP Assets** (`docs/knowledge_base/deployed_gcp_assets/`): Live cloud resources, Workload Identity Federation (WIF), IAM service accounts, GCS state backends, VPC networks, firewall rules, and Compute Engine VM instances.

---

## OKF Component Schema

Every OKF entry must be stored as a Markdown document under its corresponding category directory (`docs/knowledge_base/<category>/<sub_category>/<entry-slug>.md` or `docs/knowledge_base/<category>/<entry-slug>.md`) and start with standard YAML frontmatter:

```yaml
---
okf_version: "1.0"
entry_id: "string (kebab-case unique identifier matching entry basename)"
entry_name: "string (human-readable title)"
category: "string (cloudtop_env | codebase | deployed_gcp_assets)"
sub_category: "string (workstation | package_managers | scripts | skills | terraform | agent_runtime | cicd | compute | networking | iam | storage)"
tier: "string (Tier 1 - Critical Path | Tier 2 - Operational | Tier 3 - Development)"
status: "string (active | stable | experimental | deprecated)"
owner: "string (responsible team or role)"
dendrite_node_id: "string (exact component ID in docs/architecture.md and docs/architecture_diagram.mmd, or 'n/a' for local-only tooling)"
discovered_by: "string (static_analysis | read_agent | code_manifest | human)"
last_verified: "YYYY-MM-DD"
---
```

---

## Required Document Structure

Each OKF entry must include the following five standard sections:

### 1. Executive Summary & Purpose
- High-level overview of the component or tool.
- The specific problem it solves and its primary responsibility within the system.

### 2. Architectural Role & Topology
- **Subsystem & Boundary**: The enclosing boundary (e.g., `developer_workstation`, `github_platform`, `gcp_cloud_boundary`, `application_runtime`).
- **Inbound Connections**: Upstream callers, data sources, and triggering events.
- **Outbound Connections**: Downstream dependencies, sinks, and targets.
- **Trust Boundary & Security Classification**: Network isolation level, zero-trust classification.

### 3. Technical Specifications & Configuration
- **Implementation Path(s)**: Concrete file paths in the workspace implementing or configuring this component (e.g., `terraform/`, `scripts/`, `bin/`, `.github/workflows/`).
- **Protocols & Interfaces**: Communication protocols (HTTPS, gRPC, STS, SSH) and ports.
- **Configuration & Environment Variables**: Key environment variables, Terraform variables, or flags.
- **IAM Roles & Permissions**: Minimum required IAM roles and service account bindings.

### 4. Operational Runbook & Lifecycle
- **Provisioning & Deployment**: How the component is created, initialized, or updated.
- **Verification & Health Checks**: Commands to inspect and verify healthy operation.
- **Failure Modes & Blast Radius**: Impact on the wider system if this component fails or becomes unreachable.
- **Recovery & Troubleshooting**: Step-by-step diagnostic and remediation instructions.

### 5. References & Linked Assets
- Link to corresponding node in `docs/architecture.md` and `docs/architecture_diagram.mmd`.
- Cross-references to upstream and downstream OKF component entries.
- Official Google Cloud documentation or internal `go/` links.

---

## Quality Criteria & Validation Rules

1. **Completeness**: Every component declared in `docs/architecture.md` / `docs/architecture_diagram.mmd` must have a matching OKF document in `docs/knowledge_base/` organized within its proper category (`cloudtop_env/`, `codebase/`, or `deployed_gcp_assets/`).
2. **Determinism**: Entry IDs in frontmatter must match file basenames (`<entry-id>.md`) and map to diagram IDs.
3. **Actionable Runbooks**: Operational verification and troubleshooting sections must contain executable commands or exact paths.
