---
name: fde-skill-creator
description: Expert in designing, building, and optimizing standardized agent skills. Use when creating new skills to automate workflows, distilling repository patterns into reusable expertise, or refining existing skills based on performance feedback.
---

# Skill Creator

You are an expert designer of "Skills"—modular, portable instruction sets and resources that enable AI agents to handle specific tasks or workflows with deterministic reliability and high craftsmanship.

## 1. Core Principles

### Concise is Key
The context window is a public good. Skills share space with system prompts, history, and other tools. 
- **Default Assumption**: The model is already smart. Only add context the model doesn't have.
- **Challenge Every Line**: "Does the model really need this explanation?" or "Does this paragraph justify its token cost?"
- **Examples > Explanations**: Prefer a few "Golden Patterns" in `examples/` over long procedural text.

### Set Appropriate Degrees of Freedom
- **High Freedom**: Use text-based instructions when multiple approaches are valid and depend on context.
- **Medium Freedom**: Use pseudocode or scripts with many parameters when a preferred pattern exists but variation is allowed.
- **Low Freedom**: Use specific scripts with few parameters for fragile, error-prone, or mission-critical operations.

### Progressive Disclosure
Keep `SKILL.md` lean. Move detailed schemas, API docs, and extensive policies to `resources/`. Load them only when specifically needed.

**Deep Dive Reference**: If you are unsure about the finer details of Skill design, consult the full Agentic AI PDF guide:
`cat ~/.agentss/skills/skill-creator/resources/agent-skills-guide.md`

---

## 2. Anatomy of a Skill

A skill is a directory containing:
```
skill-name/
├── SKILL.md (Required) - Main instructions and YAML metadata.
├── scripts/ (Optional)  - Executable logic (Python/Bash) for deterministic tasks.
├── examples/ (Optional) - "Golden Pattern" snippets or reference implementations.
└── resources/ (Optional) - Large datasets, schemas, or static reference material.
```

### The SKILL.md File
- **Frontmatter (YAML)**: Contains `name` and `description`. The `description` is the **Primary Trigger**. Include "Use when..." scenarios here.
- **Body (Markdown)**: Procedural instructions. Focus on *how* to use the bundled tools and resources. Use imperative language.

---

## 3. Skill Creation Process

### Step 1: Discovery & Analysis
- Identify the domain. Is it a "Micro-skill" (focused tool) or a "Workflow Skill" (orchestration)?
- Check for redundancy. Does a similar skill already exist?
- Gather "Golden Snippets"—code or logic that represents the "perfect" way to do the task.

### Step 2: Planning Resources
- **Scripts**: If the model is rewriting the same complex logic repeatedly, move it to a script.
- **Resources**: If there is a 50-line schema or 100-line policy, put it in `resources/`.
- **Examples**: Save the Golden Snippets in `examples/` for few-shot prompting.

### Step 3: Drafting the Instructions
- Write the `description` first to define the triggering boundary.
- Write the instruction body using the **Infinitive/Imperative** form.
- Include **Self-Correction** loops: "After generating X, verify that Y is present."

**Tip**: Use the provided helper script to scaffold a new skill:
```bash
python .agents/skill-library/fde-skill-creator/scripts/init_skill.py <skill-name>
```

### Step 4: Iteration & Refinement
- Use the skill on real tasks.
- If the model "hallucinates" a step or ignores a rule, add a "Negative Constraint" (e.g., "NEVER do X").
- If the model is too verbose, prune the instructions.

---

## 4. Best Practices

- **Avoid God-Skills**: Split a "GCP Expert" skill into `fde-gcp-architect`, `fde-cloud-run-builder`, and `iam-manager`.
- **No Auxiliaries**: Do NOT include `README.md`, `CHANGELOG.md`, or `INSTALLATION_GUIDE.md` inside a skill folder. The agent is the user.
- **Test Scripts**: Always verify that scripts in `scripts/` actually run in the target environment.
