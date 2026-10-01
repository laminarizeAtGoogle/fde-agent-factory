---
name: fde-presentation-skill
description: Create professional presentations using templates. Supports both the default Google corporate template and user-uploaded custom templates. Specializes in template-based presentation creation with proper slide layout selection, text replacement, and visual consistency. Use when users need presentations created from templates orask for a presentation or slides.
---

# Presentation Skill - Template-Based Creation

This skill enables creating professional presentations from templates via a CLI interface.

**IMPORTANT WORKING DIRECTORY NOTE**:
Always run commands from the USER's actual project directory, NOT from `~/.agentss/skills/presentation-skill/`.

## Dependencies
- `python-pptx`, `markitdown[pptx]`, `defusedxml`, `Pillow`

## When to Use
Use when users request the creation of a corporate or standard presentation from a template.
Do NOT use for general PowerPoint editing (use `pptx` skill).

## Core Workflows
For detailed, step-by-step instructions on the two workflows below, **you MUST read**:
`cat ~/.agentss/skills/presentation-skill/resources/workflows.md`

### 1. Default Google Template
Uses the built-in 48-slide corporate layout: `~/.agentss/skills/presentation-skill/resources/template.pptx`.

### 2. Custom User Template
Uses a user-provided template. Extract thumbnails/text properties using `cli.py analyze`.

## Critical `cli.py` Tool Operations
The skill uses a local script at `scripts/cli.py` to drive the presentation generation:

1. **rearrange**: Create a new deck using slide layouts by their numerical index (`2,3,7,12,13,...`) from the template.
   `python scripts/cli.py rearrange <template.pptx> <working.pptx> <indices>`
2. **inventory**: Extract exact shape boundaries and property IDs before replacing.
   `python scripts/cli.py inventory <working.pptx> <inventory.json>`
3. **replace**: Write mapped JSON text into the shapes.
   `python scripts/cli.py replace <working.pptx> <replacements.json> <final-presentation.pptx> --cleanup`

### Best Practices
- **Verify before Replacing**: You MUST read the generated `inventory.json` layout map before creating your `replacements.json` file to ensure the shapes match exactly.
- **Match Formatting**: Copy paragraph formatting details (bold, alignments, font size) exactly as found in the layout map.
- **Bullets**: If you need bulleted text, use `"bullet": true, "level": 0`.
