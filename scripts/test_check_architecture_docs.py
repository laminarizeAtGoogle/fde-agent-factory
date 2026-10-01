"""
Unit and integration test suite for check_architecture_docs.py.
Verifies git command parsing, alias resolution, docs folder verification,
Mermaid diagram validation, subagent slash command execution, and PreToolUse hook execution contract.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import check_architecture_docs


class TestCheckArchitectureDocs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_arch_docs_")
        self.docs_dir = os.path.join(self.temp_dir, "docs")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_valid_kb(self):
        """Creates a valid Google OKF Knowledge Base structure inside docs/."""
        kb_components = os.path.join(self.docs_dir, "knowledge_base", "components")
        os.makedirs(kb_components, exist_ok=True)
        sample_kb = os.path.join(kb_components, "sample-component.md")
        with open(sample_kb, "w") as f:
            f.write(
                "---\nokf_version: '1.0'\ncomponent_id: 'sample'\n---\n# OKF: Sample\n"
                "This is a valid Google OKF component documentation entry.\n"
                + "x" * 60
            )

    def _create_valid_docs(self):
        """Creates valid docs directory with Mermaid diagram and OKF KB."""
        os.makedirs(self.docs_dir, exist_ok=True)
        arch_file = os.path.join(self.docs_dir, "architecture.md")
        with open(arch_file, "w") as f:
            f.write(
                "# Architecture\n"
                "Canonical Architecture Diagram in Mermaid.\n"
                "```mermaid\n"
                "flowchart TD\n"
                "    client[Web Client] --> gateway[IAP Gateway]\n"
                "```\n"
                + "x" * 100
            )
        self._create_valid_kb()

    def test_is_git_push_command(self):
        # Standard push commands
        self.assertTrue(check_architecture_docs.is_git_push_command("git push", self.temp_dir))
        self.assertTrue(check_architecture_docs.is_git_push_command("git push origin main", self.temp_dir))
        self.assertTrue(check_architecture_docs.is_git_push_command("git push -u origin feat/test", self.temp_dir))
        self.assertTrue(check_architecture_docs.is_git_push_command("git push --force-with-lease", self.temp_dir))
        self.assertTrue(check_architecture_docs.is_git_push_command("/usr/bin/git push", self.temp_dir))
        self.assertTrue(check_architecture_docs.is_git_push_command("git commit -m 'fix' && git push", self.temp_dir))
        self.assertTrue(check_architecture_docs.is_git_push_command("git -C /some/dir push", self.temp_dir))

        # Non-push commands
        self.assertFalse(check_architecture_docs.is_git_push_command("git status", self.temp_dir))
        self.assertFalse(check_architecture_docs.is_git_push_command("git commit -m 'feat'", self.temp_dir))
        self.assertFalse(check_architecture_docs.is_git_push_command("git pull", self.temp_dir))
        self.assertFalse(check_architecture_docs.is_git_push_command("terraform apply", self.temp_dir))
        self.assertFalse(check_architecture_docs.is_git_push_command("echo git push", self.temp_dir))

    def test_verify_docs_directory_missing(self):
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertFalse(valid)
        self.assertIn("Missing './docs' directory", msg)

    def test_verify_docs_directory_empty(self):
        os.makedirs(self.docs_dir, exist_ok=True)
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertFalse(valid)
        self.assertIn("No valid architecture diagram found", msg)

    def test_verify_docs_directory_missing_kb(self):
        os.makedirs(self.docs_dir, exist_ok=True)
        arch_file = os.path.join(self.docs_dir, "architecture.md")
        with open(arch_file, "w") as f:
            f.write(
                "# Architecture\nCanonical Architecture Diagram in Mermaid.\n"
                "```mermaid\nflowchart TD\n  A --> B\n```\n" + "x" * 60
            )
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertFalse(valid)
        self.assertIn("Missing Google OKF Knowledge Base", msg)

    def test_verify_docs_directory_valid(self):
        self._create_valid_docs()
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_verify_docs_rejects_ascii_box_diagram(self):
        os.makedirs(self.docs_dir, exist_ok=True)
        arch_file = os.path.join(self.docs_dir, "architecture.md")
        with open(arch_file, "w") as f:
            f.write(
                "# Architecture\n"
                "+-------------------------------------------------------+\n"
                "|                     TOPOLOGY                          |\n"
                "+-------------------------------------------------------+\n"
                "|                                                       |\n"
                "+-------------------------------------------------------+\n"
            )
        self._create_valid_kb()
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertFalse(valid)
        self.assertIn("contains markdown/ASCII box drawing instead of the mandatory Mermaid diagram format", msg)

    def test_verify_docs_accepts_mermaid_file(self):
        os.makedirs(self.docs_dir, exist_ok=True)
        mmd_file = os.path.join(self.docs_dir, "architecture_diagram.mmd")
        with open(mmd_file, "w") as f:
            f.write(
                "flowchart TD\n"
                "  client[Web Client] --> gateway[IAP Gateway]\n"
                "  gateway --> agent[Cloud Chat Agent]\n"
                + "x" * 60
            )
        self._create_valid_kb()
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertTrue(valid)

    def test_verify_docs_rejects_mermaid_missing_keyword(self):
        os.makedirs(self.docs_dir, exist_ok=True)
        mmd_file = os.path.join(self.docs_dir, "architecture_diagram.mmd")
        with open(mmd_file, "w") as f:
            f.write("invalid diagram syntax without keywords\n" + "x" * 60)
        self._create_valid_kb()
        valid, msg = check_architecture_docs.verify_docs_directory(self.temp_dir, "docs")
        self.assertFalse(valid)
        self.assertIn("must contain valid Mermaid declarations", msg)

    def test_pretooluse_hook_allows_non_push(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"},
            },
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "allow")

    def test_pretooluse_hook_denies_missing_docs_on_push(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("Missing './docs' directory", out.get("reason", ""))

    def test_git_repo_simulation_denies_when_code_changed_but_docs_did_not(self):
        # Initialize a temporary git repo
        subprocess.run(["git", "init"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)

        # Create valid docs
        self._create_valid_docs()

        # Initial commit with docs
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit with docs"], cwd=self.temp_dir, check=True)

        # Make a second commit with code changes ONLY (e.g. service.py)
        code_file = os.path.join(self.temp_dir, "service.py")
        with open(code_file, "w") as f:
            f.write("print('new feature')\n")
        subprocess.run(["git", "add", "service.py"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "add service.py"], cwd=self.temp_dir, check=True)

        # Run hook
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [self.temp_dir],
        }
        env = os.environ.copy()
        env["MOCK_SUBAGENT_RESULT"] = "fail"
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("architecture docs in './docs/' were not updated", out.get("reason", ""))
        self.assertIn("service.py", out.get("reason", ""))

    def test_git_repo_simulation_allows_when_docs_also_updated(self):
        # Initialize a temporary git repo
        subprocess.run(["git", "init"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)

        # Initial commit
        self._create_valid_docs()
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.temp_dir, check=True)

        # Commit code AND docs updates together
        code_file = os.path.join(self.temp_dir, "service.py")
        with open(code_file, "w") as f:
            f.write("print('new feature')\n")
        arch_file = os.path.join(self.docs_dir, "architecture.md")
        with open(arch_file, "a") as f:
            f.write("\nUpdated with service.py component!\n")

        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "feat: add service and update docs"], cwd=self.temp_dir, check=True)

        # Run hook
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "allow")

    def test_git_repo_simulation_denies_when_docs_have_uncommitted_changes(self):
        # Initialize a temporary git repo
        subprocess.run(["git", "init"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)

        self._create_valid_docs()
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.temp_dir, check=True)

        # Modify docs without committing
        arch_file = os.path.join(self.docs_dir, "architecture.md")
        with open(arch_file, "a") as f:
            f.write("\nUncommitted modification\n")

        # Run hook
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("Uncommitted updates detected in './docs/'", out.get("reason", ""))

    def test_subagent_mock_pass_allows_push(self):
        subprocess.run(["git", "init"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)

        self._create_valid_docs()
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.temp_dir, check=True)

        # Commit code without docs
        code_file = os.path.join(self.temp_dir, "service.py")
        with open(code_file, "w") as f:
            f.write("print('feature')\n")
        subprocess.run(["git", "add", "service.py"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "add service"], cwd=self.temp_dir, check=True)

        env = os.environ.copy()
        env["MOCK_SUBAGENT_RESULT"] = "pass"

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "allow")

    def test_subagent_mock_fail_denies_push(self):
        subprocess.run(["git", "init"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)

        self._create_valid_docs()
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.temp_dir, check=True)

        code_file = os.path.join(self.temp_dir, "service.py")
        with open(code_file, "w") as f:
            f.write("print('feature')\n")
        subprocess.run(["git", "add", "service.py"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "add service"], cwd=self.temp_dir, check=True)

        env = os.environ.copy()
        env["MOCK_SUBAGENT_RESULT"] = "fail"
        env["MOCK_SUBAGENT_REASON"] = "Subagent could not generate diagram"

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "check_architecture_docs.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("Subagent could not generate diagram", out.get("reason", ""))

    def test_shell_wrapper_fast_allow_and_push_execution(self):
        wrapper = os.path.join(SCRIPT_DIR, "check-architecture-docs.sh")
        # Fast non-git command
        payload_non_git = {
            "toolCall": {"name": "run_command", "args": {"CommandLine": "npm test"}},
            "workspacePaths": [self.temp_dir],
        }
        proc = subprocess.run(
            ["bash", wrapper],
            input=json.dumps(payload_non_git),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "allow")


if __name__ == "__main__":
    unittest.main()
