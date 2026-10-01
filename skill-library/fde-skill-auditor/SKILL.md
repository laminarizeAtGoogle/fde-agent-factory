---
name: fde-skill-auditor
description: Validates all agent skills against Agent Skill Anatomy and Core Principles to ensure structural correctness and progressive disclosure. Use this skill when asked to audit, check, or validate existing skills.
---

# Skill Auditor

You are tasked with auditing the agentic codebase's skill directory for compliance with Agent Skill Standards.

## Auditing Rules

Skills must adhere to:
1. **Valid Anatomy**: They must reside in a folder with at most `scripts/`, `examples/`, and `resources/` subdirectories. They MUST have a `SKILL.md`.
2. **No Auxiliaries**: Files like `README.md`, `CHANGELOG.md`, etc., are explicitly forbidden.
3. **Progressive Disclosure**: `SKILL.md` must be lean. Exhaustive documentation or step-by-step procedures should live in `resources/`. If a `SKILL.md` exceeds 3000 characters, it fails this check.

*Note: The complete rules and philosophies behind these checks can be found at `.agents/skill-library/fde-skill-auditor/resources/agent-skills-guide.md`.*

## Auditing Instructions

To perform an audit, run the packaged Python validation script:

```bash
# Run a dry-run audit
python .agents/skill-library/fde-skill-auditor/scripts/audit.py --dir .agents/skills

# Run an audit with auto-fix (e.g. deleting auxiliary files)
python .agents/skill-library/fde-skill-auditor/scripts/audit.py --dir .agents/skills --fix
```

## Self-Correction Loop
If the audit identifies `SKILL.md` files that are too large (violating Progressive Disclosure):
1. Use the `view_file` tool to parse the problematic `SKILL.md`.
2. Determine what procedural text or reference data can be moved.
3. Use `write_to_file` to create `.agents/skills/<skill>/resources/workflows.md` (or similar).
4. Use `replace_file_content` to drastically simplify `SKILL.md`, leaving only triggers, core constraints, and pointers to the new resource file.
5. Re-run the audit script to confirm compliance.
