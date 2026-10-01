#!/usr/bin/env bash
# Fast pre-command filter:
# Only fire the hook if the command being executed is a git command.
# Non-git commands bypass the hook immediately with zero Python overhead.

PAYLOAD=$(cat)

# Extract CommandLine from JSON payload if jq is available
CMD=""
if command -v jq >/dev/null 2>&1; then
  CMD=$(printf '%s' "$PAYLOAD" | jq -r '.toolCall.args.CommandLine // empty' 2>/dev/null)
fi

# Determine if the command is a git invocation
IS_GIT=false
if [ -n "$CMD" ]; then
  if [[ "$CMD" =~ (^|[;&|[:space:]/])git([[:space:]]|$) ]]; then
    IS_GIT=true
  fi
else
  # Fallback regex search on raw payload
  if printf '%s' "$PAYLOAD" | grep -qE '"CommandLine":\s*"[^"]*(^|[;&|[:space:]/])git([[:space:]]|$)'; then
    IS_GIT=true
  fi
fi

if [ "$IS_GIT" = false ]; then
  printf '{"decision": "allow"}\n'
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '%s' "$PAYLOAD" | exec python3 "${SCRIPT_DIR}/pre_command_hook.py"
