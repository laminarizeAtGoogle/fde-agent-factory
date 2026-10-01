#!/usr/bin/env python3
"""
Pre-command hook script for Antigravity.
Intercepts tool executions (specifically run_command), detects matching commands
(such as 'git push'), checks repository files and diffs for sensitive credentials
(cookies, JWTs, API keys), and launches a subagent slash command before allowing or denying.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svgz", ".pdf",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".whl", ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
    ".bin", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".mp3",
    ".mp4", ".mov", ".avi", ".db", ".sqlite", ".sqlite3"
}

DEFAULT_EXCLUDE_FILES = {
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "Gemfile.lock",
    "composer.lock",
    ".terraform.lock.hcl",
    "test_pre_command_hook.py",
    "pre_command_hook.py",
    "sanitize_repo.sh",
    "compliance-guide.md",
    ".agents/skills/fde-cross-compliance/SKILL.md",
    ".agents/skills/fde-git-push/SKILL.md",
    ".agents/skill-library/fde-git-push/SKILL.md",
    ".agents/skills/git-push-sanitization-check/SKILL.md",
    "skills/fde-cross-compliance/SKILL.md",
    "skills/fde-git-push/SKILL.md",
    "skill-library/fde-git-push/SKILL.md",
    "skills/git-push-sanitization-check/SKILL.md",
}

SENSITIVE_FILENAME_PATTERN = re.compile(
    r"(?:^|/)(?:\.env|\.env\.[a-zA-Z0-9_.-]+|id_rsa|id_ed25519|.*\.pem|.*\.key|credentials\.json|client_secret[a-zA-Z0-9_.-]*\.json|(?:.*[-_])?service[-_]?account[a-zA-Z0-9_.-]*\.json|cookies\.txt|skill-runs\.jsonl)$",
    re.IGNORECASE,
)

# Credential and sensitive content patterns organized by category
CREDENTIAL_PATTERNS = {
    "cookies": [
        (
            "Cookie Header",
            re.compile(
                r"""(?i)(?:^|[\s"'\r\n])(?:set-cookie|cookie)\s*[:=]\s*["']?([^"'\r\n;]{10,})["']?"""
            ),
        ),
        (
            "Session Cookie Token",
            re.compile(
                r"""(?i)\b(?:connect\.sid|sessionid|jsessionid|phpsessid|_session_id|remember_token)\s*=\s*["']?([a-zA-Z0-9_\-\.%]{12,})["']?"""
            ),
        ),
        (
            "Cookie Variable",
            re.compile(
                r"""(?i)\b(?:auth_cookie|session_cookie|cookie_token)\s*[:=]\s*["']([^"'\r\n;]{10,})["']"""
            ),
        ),
    ],
    "jwt": [
        (
            "JWT Token",
            re.compile(
                r"\b(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"
            ),
        ),
        (
            "JWT Variable Assignment",
            re.compile(
                r"""(?i)\b(?:jwt|jwt_token|id_token|access_token|refresh_token)\s*[:=]\s*["'](eyJ[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]+)*)["']"""
            ),
        ),
    ],
    "api_keys": [
        ("Google API Key", re.compile(r"\b(AIza[0-9A-Za-z-_]{35})\b")),
        (
            "Google OAuth Access Token",
            re.compile(r"\b(ya29\.[0-9A-Za-z_-]{16,})\b"),
        ),
        (
            "GCP Service Account Key",
            re.compile(r'("type"\s*:\s*"service_account")'),
        ),
        (
            "GCP Service Account Private Key ID",
            re.compile(r'(?i)"private_key_id"\s*:\s*"([a-f0-9]{20,})"'),
        ),
        (
            "GitHub Token",
            re.compile(
                r"\b((?:ghp|gho|ghu|ghs|ghr)_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})\b"
            ),
        ),
        (
            "OpenAI API Key",
            re.compile(r"\b(sk-(?:proj-|svcacct-)?[a-zA-Z0-9_-]{20,})\b"),
        ),
        ("Anthropic API Key", re.compile(r"\b(sk-ant-[a-zA-Z0-9_-]{20,})\b")),
        (
            "AWS Access Key ID",
            re.compile(
                r"\b((?:A3T[A-Z0-9]|AKIA|ABIA|ACCA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[0-9A-Z]{16})\b"
            ),
        ),
        (
            "AWS Secret Key",
            re.compile(
                r"""(?i)\b(?:aws_secret_access_key|aws_secret_key)\s*[:=]\s*["']([A-Za-z0-9/+=]{40})["']"""
            ),
        ),
        ("Slack Token", re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b")),
        (
            "Stripe API Key",
            re.compile(r"\b((?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,})\b"),
        ),
        (
            "SendGrid API Key",
            re.compile(r"\b(SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43})\b"),
        ),
        ("HuggingFace Token", re.compile(r"\b(hf_[a-zA-Z0-9]{34})\b")),
        (
            "Private Key Block",
            re.compile(
                r"(-----BEGIN (?:(?:RSA|EC|OPENSSH|DSA|PGP|[A-Z0-9_-]+)\s+)?PRIVATE KEY-----)"
            ),
        ),
        (
            "Generic API Key / Secret",
            re.compile(
                r"""(?i)\b(?:api[_-]?key|secret[_-]?key|auth[_-]?token|client[_-]?secret)\s*[:=]\s*["']([a-zA-Z0-9_\-\.]{16,})["']"""
            ),
        ),
        (
            "Bearer Token",
            re.compile(r"""(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{20,})\b"""),
        ),
    ],
    "oauth_tokens": [
        (
            "Google OAuth Access Token",
            re.compile(r"\b(ya29\.[0-9A-Za-z_-]{16,})\b"),
        ),
    ],
    "service_accounts": [
        (
            "GCP Service Account Key",
            re.compile(r'("type"\s*:\s*"service_account")'),
        ),
        (
            "GCP Service Account Private Key ID",
            re.compile(r'(?i)"private_key_id"\s*:\s*"([a-f0-9]{20,})"'),
        ),
    ],
    "internal_google": [
        (
            "Internal Go Shortlink",
            re.compile(r"(?<![a-zA-Z0-9_./-])(go/[a-zA-Z0-9_-]{2,})\b"),
        ),
        (
            "Internal Buganizer ID",
            re.compile(r"(?<![a-zA-Z0-9_./-])(b/[0-9]{6,})\b"),
        ),
        (
            "Internal Changelist ID",
            re.compile(r"(?<![a-zA-Z0-9_./-])(cl/[0-9]{6,})\b"),
        ),
        (
            "Internal YAQS Link",
            re.compile(r"(?<![a-zA-Z0-9_./-])(yaqs/[0-9]{4,})\b"),
        ),
        (
            "Internal g3doc Reference",
            re.compile(
                r"\b(g3doc(?:\.corp\.google\.com)?/[a-zA-Z0-9_./-]+)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "Internal google3 / Depot Path",
            re.compile(
                r"(//depot/google3[^\s\"'`)]*|\bgoogle3/[a-zA-Z0-9_./-]+)"
            ),
        ),
        (
            "Internal Corp Hostname",
            re.compile(
                r"\b([a-zA-Z0-9][a-zA-Z0-9_.-]*\.corp\.google\.com)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "Internal Piper Path",
            re.compile(r"(piper:///[a-zA-Z0-9_./-]+)"),
        ),
    ],
}

ALLOWED_INTERNAL_REFERENCES = {
    "go/wif",
    "go/cross",
    "b/123456",
    "cl/123456",
    "yaqs/123456",
}


def is_likely_placeholder(val: str) -> bool:
    """Checks if a matched string is an obvious placeholder rather than a real secret."""
    lower = val.lower().strip("\"' \t\r\n")
    if lower in ALLOWED_INTERNAL_REFERENCES:
        return True
    if "..." in lower:
        return True
    placeholder_keywords = [
        "placeholder", "example", "dummy", "fake", "sample",
        "your_", "your-", "replace", "changeme", "change_this",
        "todo", "mock", "demo", "xxx", "insert_", "<your", "my-api-key",
    ]
    if any(kw in lower for kw in placeholder_keywords):
        return True
    if lower.startswith("<") and lower.endswith(">"):
        return True
    if lower.startswith("${") or "process.env." in lower or "os.environ" in lower:
        return True
    # Low entropy / repeated characters
    if len(set(lower)) <= 2:
        return True
    return False


def redact_secret(val: str) -> str:
    """Safely redacts a sensitive value for reporting without leaking it."""
    cleaned = val.strip("\"' \t\r\n")
    if len(cleaned) <= 8:
        return "[REDACTED]"
    return f"{cleaned[:4]}...{cleaned[-4:]} [REDACTED]"


def is_binary_file(filepath: str) -> bool:
    """Checks whether a file appears to be binary."""
    _, ext = os.path.splitext(filepath)
    if ext.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8000)
            return b"\x00" in chunk
    except Exception:
        return False


def get_active_patterns(enabled_types: list):
    """Returns a combined, deduplicated list of (label, regex) for active credential types."""
    patterns = []
    seen_labels = set()
    for cat in enabled_types:
        if cat in CREDENTIAL_PATTERNS:
            for label, pat in CREDENTIAL_PATTERNS[cat]:
                if label not in seen_labels:
                    seen_labels.add(label)
                    patterns.append((label, pat))
    return patterns


def scan_file_for_credentials(filepath: str, rel_path: str, active_patterns: list) -> list:
    """Scans an individual file on disk for credentials."""
    findings = []
    if SENSITIVE_FILENAME_PATTERN.search(rel_path):
        findings.append({
            "file": rel_path,
            "line": 1,
            "type": "Sensitive File Pattern",
            "preview": f"File name '{os.path.basename(rel_path)}' is typically reserved for sensitive credentials",
        })

    if not os.path.isfile(filepath) or is_binary_file(filepath):
        return findings

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            for line_idx, line in enumerate(fh, 1):
                # Quick pre-filter before running all regexes
                for label, pat in active_patterns:
                    match = pat.search(line)
                    if match:
                        matched_str = match.group(1) if match.groups() else match.group(0)
                        if not is_likely_placeholder(matched_str):
                            findings.append({
                                "file": rel_path,
                                "line": line_idx,
                                "type": label,
                                "preview": redact_secret(matched_str),
                            })
    except Exception as e:
        sys.stderr.write(f"Warning: Could not scan {rel_path}: {e}\n")

    return findings


def scan_diff_for_credentials(diff_text: str, active_patterns: list, exclude_files: set = None) -> list:
    """Scans git diff output for credentials added in outgoing commits."""
    if exclude_files is None:
        exclude_files = set()
    findings = []
    current_file = "unknown"
    skip_current_file = False
    line_number = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git"):
            # Format: diff --git a/path b/path
            parts = raw_line.split()
            if len(parts) >= 4:
                current_file = parts[3].lstrip("b/")
                basename = os.path.basename(current_file)
                skip_current_file = (
                    basename in exclude_files
                    or current_file in exclude_files
                    or "test_pre_command_hook" in basename
                    or current_file.endswith("pre_command_hook.py")
                )
        elif skip_current_file:
            continue
        elif raw_line.startswith("@@"):
            # Extract starting line number from hunk header @@ -a,b +c,d @@
            match = re.search(r"\+(\d+)", raw_line)
            if match:
                line_number = int(match.group(1)) - 1
        elif raw_line.startswith("+") and not raw_line.startswith("+++"):
            line_number += 1
            line = raw_line[1:]
            for label, pat in active_patterns:
                match = pat.search(line)
                if match:
                    matched_str = match.group(1) if match.groups() else match.group(0)
                    if not is_likely_placeholder(matched_str):
                        findings.append({
                            "file": f"Outgoing commit diff ({current_file})",
                            "line": line_number,
                            "type": label,
                            "preview": redact_secret(matched_str),
                        })
        elif not raw_line.startswith("-"):
            line_number += 1

    return findings


def run_credential_checks(cwd: str, config: dict) -> list:
    """Runs credential detection across tracked files and outgoing git commits."""
    enabled_types = config.get(
        "credentialTypes",
        ["cookies", "jwt", "api_keys", "oauth_tokens", "service_accounts", "internal_google"],
    )
    active_patterns = get_active_patterns(enabled_types)
    exclude_files = set(config.get("excludeFiles", DEFAULT_EXCLUDE_FILES))
    self_path = os.path.abspath(__file__)

    findings = []
    files_to_scan = set()

    # 1. Collect tracked files
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line:
                files_to_scan.add(line)
    except Exception as e:
        sys.stderr.write(f"Warning: git ls-files failed in {cwd}: {e}\n")

    # 2. Collect staged files
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line:
                    files_to_scan.add(line)
    except Exception:
        pass

    # Scan the discovered files
    for rel_path in sorted(files_to_scan):
        basename = os.path.basename(rel_path)
        if basename in exclude_files or rel_path in exclude_files:
            continue
        full_path = os.path.join(cwd, rel_path)
        # Avoid self-scanning the hook script or test scripts
        if os.path.abspath(full_path) == self_path or "test_pre_command_hook" in basename:
            continue
        file_findings = scan_file_for_credentials(full_path, rel_path, active_patterns)
        findings.extend(file_findings)

    # 3. Check outgoing commits diff
    upstream_ref = None
    for candidate in [["git", "rev-parse", "--abbrev-ref", "@{u}"],
                      ["git", "rev-parse", "--verify", "origin/main"],
                      ["git", "rev-parse", "--verify", "origin/master"],
                      ["git", "rev-parse", "--verify", "origin/HEAD"]]:
        try:
            r = subprocess.run(
                candidate,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if r.returncode == 0:
                upstream_ref = r.stdout.strip()
                break
        except Exception:
            pass

    if upstream_ref:
        try:
            r = subprocess.run(
                ["git", "diff", f"{upstream_ref}..HEAD"],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if r.returncode == 0 and r.stdout:
                diff_findings = scan_diff_for_credentials(r.stdout, active_patterns, exclude_files)
                findings.extend(diff_findings)
        except Exception as e:
            sys.stderr.write(f"Warning: git diff {upstream_ref}..HEAD failed: {e}\n")

    return findings


def get_git_aliases(cwd: str) -> dict:
    """Retrieves all configured git aliases for the current repository and environment."""
    aliases = {}
    try:
        res = subprocess.run(
            ["git", "config", "--get-regexp", r"^alias\."],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[0].startswith("alias."):
                    alias_name = parts[0][6:]
                    aliases[alias_name] = parts[1].strip()
    except Exception:
        pass
    return aliases


def get_git_subcommands(command_line: str) -> list:
    """Extracts git subcommands from a compound shell command line."""
    subcommands = []
    # Match segments starting with git (e.g. 'git push', '/usr/bin/git p')
    git_segments = re.finditer(
        r"(?:^|[;&|])\s*(?:/[a-zA-Z0-9_.-]+/)?git\b(?P<args>[^;&|]*)",
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


def is_target_command(
    command_line: str,
    cwd: str,
    pattern: str,
    target_subcommand: str = "push",
) -> bool:
    """Checks if command_line matches the target pattern directly or via git alias expansion."""
    if not command_line:
        return False
    # Direct regex match (fast path)
    if re.search(pattern, command_line, re.IGNORECASE):
        return True

    # Check for git alias expansion
    subcommands = get_git_subcommands(command_line)
    if not subcommands:
        return False

    aliases = get_git_aliases(cwd)
    if not aliases:
        return False

    for subcmd in subcommands:
        resolved = resolve_alias_to_subcommand(subcmd, aliases)
        if resolved == target_subcommand or f" {target_subcommand} " in f" {resolved} ":
            return True

    return False


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


def main():
    # Read payload from stdin (PreToolUse contract)
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return
        payload = json.loads(raw_input)
    except Exception as e:
        # If input cannot be parsed, allow by default to avoid deadlock
        sys.stderr.write(f"Error parsing PreToolUse payload: {e}\n")
        print(json.dumps({"decision": "allow"}))
        return

    # Extract command line
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    command_line = args.get("CommandLine", "")

    # Load configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "pre-command-config.json")
    config = {
        "targetCommandPattern": r"(^|\b)git\s+push\b",
        "slashCommand": "git-push-sanitization-check",
        "denyOnFailure": True,
        "timeoutSeconds": 60,
        "checkCredentials": True,
        "credentialTypes": [
            "cookies",
            "jwt",
            "api_keys",
            "oauth_tokens",
            "service_accounts",
            "internal_google",
        ],
        "excludeFiles": list(DEFAULT_EXCLUDE_FILES),
    }

    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load config from {config_path}: {e}\n")

    pattern = config.get("targetCommandPattern", r"(^|\b)git\s+push\b")
    slash_cmd = config.get("slashCommand", "git-push-sanitization-check")
    deny_on_failure = config.get("denyOnFailure", True)
    timeout_sec = config.get("timeoutSeconds", 60)
    check_credentials = config.get("checkCredentials", True)

    # Determine workspace directory (prefer explicit Cwd from toolCall args if present)
    arg_cwd = args.get("Cwd", "")
    workspace_paths = payload.get("workspacePaths", [])
    if arg_cwd and os.path.isdir(arg_cwd):
        cwd = arg_cwd
    elif workspace_paths and os.path.isdir(workspace_paths[0]):
        cwd = workspace_paths[0]
    else:
        # Default to repository root (parent of .agents)
        cwd = os.path.abspath(os.path.join(script_dir, "..", ".."))

    # Check if this command matches the target pattern directly or via git aliases
    if not is_target_command(command_line, cwd, pattern, target_subcommand="push"):
        print(json.dumps({"decision": "allow"}))
        return

    # Credential Check Gate
    if check_credentials:
        findings = run_credential_checks(cwd, config)
        if findings:
            formatted_issues = []
            for item in findings:
                formatted_issues.append(
                    f"- {item['file']}:{item['line']}: Detected {item['type']} -> {item['preview']}"
                )
            issues_summary = "\n".join(formatted_issues)
            denial_msg = (
                f"Pre-command check failed: Credentials detected in files prior to executing '{command_line}'.\n\n"
                f"Issues found:\n{issues_summary}\n\n"
                f"Please remove or sanitize these credentials before pushing to remote."
            )
            print(json.dumps({
                "decision": "deny",
                "reason": denial_msg,
            }))
            return

    # Check for test override environment variable
    mock_result = os.environ.get("MOCK_SUBAGENT_RESULT")
    if mock_result:
        if mock_result.lower() == "pass":
            print(json.dumps({"decision": "allow"}))
            return
        else:
            reason = os.environ.get(
                "MOCK_SUBAGENT_REASON",
                f"Subagent '{slash_cmd}' detected sanitization issues in outgoing commits.",
            )
            print(
                json.dumps(
                    {
                        "decision": "deny",
                        "reason": f"Pre-command check failed: {slash_cmd} rejected '{command_line}'.\nDetails: {reason}\n\nPlease take corrective actions and try again.",
                    }
                )
            )
            return

    # Find agy CLI binary
    agy_bin = find_agy_binary()
    if not agy_bin:
        sys.stderr.write(f"Warning: agy CLI binary not found. Skipping subagent check.\n")
        print(json.dumps({"decision": "allow"}))
        return

    # Ensure CLI log/crash directory exists
    try:
        os.makedirs(os.path.expanduser("~/.gemini/antigravity-cli"), exist_ok=True)
    except Exception:
        pass

    # Launch subagent slash command
    # Prefix with slash if not present
    cmd_name = slash_cmd if slash_cmd.startswith("/") else f"/{slash_cmd}"
    prompt = f"{cmd_name} Intercepted '{command_line}'. Review outgoing commits and repository state for sanitization."

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
        stdout_output = proc.stdout.strip()
        stderr_output = proc.stderr.strip()

        # Check for failure: non-zero return code or explicit failure marker in output
        failed = False
        failure_details = []

        combined_output = f"{stdout_output}\n{stderr_output}".strip()
        if "authentication required" in combined_output.lower() or "not logged into antigravity" in combined_output.lower():
            sys.stderr.write(f"Warning: agy CLI is not authenticated. Subagent check skipped, credential check passed.\n")
            print(json.dumps({"decision": "allow"}))
            return

        if proc.returncode != 0:
            failed = True
            if stderr_output:
                failure_details.append(stderr_output)
            if stdout_output:
                failure_details.append(stdout_output)
        elif "SANITIZATION_CHECK: FAILED" in stdout_output:
            failed = True
            failure_details.append(stdout_output)

        if failed and deny_on_failure:
            detail_msg = "\n".join(failure_details) if failure_details else "Check did not pass."
            decision_payload = {
                "decision": "deny",
                "reason": (
                    f"Pre-push sanitization check ({slash_cmd}) failed prior to '{command_line}'.\n"
                    f"Subagent output:\n{detail_msg}\n\n"
                    f"Please review the issues reported by /{slash_cmd}, take corrective actions, and try again."
                ),
            }
            print(json.dumps(decision_payload))
            return

        # Passed
        print(json.dumps({"decision": "allow"}))

    except subprocess.TimeoutExpired:
        if deny_on_failure:
            print(
                json.dumps(
                    {
                        "decision": "deny",
                        "reason": f"Pre-command check ({slash_cmd}) timed out after {timeout_sec}s. Please check subagent status or retry.",
                    }
                )
            )
        else:
            print(json.dumps({"decision": "allow"}))
    except Exception as e:
        sys.stderr.write(f"Error launching subagent {slash_cmd}: {e}\n")
        # On runtime execution error of the hook itself, allow or deny based on policy
        if deny_on_failure:
            print(
                json.dumps(
                    {
                        "decision": "deny",
                        "reason": f"Unable to complete pre-command check ({slash_cmd}): {e}. Execution halted for safety.",
                    }
                )
            )
        else:
            print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
