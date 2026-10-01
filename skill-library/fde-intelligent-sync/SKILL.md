---
name: fde-intelligent-sync
description: Intelligently update global skills, scripts, and rules from the repository to user configuration with context-aware analysis.
---

# Intelligent Sync Skill (`fde-intelligent-sync`)

This skill synchronizes skills, scripts, and rules from workspace `.agents/` to global directories.

## Process

1. **Run Audit**: Compare workspace `.agents/` and `AGENTS.md` against global destination paths (`~/.gemini/jetski/global_skills/`, `~/.gemini/AGENTS.md`) to identify differences.
2. **Categorize and Analyze**:
   - **Skill Updates**: Analyze changed files in `.agents/skills/<skill_name>/`.
   - **Rules/Settings**: Analyze changes to `AGENTS.md` or `.agents/settings.json`.
3. **Impact Report**: Present grouped report (Item Name, Status, Context/Implications).
4. **Interactive Approval**: Ask user for confirmation (Update All, Skip All, or selective).
5. **Selective Execution**: Copy approved items to global target paths.
6. **Final Summary**: Report Net-New Items Added, Items Updated, and Items Skipped.
