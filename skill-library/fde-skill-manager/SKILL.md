---
name: fde-skill-manager
description: A Skill Manager that allows users to list and selectively install skills from the central repository (agent-driven-development).
---

# Skill Manager

The Skill Manager allows you to manage the skills in your local workspace or global configuration by discovery and installation from the central `agent-driven-development` repository.

## Capabilities

- **List Remote Skills**: Identify what skills are available for installation.
- **Granular Installation**: Install specific skills into your `.agents/skills/` (Workspace) or `~/.gemini/jetski/skills/` (Global) directories.
- **Update Existing Skills**: Refresh your local or global skills with the latest versions.

## Installation Strategy

> [!TIP]
> **Recommend Global Installation**: For shared tools like `adk-agent-builder`, `fde-gcp-architect`, or `openspec-propose`, recommend that the user installs them into their global directory: `~/.gemini/jetski/skills/`. This makes them available across all projects.

## Instructions

Whenever a user mentions "Skill Manager", or asks to "add a skill" or "list available skills", follow this process:

1. **List Skills First**: Use the helper script to get the current list of available skills from the remote repository.
   ```bash
   python3 .agents/skill-library/fde-skill-manager/scripts/skill-manager.py list
   ```
2. **Present and Ask**: Show the user the list of available skills.
3. **Determine Target**: Ask if they want the skill installed in the **current workspace** (default) or **globally** (recommended for most skills).
4. **Execute Installation**: Use the helper script to perform the installation.
   - **For Workspace**: `python3 .agents/skill-library/fde-skill-manager/scripts/skill-manager.py install [skill_name]`
   - **For Global**: `python3 .agents/skill-library/fde-skill-manager/scripts/skill-manager.py install [skill_name] --target ~/.gemini/jetski/skills/`
5. **Post-Install Refresh**: After a new skill is installed, acknowledge it and explain its purpose (check the new skill's `SKILL.md`).

## Technical Details

- **Source Repos**: `https://github.com/cloud-ai-fde/agent-driven-dev.git` and `https://github.com/google/adk-python/tree/main`
- **Installation Method**: Uses `git archive` to pull specific subdirectories without cluttering the local git history with remote branch tracking.
- **Safe by Default**: Does not use `sparse-checkout`, so your existing project files remain untouched and visible.
