#!/usr/bin/env python3
import os
import argparse

def init_skill(skill_name, base_path=".agents/skills"):
    skill_dir = os.path.join(base_path, skill_name)
    
    # Create directories
    directories = [
        skill_dir,
        os.path.join(skill_dir, "scripts"),
        os.path.join(skill_dir, "examples"),
        os.path.join(skill_dir, "resources")
    ]
    
    for idx, directory in enumerate(directories):
        os.makedirs(directory, exist_ok=True)
        if idx == 0:
            print(f"🚀 Initialized new skill directory: {directory}")
        else:
            print(f"📁 Created subdirectory: {directory}")
        
    # Create SKILL.md template
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    template = f"""---
name: {skill_name}
description: TODO: Add a clear description here. This serves as the primary trigger for the skill. Include "Use when..." scenarios.
---

# {skill_name}

TODO: Write clear, imperative instructions on how the AI agent should execute this task.
Focus on *how* to use the bundled scripts, resources, or examples.

## Key Instructions
1. TODO: First step for the agent
2. TODO: Second step for the agent
3. **Self-Correction**: TODO: Add a step outlining how the agent should verify its work.
"""
    if not os.path.exists(skill_md_path):
        with open(skill_md_path, "w") as f:
            f.write(template)
        print(f"📄 Created template: {skill_md_path}")
    else:
        print(f"⚠️  File already exists: {skill_md_path}")
        
    print(f"\n✅ Skill '{skill_name}' initialization complete. Customize the SKILL.md file to finish adding your skill.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize a new skill directory structure.")
    parser.add_argument("skill_name", help="The name of the skill to create")
    parser.add_argument("--path", default=".agents/skills", help="The base path where the skill should be created")
    args = parser.parse_args()
    
    init_skill(args.skill_name, args.path)
