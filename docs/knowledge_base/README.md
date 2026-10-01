# Google Operational Knowledge Framework (OKF) Knowledge Base Index

Welcome to the **Operational Knowledge Framework (OKF)** catalog for this repository. Every component represented in [`docs/architecture.md`](../architecture.md) and [`docs/architecture_diagram.mmd`](../architecture_diagram.mmd) is documented here following [`OKF_SPEC.md`](OKF_SPEC.md).

---

## 1. Specifications & Authoring Templates

| Document | Purpose |
| :--- | :--- |
| [`OKF_SPEC.md`](OKF_SPEC.md) | Canonical Google OKF v1.0 schema, required sections, and validation rules. |
| [`TEMPLATE.md`](TEMPLATE.md) | Master OKF component template covering `cloudtop_env`, `codebase`, and `deployed_gcp_assets`. |
| [`templates/cloudtop_env_template.md`](templates/cloudtop_env_template.md) | Category template for workstation scripts, skills, slash commands, and package managers. |
| [`templates/codebase_template.md`](templates/codebase_template.md) | Category template for application modules, agent runtimes, CI/CD workflows, and Terraform IaC. |
| [`templates/deployed_gcp_asset_template.md`](templates/deployed_gcp_asset_template.md) | Category template for live GCP resources inspected via the read-only probe service account. |

---

## 2. Registered OKF Component Entries

### A. Cloudtop Environment (`cloudtop_env/`)

| Entry ID | Component Name | Tier | Status | Link |
| :--- | :--- | :--- | :--- | :--- |
| `fde-agent-factory-plugin` | Cloud AI FDE Agent Software Factory Plugin & Harness | Tier 1 - Critical Path | `active` | [`cloudtop_env/fde-agent-factory-plugin.md`](cloudtop_env/fde-agent-factory-plugin.md) |

### B. Codebase Modules (`codebase/`)

*(Add codebase module OKF entries under `docs/knowledge_base/codebase/` using [`templates/codebase_template.md`](templates/codebase_template.md))*

### C. Deployed GCP Assets (`deployed_gcp_assets/`)

*(Add deployed GCP asset OKF entries under `docs/knowledge_base/deployed_gcp_assets/` using [`templates/deployed_gcp_asset_template.md`](templates/deployed_gcp_asset_template.md))*
