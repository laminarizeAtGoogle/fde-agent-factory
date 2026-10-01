#!/usr/bin/env python3
"""
Pre-command hook script: Architecture Documentation & Diagram Gate.
Intercepts tool executions (specifically run_command), detects git push commands,
and executes a subagent slash command (/update-architecture-docs) to ensure that:
1. The './docs' folder exists and contains an architecture diagram utilizing the Mermaid format.
2. The architecture documentation and diagram have been updated with all changes comprised in the git push action.
3. The Google OKF (Operational Knowledge Framework) Knowledge Base is synchronized.
4. No uncommitted modifications to './docs' are left behind.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys

DEFAULT_DOCS_DIR = "docs"
DEFAULT_DIAGRAM_FILES = [
    "architecture.md",
    "architecture_diagram.mmd",
]

# Non-architectural files that do not strictly require architecture diagram updates
IGNORABLE_EXTENSIONS = {
    ".lock", ".log", ".tmp",
}
IGNORABLE_FILES = {
    ".openspec-target",
    ".gitignore",
    ".gitkeep",
    ".gitmessage.txt",
    ".gitattributes",
    "AGENTS.md",
    "GEMINI.md",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
}


def get_git_aliases(cwd: str) -> dict:
    """Retrieves git aliases configured in repository or globally."""
    try:
        res = subprocess.run(
            ["git", "config", "--get-regexp", r"^alias\."],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        aliases = {}
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key = parts[0].replace("alias.", "")
                    aliases[key] = parts[1]
        return aliases
    except Exception:
        return {}


def get_git_subcommands(command_line: str) -> list:
    """Extracts git subcommands from a compound shell command line."""
    subcommands = []
    git_segments = re.finditer(
        r"(?:^|[;&|\n])\s*(?:/[^\s;&|]*/)?git\b(?P<args>[^;&|\n]*)",
        command_line,
    )
    flags_with_arg = {
        "-C", "-c", "--git-dir", "--work-tree",
        "--namespace", "--exec-path", "--config-env",
    }
    for m in git_segments:
        raw_args = m.group("args").strip()
        try:
            tokens = shlex.split(raw_args)
        except Exception:
            tokens = raw_args.split()

        idx = 0
        while idx < len(tokens):
            tok = tokens[idx]
            if tok in flags_with_arg:
                idx += 2
                continue
            elif any(tok.startswith(f"{f}=") for f in flags_with_arg):
                idx += 1
                continue
            elif tok.startswith("-"):
                idx += 1
                continue
            else:
                subcommands.append(tok)
                break
            idx += 1
    return subcommands


def resolve_alias_to_subcommand(subcmd: str, aliases: dict, depth: int = 0) -> str:
    """Recursively resolves a git subcommand through aliases."""
    if depth > 5:
        return subcmd
    if subcmd in aliases:
        expansion = aliases[subcmd].strip()
        if expansion.startswith("!"):
            return expansion
        first_word = expansion.split()[0] if expansion.split() else expansion
        return resolve_alias_to_subcommand(first_word, aliases, depth + 1)
    return subcmd


DEFAULT_PUSH_PATTERN = (
    r"(?:^|[;&|\n])\s*(?:/[^\s;&|]*/)?git\b"
    r"(?:\s+-[^\s]+|\s+--[^\s]+|\s+-[a-zA-Z]\s+[^\s]+)*\s+push\b"
)


def is_git_push_command(
    command_line: str,
    cwd: str,
    pattern: str = DEFAULT_PUSH_PATTERN,
) -> bool:
    """Checks if command_line executes 'git push' directly or via alias expansion."""
    if not command_line:
        return False
    if re.search(pattern, command_line, re.IGNORECASE):
        return True

    subcommands = get_git_subcommands(command_line)
    if not subcommands:
        return False

    aliases = get_git_aliases(cwd)
    if not aliases:
        return False

    for subcmd in subcommands:
        resolved = resolve_alias_to_subcommand(subcmd, aliases)
        if resolved == "push" or f" push " in f" {resolved} " or resolved.startswith("push "):
            return True

    return False


def check_diagram_is_mermaid(file_path: str) -> tuple[bool, str]:
    """Verifies that an architecture diagram file conforms to Mermaid standards and avoids ASCII art."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return False, f"Failed to read diagram file '{file_path}': {e}"

    lower = os.path.basename(file_path).lower()

    # Mermaid native file (.mmd, .mermaid) check
    if lower.endswith(".mmd") or lower.endswith(".mermaid"):
        if not re.search(r"(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|gitGraph|journey|mindmap|quadrantChart|xychart-beta)", content):
            return False, f"Mermaid model '{file_path}' must contain valid Mermaid declarations (flowchart, graph, sequenceDiagram, etc.)."
        return True, ""

    # Markdown documentation check
    if lower.endswith(".md"):
        # Check for banned ASCII art box drawing masquerading as diagrams
        has_ascii_box = bool(re.search(r"\+[=-]{10,}\+", content)) and bool(re.search(r"\|[ ]{10,}\|", content))
        if has_ascii_box and "```mermaid" not in content:
            return False, (
                f"Architecture documentation '{file_path}' contains markdown/ASCII box drawing instead of "
                f"the mandatory Mermaid diagram format. Please replace ASCII art with canonical Mermaid "
                f"declarations (```mermaid ... ```)."
            )

        # Must contain mermaid block or reference
        has_mermaid_block = bool(re.search(r"```mermaid\s*\n.*?\n```", content, re.DOTALL))
        if not has_mermaid_block:
            if "```mermaid" not in content and "mermaid" not in content.lower():
                return False, (
                    f"Architecture documentation '{file_path}' must contain a valid Mermaid diagram "
                    f"(```mermaid ... ```) as the authoritative diagram platform."
                )

    return True, ""


# Backward-compatible alias
check_diagram_is_dendrite = check_diagram_is_mermaid


def verify_docs_directory(cwd: str, docs_dir_name: str = "docs") -> tuple[bool, str]:
    """Verifies that the docs directory exists, contains a Mermaid diagram, and valid OKF KB."""
    docs_path = os.path.join(cwd, docs_dir_name)
    if not os.path.isdir(docs_path):
        return (
            False,
            f"Pre-push architecture check failed: Missing './{docs_dir_name}' directory.\n"
            f"Repository policy requires that architecture documentation and a Mermaid architecture diagram "
            f"be maintained within './{docs_dir_name}/'.\n"
            f"Please create './{docs_dir_name}/architecture.md' (containing a ```mermaid diagram) before pushing.",
        )

    # Check for architecture diagram files
    found_diagram = False
    valid_files = []
    try:
        entries = os.listdir(docs_path)
    except Exception as e:
        return False, f"Failed to read './{docs_dir_name}': {e}"

    for entry in entries:
        full_path = os.path.join(docs_path, entry)
        if not os.path.isfile(full_path):
            continue

        lower = entry.lower()
        if (
            "architecture" in lower
            or "diagram" in lower
            or lower.endswith(".mmd")
            or lower.endswith(".mermaid")
        ):
            # Ignore legacy dendrite files
            if lower.endswith(".dendrite") or lower.endswith(".dendrite.yaml") or lower.endswith(".dendrite.yml"):
                continue

            # Check content is non-empty
            size = os.path.getsize(full_path)
            if size > 50:
                is_mermaid, mermaid_err = check_diagram_is_mermaid(full_path)
                if not is_mermaid:
                    return False, f"Pre-push architecture check failed: {mermaid_err}"
                found_diagram = True
                valid_files.append(entry)

    if not found_diagram:
        return (
            False,
            f"Pre-push architecture check failed: No valid architecture diagram found in './{docs_dir_name}/'.\n"
            f"The './{docs_dir_name}' folder must contain an architecture documentation file with a Mermaid diagram "
            f"(e.g., 'architecture.md' or 'architecture_diagram.mmd') utilizing the Mermaid format.\n"
            f"Please author your architecture diagram using Mermaid and save it in './{docs_dir_name}/'.",
        )

    # Check for Google OKF Knowledge Base
    kb_path = os.path.join(docs_path, "knowledge_base")
    if not os.path.isdir(kb_path):
        return (
            False,
            f"Pre-push architecture check failed: Missing Google OKF Knowledge Base in './{docs_dir_name}/knowledge_base/'.\n"
            f"Repository policy requires an Operational Knowledge Framework (OKF) knowledge base where each "
            f"architectural component has an entry under './{docs_dir_name}/knowledge_base/'.\n"
            f"Please ensure './{docs_dir_name}/knowledge_base/' exists with component documentation.",
        )

    # Verify that KB has valid OKF entries (in components/ or subcategory directories)
    valid_okf_files = []
    try:
        for root, _, files in os.walk(kb_path):
            for f in files:
                if f.endswith(".md") and not f.startswith("TEMPLATE") and not f.startswith("OKF_SPEC") and not f.startswith("README"):
                    full_f = os.path.join(root, f)
                    if os.path.getsize(full_f) > 50:
                        valid_okf_files.append(f)
    except Exception as e:
        return False, f"Failed to inspect './{docs_dir_name}/knowledge_base/': {e}"

    if not valid_okf_files:
        return (
            False,
            f"Pre-push architecture check failed: No valid OKF entries found in './{docs_dir_name}/knowledge_base/'.\n"
            f"Each architectural component must have an OKF entry conforming to the Google OKF specification.",
        )

    return True, ""


def check_uncommitted_docs_changes(cwd: str, docs_dir_name: str = "docs") -> list[str]:
    """Checks if there are unstaged or uncommitted changes in the docs directory."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "--", docs_dir_name],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            return lines
    except Exception:
        pass
    return []


def get_outgoing_commit_range(cwd: str) -> str:
    """Determines the git commit range for the push."""
    # 1. Try tracking upstream @{u}
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            return "@{u}..HEAD"
    except Exception:
        pass

    # Get current branch name
    current_branch = ""
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            current_branch = res.stdout.strip()
    except Exception:
        pass

    # 2. Try remote tracking branches (never compare local branch to itself)
    remote_refs = []
    if current_branch:
        remote_refs.append(f"origin/{current_branch}")
    remote_refs.extend(["origin/main", "origin/master", "origin/HEAD"])

    for ref in remote_refs:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--verify", ref],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return f"{ref}..HEAD"
        except Exception:
            pass

    # 3. Fallback: check if parent commit exists
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD~1"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            return "HEAD~1..HEAD"
    except Exception:
        pass

    return "HEAD"


def get_changed_files_in_range(cwd: str, commit_range: str) -> list[str]:
    """Retrieves list of changed files in the specified commit range."""
    if commit_range == "HEAD":
        # Root commit: inspect files in HEAD
        try:
            res = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
        except Exception:
            pass

    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", commit_range],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            return [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
    except Exception:
        pass

    # Fallback: check status of committed HEAD vs previous
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            return [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
    except Exception:
        pass

    return []


def is_significant_project_file(file_path: str, docs_dir: str = "docs") -> bool:
    """Checks if a file represents significant project code, infrastructure, or configuration."""
    clean = file_path.replace("\\", "/").strip()
    if clean.startswith(f"{docs_dir}/") or clean == docs_dir:
        return False

    base = os.path.basename(clean)
    if base in IGNORABLE_FILES:
        return False

    ext = os.path.splitext(clean)[1].lower()
    if ext in IGNORABLE_EXTENSIONS:
        return False

    return True


def find_agy_binary():
    """Finds the agy CLI binary path."""
    which_path = shutil.which("agy")
    if which_path:
        return which_path

    common_paths = [
        os.path.expanduser("~/.gemini/bin/agy"),
        os.path.expanduser("~/.gemini/antigravity/bin/agy"),
        "/usr/local/bin/agy",
    ]
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def invoke_subagent_update(
    cwd: str,
    slash_cmd: str,
    command_line: str,
    timeout_sec: int = 60,
) -> tuple[bool, str]:
    """Invokes the subagent slash command to update the architecture diagram and KB."""
    mock_result = os.environ.get("MOCK_SUBAGENT_RESULT")
    if mock_result:
        if mock_result.lower() == "pass":
            return True, "Subagent update passed (mocked)."
        else:
            return False, os.environ.get(
                "MOCK_SUBAGENT_REASON",
                f"Subagent '{slash_cmd}' failed to update architecture docs (mocked).",
            )

    agy_bin = find_agy_binary()
    if not agy_bin:
        return False, "agy CLI binary not found."

    cmd_name = slash_cmd if slash_cmd.startswith("/") else f"/{slash_cmd}"
    prompt = (
        f"{cmd_name} Intercepted '{command_line}'. "
        f"Outgoing changes detected in repository without synchronized architecture documentation. "
        f"Update the Mermaid architecture diagram and Google OKF Knowledge Base before pushing."
    )

    agy_cmd = [
        agy_bin,
        "-p",
        prompt,
        "--print-timeout",
        f"{timeout_sec}s",
    ]

    try:
        proc = subprocess.run(
            agy_cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec + 5,
        )
        combined = f"{proc.stdout}\n{proc.stderr}".strip()
        if (
            "authentication required" in combined.lower()
            or "not logged into antigravity" in combined.lower()
        ):
            sys.stderr.write(
                "Warning: agy CLI is not authenticated. Subagent auto-update skipped.\n"
            )
            return False, "agy CLI is not authenticated."

        if proc.returncode != 0:
            return False, combined or "Subagent execution returned non-zero code."

        if "ARCHITECTURE_DOCS_UPDATE: FAILED" in proc.stdout:
            return False, proc.stdout.strip()

        return True, proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"Subagent timed out after {timeout_sec}s."
    except Exception as e:
        return False, f"Subagent invocation failed: {e}"


def evaluate_architecture_docs_gate(cwd: str, config: dict, command_line: str = "git push") -> tuple[str, str]:
    """Evaluates whether git push should be allowed or denied based on architecture docs state."""
    docs_dir = config.get("docsDir", DEFAULT_DOCS_DIR)
    slash_cmd = config.get("slashCommand", "update-architecture-docs")
    timeout_sec = config.get("timeoutSeconds", 60)

    # Step 1: Verify docs directory and Mermaid diagram exist
    docs_valid, docs_err = verify_docs_directory(cwd, docs_dir)
    if not docs_valid:
        return "deny", docs_err

    # Step 2: Check for uncommitted changes in docs/
    uncommitted_docs = check_uncommitted_docs_changes(cwd, docs_dir)
    if uncommitted_docs:
        lines_summary = "\n".join(f"  {line}" for line in uncommitted_docs)
        return (
            "deny",
            f"Pre-push architecture check failed: Uncommitted updates detected in './{docs_dir}/'.\n"
            f"Modified/untracked files:\n{lines_summary}\n\n"
            f"Please stage and commit your architecture updates before pushing:\n"
            f"  git add {docs_dir}/ && git commit -m 'docs: update architecture diagram and documentation'",
        )

    # Step 3: Determine commit range
    commit_range = get_outgoing_commit_range(cwd)
    changed_files = get_changed_files_in_range(cwd, commit_range)

    # If no files changed in the push range (e.g. branch is already up to date)
    if not changed_files:
        return "allow", ""

    # Step 4: Categorize changed files
    project_files = [f for f in changed_files if is_significant_project_file(f, docs_dir)]
    docs_files = [f for f in changed_files if f.startswith(f"{docs_dir}/")]

    # If significant project files changed and docs were not updated, invoke subagent slash command!
    if project_files and not docs_files:
        changed_list = "\n".join(f"  - {f}" for f in project_files[:15])
        if len(project_files) > 15:
            changed_list += f"\n  - ... and {len(project_files) - 15} more files"

        # Invoke subagent via slash command
        subagent_success, subagent_msg = invoke_subagent_update(
            cwd=cwd,
            slash_cmd=slash_cmd,
            command_line=command_line,
            timeout_sec=timeout_sec,
        )

        if subagent_success:
            # Re-check if docs directory and Mermaid diagram are valid
            recheck_valid, recheck_err = verify_docs_directory(cwd, docs_dir)
            if not recheck_valid:
                return "deny", f"Subagent completed but docs validation failed: {recheck_err}"
            # Re-check uncommitted docs changes
            recheck_uncommitted = check_uncommitted_docs_changes(cwd, docs_dir)
            if recheck_uncommitted:
                lines_sum = "\n".join(f"  {l}" for l in recheck_uncommitted)
                return (
                    "deny",
                    f"Subagent updated documentation in './{docs_dir}/', but files need to be committed before pushing:\n"
                    f"{lines_sum}\n\n"
                    f"Please run:\n  git add {docs_dir}/ && git commit -m 'docs: update architecture diagram and KB'",
                )
            return "allow", ""

        # Subagent did not run or failed to auto-update
        cmd_name = slash_cmd if slash_cmd.startswith("/") else f"/{slash_cmd}"
        return (
            "deny",
            f"Pre-push architecture check failed: Changes are being pushed to GitHub, but architecture docs "
            f"in './{docs_dir}/' were not updated!\n\n"
            f"Repository Policy:\n"
            f"Whenever modifying code, infrastructure, or workflows, the architecture documentation and Mermaid "
            f"diagram in './{docs_dir}/' must be updated to reflect all changes comprised in the git push action.\n\n"
            f"Project files changed in this push ({commit_range}):\n{changed_list}\n\n"
            f"Subagent Execution ({cmd_name}):\n{subagent_msg}\n\n"
            f"Action Required for Agent:\n"
            f"1. Run the subagent slash command `{cmd_name}` to automatically analyze diffs and update the Mermaid diagram and OKF Knowledge Base.\n"
            f"2. Stage and commit the documentation: `git add {docs_dir}/ && git commit -m 'docs: update architecture diagram (Mermaid) and OKF KB'`\n"
            f"3. Re-run '{command_line}'.",
        )

    # Either docs were updated alongside code, or only docs were modified
    return "allow", ""


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return
        payload = json.loads(raw_input)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to parse PreToolUse payload in check_architecture_docs: {e}\n")
        print(json.dumps({"decision": "allow"}))
        return

    # Extract command line
    tool_call = payload.get("toolCall", {})
    args = tool_call.get("args", {})
    command_line = args.get("CommandLine", "")

    # Determine workspace directory (prefer explicit Cwd from toolCall args if present)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    arg_cwd = args.get("Cwd", "")
    workspace_paths = payload.get("workspacePaths", [])
    if arg_cwd and os.path.isdir(arg_cwd):
        cwd = arg_cwd
    elif workspace_paths and os.path.isdir(workspace_paths[0]):
        cwd = workspace_paths[0]
    else:
        cwd = os.path.abspath(os.path.join(script_dir, "..", ".."))

    # Load configuration
    config_path = os.path.join(script_dir, "check-architecture-docs-config.json")
    config = {
        "targetCommandPattern": r"(?:^|[;&|]\s*)\s*git(?:\s+-[^\s]+|\s+--[^\s]+|\s+-[a-zA-Z]\s+[^\s]+)*\s+push\b",
        "docsDir": DEFAULT_DOCS_DIR,
        "diagramFiles": DEFAULT_DIAGRAM_FILES,
        "denyOnFailure": True,
        "timeoutSeconds": 60,
        "slashCommand": "update-architecture-docs",
    }
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to read {config_path}: {e}\n")

    pattern = config.get("targetCommandPattern", r"(^|\b)git\s+push\b")

    # Fast check: Only evaluate if the command is git push
    if not is_git_push_command(command_line, cwd, pattern):
        print(json.dumps({"decision": "allow"}))
        return

    # Mock override for test suites
    mock_decision = os.environ.get("MOCK_ARCH_DOCS_DECISION")
    if mock_decision:
        if mock_decision.lower() == "allow":
            print(json.dumps({"decision": "allow"}))
        else:
            print(json.dumps({
                "decision": "deny",
                "reason": os.environ.get("MOCK_ARCH_DOCS_REASON", "Mocked architecture check denial"),
            }))
        return

    decision, reason = evaluate_architecture_docs_gate(cwd, config, command_line=command_line)
    if decision == "deny":
        print(json.dumps({"decision": "deny", "reason": reason}))
    else:
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
