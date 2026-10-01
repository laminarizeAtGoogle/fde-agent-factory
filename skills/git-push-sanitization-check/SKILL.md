---
name: git-push-sanitization-check
description: >-
  Sanitizes and validates repository changes prior to git push.
  Checks for sensitive credentials, uncommitted secrets, lint issues, or forbidden artifacts.
---

# git-push-sanitization-check Subagent
 
This subagent is automatically triggered prior to running `git push`.
It reviews outgoing changes to ensure all code and repository states are sanitized before pushing to remote.

## Instructions

Configure your sanitization rules and checks below:

1. **Check Outgoing Commits and Diffs**:
   - Inspect unpushed commits:
     ```bash
     git log @{u}..HEAD --oneline
     ```
   - Inspect diff of unpushed commits:
     ```bash
     git diff @{u}..HEAD
     ```

2. **Verify No Credentials, Secrets, Internal Identifiers, or Sensitive Files**:
   - **Cookies**: Check for hardcoded cookie strings, session IDs (`sessionid=`, `connect.sid=`, `remember_token=`), and `Cookie:` / `Set-Cookie:` headers.
   - **JWTs & OAuth Tokens**: Check for JSON Web Tokens (`eyJ...`), Google OAuth 2.0 access tokens (`ya29....`), auth headers, or hardcoded session tokens.
   - **API Keys, Cloud Credentials & Service Accounts**: Check for provider-specific API keys and IAM resource identifiers (Google `AIza...`, GitHub `ghp_...` / `github_pat_...`, OpenAI `sk-...`, Anthropic `sk-ant-...`, AWS `A3T...` / `AKIA...` / `AGPA...` / `AIDA...` / `AROA...` / `AIPA...` / `ANPA...` / `ANVA...` / `ASIA...`, Stripe, Slack, SendGrid, HuggingFace), GCP Service Account key payloads (`"type": "service_account"`, `"private_key_id"`), private key blocks (`-----BEGIN ... PRIVATE KEY-----`), and generic `api_key = "..."`, `secret_key = "..."`, `Bearer <token>`.
   - **Internal Google Links & Identifiers**: Check for unredacted internal shortlinks (`go/...`, `b/...`, `cl/...`, `yaqs/...`), internal depot/Piper paths (`//depot/google3/...`, `google3/...`, `piper:///...`), internal corporate hostnames (`*.corp.google.com`), and `g3doc` URLs.
   - **Sensitive Files**: Check for sensitive or untracked configuration files (e.g. `.env`, `.env.*`, service account JSON keys, `client_secret*.json`, `.pem` / `.key` files, private keys, `credentials.json`, `cookies.txt`, `skill-runs.jsonl`).
   - Ensure `.gitignore` properly excludes local credentials, scratch directories, and configuration files.

3. **Validation Outcome**:
   - If **all checks pass**:
     - Conclude with a clear confirmation: `SANITIZATION_CHECK: PASSED`.
   - If **issues are detected**:
     - State clearly what issue was found: `SANITIZATION_CHECK: FAILED: <details of issue>`.
     - Detail the corrective actions needed (e.g. `git reset`, untracking sensitive files, or removing hardcoded secrets/internal references).
