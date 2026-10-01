---
name: update-architecture-docs
description: >-
  Instructs a subagent to update the Google OKF Knowledge Base and Mermaid architecture
  diagram with all changes comprised in outgoing git commits prior to pushing.
---

# update-architecture-docs Subagent

This subagent is executed automatically by the pre-tool-use hook on `git push` or manually via the `/update-architecture-docs` slash command.
Its mission is to ensure that `./docs/` is always completely synchronized with outgoing code and infrastructure updates, utilizing the **Mermaid format** for diagrams and **Google OKF** (Operational Knowledge Framework) for the Knowledge Base.

---

## Subagent Procedure

When invoked, execute the following steps in sequence:

### Step 1: Inspect Outgoing Changes & Diffs

1. Determine the outgoing commit range:
   ```bash
   git rev-parse --abbrev-ref @{u} 2>/dev/null && RANGE="@{u}..HEAD" || RANGE="origin/main..HEAD"
   git log $RANGE --oneline
   git diff --name-only $RANGE
   ```
2. Inspect the detailed code/infrastructure diff:
   ```bash
   git diff $RANGE
   ```
3. Classify all modified files across the 3 OKF categories:
   - **Cloudtop Environment** (`docs/knowledge_base/cloudtop_env/`):
     - Scripts in `.agents/scripts/`, `scripts/`, or root.
     - Skills in `.agents/skills/`, `.gemini/skills/`.
     - Slash commands in `.gemini/commands/`.
     - Toolchains & package managers (`bin/`, `uv`, `terraform`, `gcloud`, `gh`).
   - **Deployed GCP Assets** (`docs/knowledge_base/deployed_gcp_assets/`):
     - Terraform infrastructure definitions (`terraform/*.tf`).
     - GCP resources: WIF pools, service accounts, IAM roles, GCS buckets, VPCs, firewall rules, compute instances.
   - **Codebase** (`docs/knowledge_base/codebase/`):
     - Application modules, Python ADK agent implementations.
     - CI/CD workflows (`.github/workflows/*.yml`).
     - Architectural subsystems and interfaces.

---

### Step 2: Update the Canonical Mermaid Architecture Diagram

1. **Strict Mermaid Standard**:
   - The architecture diagram **MUST** utilize **Mermaid** syntax (`flowchart TD` or `flowchart LR`).
   - Diagrams must be maintained in [`docs/architecture.md`](docs/architecture.md) (in a ````mermaid` block) and [`docs/architecture_diagram.mmd`](docs/architecture_diagram.mmd).
   - **NEVER** use ASCII text box art (`+---+` / `|   |`).
2. **Update Diagram Model**:
   - Inspect [`docs/architecture_diagram.mmd`](docs/architecture_diagram.mmd) and [`docs/architecture.md`](docs/architecture.md).
   - If new components or systems were introduced, add them under the corresponding subgraph boundary (`Zone1`, `Zone2`, `Zone3`, or `Zone4`).
   - If new inter-component flows or security controls were added, register the directional edges with appropriate labels and protocols.
   - Update `Last Synchronized` date.
3. **Synchronize `docs/architecture.md`**:
   - Update the embedded ````mermaid` code block in [`docs/architecture.md`](docs/architecture.md) to reflect the refreshed architecture.
   - Ensure component descriptions, security perimeters, and interfaces remain completely synchronized.

---

### Step 3: Update the Google OKF Knowledge Base

1. **Follow OKF Specifications**:
   - Follow the standards defined in [`docs/knowledge_base/OKF_SPEC.md`](docs/knowledge_base/OKF_SPEC.md) and [`docs/knowledge_base/TEMPLATE.md`](docs/knowledge_base/TEMPLATE.md).
2. **Create or Update Category Entries**:
   - For **Cloudtop Environment**: use [`templates/cloudtop_env_template.md`](docs/knowledge_base/templates/cloudtop_env_template.md) in `docs/knowledge_base/cloudtop_env/{workstation,package_managers,scripts,skills}/`.
   - For **Deployed GCP Assets**: use [`templates/deployed_gcp_asset_template.md`](docs/knowledge_base/templates/deployed_gcp_asset_template.md) in `docs/knowledge_base/deployed_gcp_assets/`.
   - For **Codebase**: use [`templates/codebase_template.md`](docs/knowledge_base/templates/codebase_template.md) in `docs/knowledge_base/codebase/`.
3. **Architectural Component Coverage**:
   - Every architectural component declared in the Mermaid diagram must have a matching OKF documentation entry within its corresponding category directory.
4. **Update Catalog Index**:
   - Ensure [`docs/knowledge_base/README.md`](docs/knowledge_base/README.md) lists the new or modified components in the catalog table.

---

### Step 4: Stage & Commit Architecture Documentation

1. Stage all documentation updates:
   ```bash
   git add docs/
   ```
2. Commit the changes:
   ```bash
   git commit -m "docs: update architecture diagram (Mermaid) and OKF knowledge base"
   ```

---

### Step 5: Verification & Status Output

1. Verify that `docs/architecture.md` and `docs/architecture_diagram.mmd` are clean, well-formed, and free of ASCII box drawings.
2. Verify that all OKF files pass basic structure checks.
3. Emit final status line:
   - On success:
     ```text
     ARCHITECTURE_DOCS_UPDATE: SUCCESS: Updated <list-of-updated-components> in Mermaid diagram and OKF Knowledge Base.
     ```
   - On failure:
     ```text
     ARCHITECTURE_DOCS_UPDATE: FAILED: <reason-for-failure>
     ```
