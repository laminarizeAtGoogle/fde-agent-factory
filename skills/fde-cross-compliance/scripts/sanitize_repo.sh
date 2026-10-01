#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

CHECK_ONLY=0
KEEP_SKILLS=0
TARGET_DIR="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check|--dry-run)
      CHECK_ONLY=1
      shift
      ;;
    --keep-skills)
      KEEP_SKILLS=1
      shift
      ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--check|--dry-run] [--keep-skills] [target_directory]"
      exit 0
      ;;
    *)
      TARGET_DIR="$1"
      shift
      ;;
  esac
done

ABS_TARGET_DIR="$(cd "${TARGET_DIR}" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCES_DIR="$(cd "${SCRIPT_DIR}/../resources" && pwd)"
YEAR=$(date +"%Y")
CROSS_BIN="/google/bin/releases/opensource/thirdparty/cross/cross"
EXIT_CODE=0

REPO_BASENAME="$(basename "${ABS_TARGET_DIR}")"
if [[ "${REPO_BASENAME}" =~ ^(agent-driven-dev|fde-skills|fde-skills-repo|fde-essential-skills|egm-plugin)$ ]]; then
  KEEP_SKILLS=1
fi

echo "================================================================"
echo " Starting FDE Cross Compliance & Sanitization Toolkit"
echo " Target Directory: ${ABS_TARGET_DIR}"
if [ "${CHECK_ONLY}" -eq 1 ]; then
  echo " Mode: CHECK ONLY (dry-run audit)"
else
  echo " Mode: SANITIZE & VERIFY"
fi
echo "================================================================"

echo ""
echo "=== [1/5] Checking .gitignore for Googler-Exclusive AI Skills ==="
GITIGNORE_FILE="${ABS_TARGET_DIR}/.gitignore"
MARKER="# Googler-Exclusive AI Skills & Agent Configurations"

if [ "${KEEP_SKILLS}" -eq 0 ]; then
  if [ "${CHECK_ONLY}" -eq 1 ]; then
    if [ ! -f "${GITIGNORE_FILE}" ] || ! grep -Fq "${MARKER}" "${GITIGNORE_FILE}"; then
      echo "WARNING: .gitignore is missing Googler-exclusive AI skills exclusion rules."
    else
      echo ".gitignore contains Googler-exclusive AI skills exclusion rules."
    fi
  else
    if [ ! -f "${GITIGNORE_FILE}" ]; then
      touch "${GITIGNORE_FILE}"
    fi
    if ! grep -Fq "${MARKER}" "${GITIGNORE_FILE}"; then
      echo "" >> "${GITIGNORE_FILE}"
      cat "${RESOURCES_DIR}/gitignore.skills" >> "${GITIGNORE_FILE}"
      echo "Added Googler-exclusive AI skills & agent exclusion rules to .gitignore."
    else
      echo ".gitignore already contains Googler-exclusive AI skills exclusion rules."
    fi

    if [ -d "${ABS_TARGET_DIR}/.git" ]; then
      SKILL_PATHS=(
        ".gemini" ".agents" "_agents" "skills" "fde-skills-repo" "clean-code-skill"
        "GEMINI.md" "AGENTS.md" "CLAUDE.md" "CONTEXT.md"
        ".cursor" ".cursorrules" ".claude" ".codex" ".opencode" ".hermes" "skill-runs.jsonl"
      )
      for spath in "${SKILL_PATHS[@]}"; do
        TRACKED=$(git -C "${ABS_TARGET_DIR}" ls-files "${spath}" 2>/dev/null || true)
        if [ -n "${TRACKED}" ]; then
          echo "WARNING: Untracking Googler-exclusive path from Git index: ${spath}"
          git -C "${ABS_TARGET_DIR}" rm -r --cached --quiet "${spath}" || true
        fi
      done
    fi
  fi
else
  echo "Target is an FDE harness/skills repository (${REPO_BASENAME}); preserving .agents/ and skills/."
fi

echo ""
echo "=== [2/5] Ensuring OSPO Files & Apache-2.0 Headers ==="
if [ ! -f "${ABS_TARGET_DIR}/LICENSE" ]; then
  if [ "${CHECK_ONLY}" -eq 0 ] && [ -f "${RESOURCES_DIR}/LICENSE" ]; then
    cp "${RESOURCES_DIR}/LICENSE" "${ABS_TARGET_DIR}/LICENSE"
    echo "Added standard Apache-2.0 LICENSE file."
  else
    echo "ERROR: Missing root LICENSE file in ${ABS_TARGET_DIR}."
    EXIT_CODE=1
  fi
else
  echo "Found root LICENSE file."
fi

if [ ! -f "${ABS_TARGET_DIR}/CONTRIBUTING.md" ] && [ ! -f "${ABS_TARGET_DIR}/CONTRIBUTING" ] && [ ! -f "${ABS_TARGET_DIR}/CONTRIBUTING.txt" ]; then
  if [ "${CHECK_ONLY}" -eq 0 ] && [ -f "${RESOURCES_DIR}/CONTRIBUTING.md" ]; then
    cp "${RESOURCES_DIR}/CONTRIBUTING.md" "${ABS_TARGET_DIR}/CONTRIBUTING.md"
    echo "Added standard Google OSPO CONTRIBUTING.md file."
  else
    echo "ERROR: Missing root CONTRIBUTING.md file in ${ABS_TARGET_DIR}."
    EXIT_CODE=1
  fi
else
  echo "Found root CONTRIBUTING.md file."
fi

if [ ! -f "${ABS_TARGET_DIR}/README.md" ]; then
  echo "WARNING: Missing root README.md file (recommended by OSPO)."
else
  echo "Found root README.md file."
fi

ADDLICENSE_BIN=""
if command -v addlicense &> /dev/null; then
  ADDLICENSE_BIN="addlicense"
elif [ -x "${HOME}/go/bin/addlicense" ]; then
  ADDLICENSE_BIN="${HOME}/go/bin/addlicense"
fi

if [ -n "${ADDLICENSE_BIN}" ]; then
  ADDLICENSE_ARGS=(
    -ignore ".git/**"
    -ignore "node_modules/**"
    -ignore ".venv/**"
    -c "Google LLC"
    -l apache
    -y "${YEAR}"
  )
  if [ "${KEEP_SKILLS}" -eq 0 ]; then
    ADDLICENSE_ARGS+=(
      -ignore ".gemini/**"
      -ignore ".agents/**"
      -ignore "_agents/**"
      -ignore "skills/**"
      -ignore "clean-code-skill/**"
      -ignore "fde-skills-repo/**"
    )
  fi
  if [ "${CHECK_ONLY}" -eq 1 ]; then
    ADDLICENSE_ARGS+=(-check)
  fi
  if "${ADDLICENSE_BIN}" "${ADDLICENSE_ARGS[@]}" "${ABS_TARGET_DIR}"; then
    echo "License headers verified/applied successfully."
  else
    echo "ERROR: Missing Apache-2.0 license headers detected."
    EXIT_CODE=1
  fi
else
  echo "WARNING: addlicense not found in PATH. Run: go install github.com/google/addlicense@latest"
fi

echo ""
echo "=== [3/5] Scanning for Internal Links & Identifiers ==="
CORP_HOST="\.corp\.goo""gle\.com"
INTERNAL_PATTERNS="(go\/[a-zA-Z0-9_-]+|b\/[0-9]{6,}|cl\/[0-9]{6,}|g3doc|google3|${CORP_HOST}|piper:\/\/\/)"
MATCHES=$(grep -rEnI \
  --exclude="sanitize_repo.sh" \
  --exclude="SKILL.md" \
  --exclude="compliance-guide.md" \
  --exclude-dir={.git,.venv,node_modules,__pycache__,.gemini,_agents,clean-code-skill,fde-skills-repo,.cursor,.claude} \
  "${INTERNAL_PATTERNS}" "${ABS_TARGET_DIR}" || true)

if [ -n "${MATCHES}" ]; then
  echo "WARNING: Found potential internal Google references that need review/redaction:"
  echo "${MATCHES}"
else
  echo "No common internal references detected."
fi

echo ""
echo "=== [4/5] Checking for Secrets & API Keys ==="
SECRET_PATTERNS='(AIzaSy[A-Za-z0-9_-]{33}|ya29\.[0-9A-Za-z_-]+|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}|(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}|"type":\s*"service_account"|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY)'
SECRET_MATCHES=$(grep -rEnI \
  --exclude="sanitize_repo.sh" \
  --exclude="SKILL.md" \
  --exclude="compliance-guide.md" \
  --exclude-dir={.git,.venv,node_modules,__pycache__,.gemini,_agents,clean-code-skill,fde-skills-repo,.cursor,.claude} \
  "${SECRET_PATTERNS}" "${ABS_TARGET_DIR}" || true)

if [ -n "${SECRET_MATCHES}" ]; then
  echo "ERROR: Potential credentials/API keys detected:"
  echo "${SECRET_MATCHES}"
  EXIT_CODE=1
else
  echo "No high-entropy secrets or keys detected."
fi

echo ""
echo "=== [5/5] Running OSPO cross Compliance Scan ==="
if [ -x "${CROSS_BIN}" ]; then
  "${CROSS_BIN}" "${ABS_TARGET_DIR}"
else
  echo "Cross binary not found. Ensure BinFS is active or run manually:"
  echo "${CROSS_BIN} ${ABS_TARGET_DIR}"
fi

exit "${EXIT_CODE}"
