#!/usr/bin/env python3
"""
Unit and integration test suite for the pre-command credential hook.
Tests pattern matching for cookies, JWTs, and API keys, redaction,
placeholder suppression, and PreToolUse contract execution.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Import functions from pre_command_hook
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import pre_command_hook


class TestCredentialPatterns(unittest.TestCase):
    def setUp(self):
        self.all_patterns = pre_command_hook.get_active_patterns([
            "cookies",
            "jwt",
            "api_keys",
            "oauth_tokens",
            "service_accounts",
            "internal_google",
        ])

    def _matches_any(self, text, expected_label=None):
        matched_labels = []
        for label, pat in self.all_patterns:
            m = pat.search(text)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                if not pre_command_hook.is_likely_placeholder(val):
                    matched_labels.append(label)
        if expected_label:
            self.assertIn(expected_label, matched_labels, f"Expected {expected_label} in {matched_labels} for '{text}'")
        return len(matched_labels) > 0

    def test_cookie_patterns(self):
        # Cookie headers
        self.assertTrue(self._matches_any("Cookie: sessionid=abcdef1234567890; path=/", "Cookie Header"))
        self.assertTrue(self._matches_any("Set-Cookie: auth_token=9876543210fedcba; Secure; HttpOnly", "Cookie Header"))

        # Session cookie tokens
        self.assertTrue(self._matches_any("connect.sid=s%3A1234567890abcdef1234567890", "Session Cookie Token"))
        self.assertTrue(self._matches_any("sessionid=ab12cd34ef56gh78ij90kl12", "Session Cookie Token"))
        self.assertTrue(self._matches_any("remember_token=longrandomstringofcredentials12345", "Session Cookie Token"))

        # Cookie variable
        self.assertTrue(self._matches_any('auth_cookie = "secret_cookie_payload_12345"', "Cookie Variable"))

    def test_jwt_patterns(self):
        jwt_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        self.assertTrue(self._matches_any(f"token = '{jwt_token}'", "JWT Token"))
        self.assertTrue(self._matches_any(f'jwt_token = "{jwt_token}"', "JWT Variable Assignment"))

    def test_api_key_patterns(self):
        # Google API key (AIza + 35 characters = 39 total)
        fake_google_key = "".join(["AI", "za", "SyD", "12345678901234567890123456789012"])
        self.assertTrue(self._matches_any(fake_google_key, "Google API Key"))

        # Google OAuth 2.0 Access Token (ya29....)
        fake_oauth = "".join(["ya", "29.", "a0AfH6SMBx1234567890abcdef123456"])
        self.assertTrue(self._matches_any(fake_oauth, "Google OAuth Access Token"))

        # GCP Service Account JSON payload
        fake_sa_type = "".join(['"type": ', '"service_account"'])
        self.assertTrue(self._matches_any(fake_sa_type, "GCP Service Account Key"))
        fake_sa_pkid = '"private_key_id": "a1b2c3d4e5f60123456789abcdef0123456789ab"'
        self.assertTrue(self._matches_any(fake_sa_pkid, "GCP Service Account Private Key ID"))

        # GitHub tokens
        self.assertTrue(self._matches_any("ghp_123456789012345678901234567890123456", "GitHub Token"))
        self.assertTrue(self._matches_any("github_pat_11AAAAAAA0123456789012345678901234567890123456789012345678901234567890123456789012", "GitHub Token"))

        # OpenAI API key
        self.assertTrue(self._matches_any("sk-proj-123456789012345678901234567890", "OpenAI API Key"))
        self.assertTrue(self._matches_any("sk-123456789012345678901234567890", "OpenAI API Key"))

        # Anthropic API key
        self.assertTrue(self._matches_any("sk-ant-api03-123456789012345678901234567890", "Anthropic API Key"))

        # AWS Access Keys & Resource IDs (including expanded PR #23 prefixes)
        for prefix in ["AKIA", "ASIA", "AGPA", "AIDA", "AROA", "AIPA", "ANPA", "ANVA", "A3T1"]:
            fake_aws_key = "".join([prefix[:2], prefix[2:], "IOSFODNN7ABCDEFG"])
            self.assertTrue(self._matches_any(fake_aws_key, "AWS Access Key ID"))

        # AWS Secret Key (40 characters)
        fake_aws_sec = "".join(["wJalrXUtnFEMI/K7", "MDENG/bPxRfiCY", "1234567890"])
        fake_aws_sec_line = f'aws_{"secret"}_access_{"key"} = "{fake_aws_sec}"'
        self.assertTrue(self._matches_any(fake_aws_sec_line, "AWS Secret Key"))

        # Private Key
        self.assertTrue(self._matches_any("-----BEGIN RSA PRIVATE KEY-----", "Private Key Block"))
        self.assertTrue(self._matches_any("-----BEGIN OPENSSH PRIVATE KEY-----", "Private Key Block"))

        # Generic API key
        self.assertTrue(self._matches_any('api_key = "secret_value_abcdef1234567890"', "Generic API Key / Secret"))
        self.assertTrue(self._matches_any("Authorization: Bearer my_secret_token_1234567890abcdef", "Bearer Token"))

    def test_internal_google_patterns(self):
        # Internal shortlinks, bugs, CLs, depot paths, corp domains
        self.assertTrue(self._matches_any("See " + "".join(["go", "/internal-secret-roadmap"]), "Internal Go Shortlink"))
        self.assertTrue(self._matches_any("Fixed in " + "".join(["b", "/987654321"]), "Internal Buganizer ID"))
        self.assertTrue(self._matches_any("Reviewed in " + "".join(["cl", "/654321098"]), "Internal Changelist ID"))
        self.assertTrue(self._matches_any("Question at " + "".join(["yaqs", "/5432109"]), "Internal YAQS Link"))
        self.assertTrue(self._matches_any("Docs at " + "".join(["g3", "doc/company/teams/secret"]), "Internal g3doc Reference"))
        self.assertTrue(self._matches_any("Path " + "".join(["//depot/", "google3/cloud/secret/main.py"]), "Internal google3 / Depot Path"))
        self.assertTrue(self._matches_any("Host " + "".join(["my-service", ".corp.", "google.com"]), "Internal Corp Hostname"))
        self.assertTrue(self._matches_any("Ref " + "".join(["piper", ":///depot/google3/foo/bar.py"]), "Internal Piper Path"))

    def test_sensitive_filename_patterns(self):
        active = self.all_patterns
        for fname in ["service_account_key.json", "my-service-account.json", "client_secret_123.json", "skill-runs.jsonl"]:
            findings = pre_command_hook.scan_file_for_credentials("/nonexistent/" + fname, fname, active)
            self.assertTrue(any(f["type"] == "Sensitive File Pattern" for f in findings), f"Should flag filename {fname}")

    def test_placeholder_suppression(self):
        # Examples and placeholders should not match
        fake_aws_example = "".join(["AK", "IA", "IOSFODNN7EXAMPLE"])
        placeholders = [
            'api_key = "your-api-key-here"',
            'api_key = "YOUR_API_KEY"',
            'api_key = "EXAMPLE_KEY_12345678"',
            'api_key = "<YOUR_API_KEY>"',
            'api_key = "dummy_key_12345678"',
            'api_key = "replace_me_with_key"',
            'api_key = "00000000000000000000"',
            'api_key = "xxxxxxxxxxxxxxxxxxxx"',
            f'aws_key = "{fake_aws_example}"',
            "See go/cross for OSPO compliance guidelines",
            "Example bug b/123456 or path //depot/google3/...",
        ]
        for p in placeholders:
            self.assertFalse(self._matches_any(p), f"Should not flag placeholder: {p}")

    def test_redaction(self):
        redacted = pre_command_hook.redact_secret("ghp_123456789012345678901234567890123456")
        self.assertNotIn("12345678901234567890", redacted)
        self.assertTrue(redacted.endswith("[REDACTED]"))
        self.assertTrue(redacted.startswith("ghp_"))


class TestHookExecution(unittest.TestCase):
    def test_non_matching_command_allowed(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"},
            }
        }
        res = subprocess.run(
            ["python3", os.path.join(SCRIPT_DIR, "pre_command_hook.py")],
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("decision"), "allow")

    def test_clean_repo_git_push_allowed_with_mock(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))],
        }
        env = os.environ.copy()
        env["MOCK_SUBAGENT_RESULT"] = "pass"

        res = subprocess.run(
            ["python3", os.path.join(SCRIPT_DIR, "pre_command_hook.py")],
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("decision"), "allow")

    def test_subagent_failure_references_new_skill_name(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))],
        }
        env = os.environ.copy()
        env["MOCK_SUBAGENT_RESULT"] = "fail"
        env["MOCK_SUBAGENT_REASON"] = "Found uncommitted changes"

        res = subprocess.run(
            ["python3", os.path.join(SCRIPT_DIR, "pre_command_hook.py")],
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("decision"), "deny")
        reason = data.get("reason", "")
        self.assertIn("git-push-sanitization-check", reason)
        self.assertNotIn("gitPushSanitizationCheck", reason)

    def test_scan_file_for_credentials(self):
        patterns = pre_command_hook.get_active_patterns(["cookies", "jwt", "api_keys"])
        test_file = os.path.join(SCRIPT_DIR, "tmp_test_secrets.py")
        fake_google_key = "".join(["AI", "za", "SyD", "12345678901234567890123456789012"])
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write('COOKIE = "connect.sid=s%3Aabcdef1234567890abcdef"\n')
                f.write('JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdef1234567890abcdef1234567890"\n')
                f.write(f'API_KEY = "{fake_google_key}"\n')

            findings = pre_command_hook.scan_file_for_credentials(test_file, "tmp_test_secrets.py", patterns)
            found_types = {item["type"] for item in findings}
            self.assertIn("Session Cookie Token", found_types)
            self.assertIn("JWT Token", found_types)
            self.assertIn("Google API Key", found_types)

            # Ensure all previews are redacted
            for item in findings:
                self.assertIn("[REDACTED]", item["preview"])
                self.assertNotIn(fake_google_key, item["preview"])
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_scan_diff_for_credentials(self):
        patterns = pre_command_hook.get_active_patterns(["cookies", "jwt", "api_keys"])
        sample_diff = (
            "diff --git a/app.py b/app.py\n"
            "index 0000000..1111111 100644\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1,2 +1,5 @@\n"
            "+# Added credentials\n"
            "+cookie_hdr = \"Cookie: sessionid=abcdef1234567890;\"\n"
            "+jwt_val = \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdef1234567890abcdef1234567890\"\n"
            "+api_token = \"ghp_123456789012345678901234567890123456\"\n"
        )
        findings = pre_command_hook.scan_diff_for_credentials(sample_diff, patterns)
        found_types = {item["type"] for item in findings}
        self.assertIn("Cookie Header", found_types)
        self.assertIn("JWT Token", found_types)
        self.assertIn("GitHub Token", found_types)

        for item in findings:
            self.assertIn("[REDACTED]", item["preview"])
            self.assertIn("Outgoing commit diff", item["file"])

    def test_credential_detected_denies_git_push(self):
        import io
        from unittest.mock import patch

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main"},
            },
            "workspacePaths": [os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))],
        }

        mock_findings = [
            {
                "file": "config.py",
                "line": 10,
                "type": "JWT Token",
                "preview": "eyJh...890 [REDACTED]",
            },
            {
                "file": "auth.py",
                "line": 25,
                "type": "Session Cookie Token",
                "preview": "conn...cdef [REDACTED]",
            },
            {
                "file": "keys.py",
                "line": 4,
                "type": "Google API Key",
                "preview": "AIza...9012 [REDACTED]",
            },
        ]

        with patch("sys.stdin", io.StringIO(json.dumps(payload))), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, \
             patch("pre_command_hook.run_credential_checks", return_value=mock_findings):
            pre_command_hook.main()

            output = mock_stdout.getvalue()
            data = json.loads(output)
            self.assertEqual(data.get("decision"), "deny")
            reason = data.get("reason", "")
            self.assertIn("Credentials detected", reason)
            self.assertIn("JWT Token", reason)
            self.assertIn("Session Cookie Token", reason)
            self.assertIn("Google API Key", reason)
            self.assertIn("[REDACTED]", reason)

    def test_shell_script_non_git_fast_path(self):
        # Non-git command should return allow immediately
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "ls -la"},
            }
        }
        res = subprocess.run(
            [os.path.join(SCRIPT_DIR, "pre-command-hook.sh")],
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("decision"), "allow")

    def test_git_alias_resolution(self):
        aliases = {
            "p": "push",
            "pub": "push origin main",
            "st": "status",
            "pp": "p",
        }
        self.assertEqual(pre_command_hook.resolve_alias_to_subcommand("p", aliases), "push")
        self.assertEqual(pre_command_hook.resolve_alias_to_subcommand("pub", aliases), "push")
        self.assertEqual(pre_command_hook.resolve_alias_to_subcommand("pp", aliases), "push")
        self.assertEqual(pre_command_hook.resolve_alias_to_subcommand("st", aliases), "status")
        self.assertEqual(pre_command_hook.resolve_alias_to_subcommand("commit", aliases), "commit")

    def test_is_target_command_with_aliases(self):
        from unittest.mock import patch
        mock_aliases = {"p": "push", "publish": "push origin HEAD", "st": "status"}

        pattern = r"(?:^|[;&|]\s*)\s*git(?:\s+-[^\s]+|\s+--[^\s]+|\s+-[a-zA-Z]\s+[^\s]+)*\s+push\b"
        with patch("pre_command_hook.get_git_aliases", return_value=mock_aliases):
            # Literal push matches
            self.assertTrue(pre_command_hook.is_target_command("git push origin main", "/tmp", pattern))
            # Aliased push matches
            self.assertTrue(pre_command_hook.is_target_command("git p origin main", "/tmp", pattern))
            self.assertTrue(pre_command_hook.is_target_command("git -C /some/dir p", "/tmp", pattern))
            self.assertTrue(pre_command_hook.is_target_command("git publish", "/tmp", pattern))
            # Other git commands or aliases do not match
            self.assertFalse(pre_command_hook.is_target_command("git st", "/tmp", pattern))
            self.assertFalse(pre_command_hook.is_target_command("git status", "/tmp", pattern))
            self.assertFalse(pre_command_hook.is_target_command("git commit -m 'msg'", "/tmp", pattern))
            self.assertFalse(pre_command_hook.is_target_command("ls -la", "/tmp", pattern))


if __name__ == "__main__":
    unittest.main()
