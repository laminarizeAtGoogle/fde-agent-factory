import subprocess
import os
import sys
import argparse
import tempfile
import tarfile

REMOTE_REPO = "https://github.com/cloud-ai-fde/agent-driven-dev.git"
SKILLS_PREFIX = "skills/"

def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()

def list_skills():
    # Use ls-remote and ls-tree if we don't want to clone, 
    # but ls-tree requires a local tree or a fetch.
    # A cleaner way is to use ls-tree on the remote branch if possible.
    # Since we likely have the remote fetched as 'agent-driven-development'
    
    cmd = f"git ls-tree -d agent-driven-development/main:{SKILLS_PREFIX}"
    output = run_command(cmd)
    if not output:
        # Fallback to local if remote fetch fails or ref is missing
        cmd = f"git ls-tree -d HEAD:{SKILLS_PREFIX}"
        output = run_command(cmd)
    
    if output:
        skills = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                skills.append(parts[3])
        return sorted(skills)
    return []

def install_skill(skill_name, target_root):
    full_skill_path = os.path.join(SKILLS_PREFIX, skill_name)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = os.path.join(tmp_dir, "skill.tar")
        archive_cmd = f"git archive --remote={REMOTE_REPO} main {full_skill_path} > {archive_path}"
        print(f"Archiving {full_skill_path} from remote...")
        if run_command(archive_cmd) is None:
            return False
        
        # Extract to temp dir
        with tarfile.open(archive_path) as tar:
            tar.extractall(path=tmp_dir)
            
        # The contents will be in tmp_dir/.agents/skills/skill_name
        src_path = os.path.join(tmp_dir, full_skill_path)
        if not os.path.exists(src_path):
            print(f"Error: Could not find skill contents in archive at {src_path}")
            return False
            
        # Final destination: target_root/skill_name
        dest_path = os.path.join(os.path.expanduser(target_root), skill_name)
        os.makedirs(os.path.split(dest_path)[0], exist_ok=True)
        
        print(f"Installing to {dest_path}...")
        if os.path.exists(dest_path):
            import shutil
            shutil.rmtree(dest_path)
            
        import shutil
        shutil.move(src_path, dest_path)
            
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill Manager")
    parser.add_argument("command", choices=["list", "install"])
    parser.add_argument("skill", nargs="?", help="Name of the skill to install")
    parser.add_argument("--target", default=".", help="Target directory for installation")
    
    args = parser.parse_args()
    
    if args.command == "list":
        skills = list_skills()
        if skills:
            print("\n".join(skills))
        else:
            print("No skills found.")
    elif args.command == "install":
        if not args.skill:
            print("Error: Specify a skill name to install.")
            sys.exit(1)
        if install_skill(args.skill, args.target):
            print(f"Successfully installed {args.skill}")
        else:
            print(f"Failed to install {args.skill}")
