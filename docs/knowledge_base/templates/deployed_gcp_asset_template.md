---
okf_version: "1.0"
entry_id: "<unique-kebab-case-slug>"
entry_name: "<Human Readable GCP Asset Name>"
category: "deployed_gcp_assets"
sub_category: "<compute | networking | iam | storage>"
tier: "<Tier 1 - Critical Path | Tier 2 - Operational | Tier 3 - Dev/Tooling>"
status: "active"
owner: "<Responsible Team or Engineering Function>"
dendrite_node_id: "<exact node id in docs/architecture_diagram.mmd>"
discovered_by: "read_agent"
last_verified: "YYYY-MM-DD"
---

# OKF (Deployed GCP Asset): [Asset Name]

## 1. Executive Summary & Purpose
- **Primary Function**: [Brief 1-sentence statement of asset role in GCP]
- **Target Audience / Consumer**: [Who or what interacts with this asset]
- **Key Outcome**: [Operational purpose provided by this cloud asset]

## 2. Deployed GCP Asset Context
- **GCP Resource Type**: `[e.g., compute.instances | storage.buckets | iam.workloadIdentityPools | compute.firewalls]`
- **Resource Identifier**: `[e.g., projects/<PROJECT_ID>/zones/<ZONE>/instances/<NAME>]`
- **Discovery Method (Read Agent)**:
  - Discovery SA: `cloudtop-agent-reader@<PROJECT_ID>.iam.gserviceaccount.com` (Viewer / read-only)
  - Inspection Command: `[e.g., gcloud compute instances describe <NAME> --project <PROJECT_ID>]`
- **Live State Attributes**:
  - Region / Zone: `[e.g., us-central1 / us-central1-a]`
  - Network Tier / IP: `[Internal IP, External IP, or N/A]`
  - Lifecycle Status: `[PROVISIONED / RUNNING / ACTIVE]`
- **IAM Boundary**: `[Managed under target GCP project perimeter; mutation restricted to least-privilege CI/CD service account]`

## 3. Technical Specifications & Configuration
- **Terraform Declarations**: `[Path to Terraform .tf defining this resource, e.g. terraform/main.tf]`
- **Attributes & Configuration**:
  | Attribute | Value / Default | Description |
  |---|---|---|
  | `machine_type` | `e2-medium` | `Instance size` |
- **Security & IAM Roles**:
  - Assigned Service Account: `[Assigned runtime SA or default]`
  - Management Permissions: `[Required role for deployer-sa to modify this asset]`

## 4. Operational Runbook & Lifecycle
- **Step 1: Provisioning & Update Flow**:
  ```bash
  # Deployment commands or PR trigger instructions
  ```
- **Step 2: Inspection & Health Check**:
  ```bash
  # Inspection commands via read-only agent
  ```
- **Step 3: Failure Modes & Blast Radius**:
  - *Failure Scenario*: `[What occurs when this cloud asset degrades or fails]`
  - *Blast Radius*: `[Impact on active services or development workflows]`
- **Step 4: Remediation & Incident Recovery**:
  ```bash
  # Remediation procedures
  ```

## 5. References & Cross-Links
- **Mermaid Architecture Diagram**: [`docs/architecture_diagram.mmd`](../../architecture_diagram.mmd)
- **Architecture Overview**: [`docs/architecture.md`](../../architecture.md)
- **Related OKF Entries**:
  - Related Cloud Assets: `[Link to corresponding OKF entry in docs/knowledge_base/{cloudtop_env,codebase,deployed_gcp_assets}/]`
  - Codebase: `[Link to related codebase module in docs/knowledge_base/codebase/]`
- **External Links**: `[GCP Documentation]`
