# Google Operational Knowledge Framework (OKF) Entry Template
<!--
  This template is used by the Knowledge Base Creation Agent to author or update
  knowledge base entries across three primary subcategories:
    1. cloudtop_env (scripts, skills, slash_commands, package_managers)
    2. deployed_gcp_assets (discovered via read-only agent queries)
    3. codebase (backed by the Mermaid architecture diagram)

  INSTRUCTIONS FOR KB CREATION AGENT:
  - Copy this template into the appropriate directory under docs/knowledge_base/:
      - cloudtop_env: docs/knowledge_base/cloudtop_env/<sub_category>/<entry-slug>.md
      - deployed_gcp_assets: docs/knowledge_base/deployed_gcp_assets/<entry-slug>.md
      - codebase: docs/knowledge_base/codebase/<entry-slug>.md
  - Populate the YAML frontmatter with exact identifiers.
  - Fill in all sections; delete any bracketed guidance comments.
  - Register the new entry in docs/knowledge_base/README.md.
-->

---
okf_version: "1.0"
entry_id: "<unique-kebab-case-slug>"
entry_name: "<Human Readable Name of Component, Script, Asset, or Module>"
category: "<cloudtop_env | deployed_gcp_assets | codebase>"
sub_category: "<scripts | skills | slash_commands | package_managers | compute | networking | iam | storage | terraform | agent_runtime | cicd>"
tier: "<Tier 1 - Critical Path | Tier 2 - Operational | Tier 3 - Dev/Tooling>"
status: "<active | stable | experimental | deprecated>"
owner: "<Responsible Team or Engineering Function>"
dendrite_node_id: "<exact node id in docs/architecture_diagram.mmd, or 'n/a' if purely local tool>"
discovered_by: "<read_agent | static_analysis | code_manifest | human>"
last_verified: "YYYY-MM-DD"
---

# OKF: [Entry Name]

## 1. Executive Summary & Purpose
<!--
  Provide a concise 2-4 sentence summary of what this component/asset is, why it exists,
  and its primary responsibility within the L200 workspace or cloud environment.
-->
- **Primary Function**: [Brief 1-sentence statement of core capability]
- **Target Audience / Consumer**: [Who or what invokes/uses this: e.g. Engineers, AI agents, CI/CD pipelines, Cloud runtime]
- **Key Outcome**: [What goal or state is achieved when this runs or exists]

---

## 2. Category-Specific Architectural Context

<!-- SELECT AND FILL THE RELEVANT SUB-SECTION BELOW BASED ON CATEGORY -->

### Option A: Cloudtop Environment Context (`category: cloudtop_env`)
<!-- Use this section if sub_category is scripts, skills, slash_commands, or package_managers -->
- **Tool Type**: `[script | skill | slash_command | package_manager]`
- **Executable / Config Location**: `[e.g., .agents/skills/<name> | .gemini/commands/ | ./scripts/<name>.sh]`
- **Invocation Command / Syntax**: `[e.g., /opsx-propose | /fde-audit | ./bin/uv run ...]`
- **Runtime Dependencies**: `[e.g., Bash 5.2, Python 3.12, Node.js 22, gcloud SDK]`
- **Isolation Scope**: `[Local workstation sandbox; does not alter remote cloud resources directly]`

### Option B: Deployed GCP Asset Context (`category: deployed_gcp_assets`)
<!-- Use this section for live cloud resources discovered via the read-only agent -->
- **GCP Resource Type**: `[e.g., run.services | compute.instances | storage.buckets | aiplatform.reasoningEngines]`
- **Resource Identifier**: `[e.g., projects/<PROJECT_ID>/locations/<REGION>/services/<NAME> | gs://<BUCKET_NAME>]`
- **Discovery Method (Read Agent)**:
  - Discovery SA: `<READONLY_SA>@<PROJECT_ID>.iam.gserviceaccount.com` (Viewer / read-only)
  - Inspection Command: `[e.g., gcloud run services describe <NAME> | gcloud storage buckets describe gs://<NAME>]`
- **Live State Attributes**:
  - Region / Zone: `[e.g., us-central1 / us-central1-a]`
  - Network Tier / IP: `[Internal IP, External IP, or N/A for serverless/IAM]`
  - Lifecycle Status: `[PROVISIONED / RUNNING / ACTIVE]`
- **IAM Boundary**: `[Bound to target GCP project; mutation restricted to least-privilege CI/CD service account]`

### Option C: Codebase Context (`category: codebase`)
<!-- Use this section for code, Terraform modules, and architecture assets backed by the diagram -->
- **Mermaid Diagram Backing**:
  - Authoritative Platform: **Mermaid** (`docs/architecture_diagram.mmd`)
  - Node ID: `[Matching ID in docs/architecture_diagram.mmd]`
  - Architectural Boundary: `[e.g., developer_workstation | github_platform | gcp_cloud_boundary | application_runtime]`
- **Source Code Paths**: `[e.g., terraform/main.tf, .github/workflows/terraform-apply.yml, main.py]`
- **Inbound Connections**: `[Upstream components that trigger, call, or provide input to this module]`
- **Outbound Connections**: `[Downstream dependencies, APIs, storage sinks, or compute targets]`
- **Data & Control Flow**: `[Protocol (HTTPS/gRPC/STS), Auth method (OIDC/SA Token), Flow Direction]`

---

## 3. Technical Specifications & Configuration
- **Configuration Files / Manifests**: `[File paths where settings are declared, e.g. terraform.tfvars, uv.toml, .env]`
- **Parameters & Variables**:
  | Name | Type | Default | Description |
  |---|---|---|---|
  | `example_param` | `string` | `""` | `Description of what this controls` |
- **Security & Permissions**:
  - Required IAM Roles: `[e.g., roles/viewer, roles/compute.admin]`
  - Network Access: `[e.g., IAP tunnel tcp:22, egress to Airlock proxy http://airlock-proxy.uplink.goog:999]`
  - Secret Handling: `[No hardcoded credentials; uses WIF OIDC or Secret Manager]`

---

## 4. Operational Runbook & Lifecycle
- **Step 1: Provision / Setup**:
  ```bash
  # Command(s) to create, initialize, or install this component
  ```
- **Step 2: Verification & Health Check**:
  ```bash
  # Command(s) to verify healthy operation and correct output
  ```
- **Step 3: Failure Modes & Blast Radius**:
  - *Failure Scenario*: `[What happens if this fails or becomes unavailable]`
  - *Blast Radius*: `[Isolated to local developer / blocks CI/CD / impacts live GCP sandbox]`
- **Step 4: Recovery & Troubleshooting**:
  ```bash
  # Diagnostic commands and remediation steps
  ```

---

## 5. References & Cross-Links
- **Mermaid Architecture Diagram**: [`docs/architecture_diagram.mmd`](../architecture_diagram.mmd)
- **Architecture Overview**: [`docs/architecture.md`](../architecture.md)
- **Related OKF Entries**:
  - Upstream: `[Link to upstream OKF component]`
  - Downstream: `[Link to downstream OKF component]`
- **External Links**: `[Official GCP docs]`
