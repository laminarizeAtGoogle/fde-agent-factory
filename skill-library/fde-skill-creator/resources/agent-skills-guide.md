# The Complete Guide to Building Skills for AI Agents

## Introduction
A skill is a set of instructions—packaged as a simple folder—that teaches the AI agent how to handle specific tasks or workflows. Skills are one of the most powerful ways to customize the AI agent for your specific needs. Instead of re-explaining your preferences, processes, and domain expertise in every conversation, skills let you teach the AI agent once and benefit every time.

Skills are powerful when you have repeatable workflows: generating frontend designs from specs, conducting research with consistent methodology, creating documents that follow your team's style guide, or orchestrating multi-step processes. They work well with the agent's built-in capabilities like code execution and document creation. For those building MCP integrations, skills add another powerful layer helping turn raw tool access into reliable, optimized workflows.

This guide covers everything you need to know to build effective skills—from planning and structure to testing and distribution.

### What You'll Learn:
- Technical requirements and best practices for skill structure.
- Patterns for standalone skills and MCP-enhanced workflows.
- How to test, iterate, and distribute your skills.

### Who This Is For:
- Developers who want the AI agent to follow specific workflows consistently.
- Power users who want the AI agent to automate workflows.
- Teams looking to standardize how the AI agent works across their organization.

---

## 1. Fundamentals

### What is a Skill?
A skill is a straightforward directory containing:
- `SKILL.md` (required): Instructions in Markdown with YAML frontmatter.
- `scripts/` (optional): Executable code (Python, Bash, etc.) for deterministic logic.
- `resources/` (optional): Documentation loaded as needed (schemas, static data).
- `examples/` (optional): Templates, golden code snippets, or reference implementations used in output.

**Important**: A skill MUST NOT contain any auxiliary files like `README.md`, `CHANGELOG.md`, or other meta-files. The target audience of a skill is the agent, not a human.

### Core Design Principles

**Progressive Disclosure**
Skills use a three-level system to minimize context window bloat:
1. **First level (YAML frontmatter)**: Always loaded in the agent's system prompt. Provides just enough information for the AI agent to know *when* each skill should be used without loading all of it into context.
2. **Second level (SKILL.md body)**: Loaded when the AI agent thinks the skill is relevant to the current task. Contains the full instructions and guidance.
3. **Third level (Linked files)**: Additional files bundled within the `resources/`, `examples/`, or `scripts/` directory that the AI agent can choose to navigate and discover only as needed.

**Composability & Portability**
The AI agent can load multiple skills simultaneously. Your skill should work well alongside others and not assume it's the only capability available. Create a skill once and it works identically across the chat interface, the coding environment, and API.

### For MCP Builders: Skills + Connectors
If you already have a working Model Context Protocol (MCP) server, skills act as the knowledge layer on top. 

**The Kitchen Analogy**:
- MCP provides the professional kitchen: access to tools, ingredients, and equipment.
- Skills provide the recipes: step-by-step instructions on how to create something valuable.

Without skills, users have tool access but don't know the proper workflow. With skills, pre-built workflows activate automatically, ensuring consistent, reliable tool usage.

---

## 2. Planning and Design

### Start with Use Cases
Identify 2-3 concrete use cases your skill should enable before writing any code.

**Common Skill Categories:**
1. **Document & Asset Creation**: Creating consistent, high-quality output (designs, docs, code). Rely mostly on the agent's built-in toolsets or code execution.
2. **Workflow Automation**: Multi-step processes that benefit from consistent methodology, including coordination across multiple tools.
3. **MCP Enhancement**: Enhancing the tool access an MCP server provides with domain expertise, error handling, and orchestrating multiple tools in sequence.

### Defining Success Criteria
Aim for rigor in testing.
- **Quantitative Metrics**: Does the skill trigger 90%+ of the time appropriately? Does the workflow succeed with 0 failed API calls?
- **Qualitative Metrics**: Users don't need to prompt the agent about next steps; the workflows complete without deep human correction.

### Technical Requirements

**File Structure Overview:**
```
my-amazing-skill/
├── SKILL.md                 # Required 
├── scripts/                 # Optional
│   └── process_data.py
├── resources/               # Optional
│   └── schema-v1.json
└── examples/                # Optional
    └── perfect-output.md
```

**YAML Frontmatter Rules (CRITICAL)**
The YAML frontmatter tells the agent *when* to trigger.

```yaml
---
name: my-amazing-skill
description: What it does. Use when the user asks to [specific trigger phrases]. No more than 1024 characters.
metadata:
  author: Agent Author
  version: 1.0.0
---
```

**Rules:**
- `name`: kebab-case only. No spaces, no capitals. Do NOT use restricted system keywords.
- `description`: MUST state *what* it does, and *when* to use it (trigger phrases).
- XML tags (`<`, `>`) are strictly forbidden in frontmatter.

### Writing Effective SKILL.md Instructions
Keep the instructions concise and actionable.
Write the instruction body using the imperative form. Example:

```markdown
# My Amazing Skill

## Instructions

### Step 1: Initialize
- Fetch the data via the `fetch_tool`.
- Parse the content against the schema in `resources/schema-v1.json`.

### Step 2: Validate
- Run `python scripts/process_data.py --input {data}` to check validity.
- CRITICAL: Never proceed if the script exits with code 1.

## Troubleshooting
If the API returns "Rate Limited", implement an exponential backoff wait and try again.
```

---

## 3. Testing and Iteration

### Recommended Testing Approach
1. **Triggering Tests**: Ask the chat interface queries that should and shouldn't trigger the skill. Ensure the frontmatter is correctly capturing intention.
2. **Functional Tests**: Ask the AI agent to execute a task using the skill end-to-end. Does it succeed in 1 shot? Does it hallucinate a step?
3. **Performance Limits**: If the agent hallucinates, add a negative constraint (e.g., "NEVER guess the path; always read the file system").

### Overtriggering and Undertriggering
- **Overtriggering**: The skill loads for irrelevant queries. Fix: Add negative triggers (e.g., "Do NOT use for general queries").
- **Undertriggering**: The skill doesn't load when requested. Fix: Add explicit keywords and synonyms.

---

## 4. Distribution and Sharing

Skills should be portable across tools and platforms. 
1. **Host on GitHub / Git**: Push your skills to source control.
2. **Distribute as Zips/Directories**: Users can drop the skill folder into their respective `.agents/skills/` directory or upload it securely to their web chat interfaces.

When marketing or documenting a skill, focus on the **outcome**.
- **Good**: "The XYZ skill enables teams to set up complete project workspaces in seconds."
- **Bad**: "This skill calls an MCP server multiple times sequentially."

---

## 5. Patterns and Troubleshooting

### Common Patterns
1. **Sequential Workflow Orchestration**: Step 1 -> Step 2 -> Step 3. Explicit dependencies and fallback logic.
2. **Multi-Tool Coordination**: Fetch from Figma MCP -> Save to Drive MCP -> Create task in Linear MCP.
3. **Iterative Refinement**: Generate draft -> run local `check_report.py` script -> analyze failures -> apply fixes -> loop until passing.
4. **Context-Aware Decision Trees**: Check file size -> IF > 10MB upload elsewhere -> ELSE parse immediately.

### Troubleshooting Guide

- **Skill Doesn't Trigger**: 
  - Ensure the frontmatter doesn't have unclosed quotes or missing delimiters (`---`).
  - Make sure `SKILL.md` is named exactly `SKILL.md` (case-sensitive).
  - Ask the AI agent: "When would you use the [skill name] skill?". The AI agent will quote the description back. Adjust it if needed.
- **Skill Hallucinates Details**: 
  - The context window might be flooded. Move complex definitions or API schemas out of `SKILL.md` into static files in `resources/`.
- **API/MCP Fails**:
  - Remind the AI agent in the instructions what to do if an MCP tool fails or returns empty data. Provide step-by-step debug actions the agent should take autonomously before asking the user for help.

---

## 6. Resources and References

### Core Resources
- **Skill Structure Validation**: Run your skill through automated validators to ensure anatomical correctness.
- **API Reference / SDK Docs**: Always refer to the standard agent SDK documentation for precise integrations.

### Summary Checklist for Skill Creators
- [ ] Folder named in `kebab-case`.
- [ ] `SKILL.md` file exists and is correctly capitalized.
- [ ] No extraneous files like `README.md` in the skill folder.
- [ ] YAML frontmatter uses strict `---` delimiters and avoids restricted system keywords.
- [ ] Frontmatter `description` includes exact "when to use" trigger phrase logic.
- [ ] Heavy data and API logs moved to the `resources/` mapping.
- [ ] Iterative test cases successfully pass without hallucination.
