#!/usr/bin/env python3
import os
import argparse
import sys

def run_audit(skill_dir=".agents/skills", auto_fix=False):
    aux_files = ["README.MD", "INSTALLATION_GUIDE.MD", "CHANGELOG.MD", "QUICK_REFERENCE.MD"]
    valid_subdirs = {"scripts", "examples", "resources", "references", "__pycache__"}

    violations = {}
    error_skills_count = 0
    
    print(f"🔍 Auditing skills in {skill_dir}")

    for skill_name in sorted(os.listdir(skill_dir)):
        path = os.path.join(skill_dir, skill_name)
        if os.path.isdir(path):
            skill_viols = []
            has_error = False
            skill_md = os.path.join(path, "SKILL.md")
            
            # 1. Check for SKILL.md existence
            if not os.path.exists(skill_md):
                skill_viols.append("❌ Missing SKILL.md")
                has_error = True
                violations[skill_name] = skill_viols
                error_skills_count += 1
                continue
                
            # 2. Check for Aux files
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.upper() in aux_files:
                        msg = f"❌ Contains auxiliary file '{file}' in {os.path.relpath(root, path)}"
                        if auto_fix:
                            os.remove(os.path.join(root, file))
                            msg += " (Auto-fixed: Removed)"
                        skill_viols.append(msg)
                        has_error = True
                        
            # 3. Check for Frontmatter in SKILL.md (Triggers)
            try:
                with open(skill_md, "r") as f:
                    content = f.read()
                    
                if not content.startswith("---\n"):
                    skill_viols.append("❌ Missing YAML frontmatter in SKILL.md")
                    has_error = True
                else:
                    frontmatter_end = content.find("\n---\n", 4)
                    if frontmatter_end == -1:
                        skill_viols.append("❌ Malformed YAML frontmatter in SKILL.md")
                        has_error = True
                    else:
                        frontmatter = content[4:frontmatter_end]
                        if "name:" not in frontmatter:
                            skill_viols.append("❌ Missing 'name:' in frontmatter")
                            has_error = True
                        if "description:" not in frontmatter:
                            skill_viols.append("❌ Missing 'description:' in frontmatter")
                            has_error = True
                            
            except Exception as e:
                skill_viols.append(f"❌ Failed to read SKILL.md: {e}")
                has_error = True
                        
            # 4. Check for invalid subdirectories
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and item not in valid_subdirs:
                    skill_viols.append(f"⚠️ Non-standard subdirectory '{item}'")
            
            # 5. Check size limit
            if os.path.exists(skill_md):
                size = len(content)
                if size > 3000:
                    skill_viols.append(f"⚠️ SKILL.md is quite large ({size} chars). Progressive Disclosure check failed.")
                    
            if skill_viols:
                violations[skill_name] = skill_viols
                if has_error:
                    error_skills_count += 1

    if not violations:
        print("\n✅ All skills passed documentation standards!")
    elif error_skills_count == 0:
        print("\n⚠️  Skills passed structural audit, but with quality warnings:")
        for skill, viols in violations.items():
            print(f"\n📁 {skill}:")
            for v in viols:
                print(f"  {v}")
    else:
        print(f"\n❌ Audit failed with {error_skills_count} skills containing critical errors:")
        for skill, viols in violations.items():
            print(f"\n📁 {skill}:")
            for v in viols:
                print(f"  {v}")
                
    return error_skills_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit agent skills against Google Agent's structural standards.")
    parser.add_argument("--dir", default=".agents/skills", help="Directory containing the skills")
    parser.add_argument("--fix", action="store_true", help="Auto-fix trivial violations (like deleting auxiliary documentation)")
    args = parser.parse_args()
    
    sys.exit(run_audit(args.dir, args.fix))
