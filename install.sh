#!/usr/bin/env bash
# ==============================================================================
# Cloud AI FDE Agent Software Factory (fde-agent-factory) Installer & Linker
# ==============================================================================
# Supports two primary installation modes:
#   1. --link (Default): Symlinks .agents/, .gemini/commands/, AGENTS.md,
#      .gitmessage.txt, and OKF templates directly to this plugin repository so
#      any local edits in the host workspace automatically update the tracked
#      files in the fde-agent-factory git repository.
#   2. --copy: Copies all skills, workflows, hooks, slash commands, governance
#      rules, and OKF/Mermaid starter templates as standalone files into a
#      target repository.
#
# Optional Flags:
#   --force             : Overwrite existing starter docs/architecture.md or
#                         openspec/config.yaml when seeding.
#   --verify            : Run the PreToolUse hook unit test suites and exit.
# ==============================================================================

set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="link"
FORCE=false
VERIFY_ONLY=false
TARGET_ARG=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] [TARGET_WORKSPACE_DIR]

Options:
  --link                Symlink components to this fde-agent-factory clone so local
                        workspace edits directly update the plugin repo (default).
  --copy                Copy components as standalone files into the target workspace.
  --force               Overwrite existing project-level starter files (openspec/config.yaml,
                        docs/architecture.md, docs/architecture_diagram.mmd).
  --verify              Run the hook test suites (pre_command_hook & check_architecture_docs).
  -h, --help            Show this help message.

Examples:
  # 1. Clone directly into .agents/ of an existing repo and wire symlinks:
  rm -rf .agents && git clone <REPO_URL> .agents && ./.agents/install.sh --link

  # 2. Link from a local ./fde-agent-factory clone into the current workspace:
  ./fde-agent-factory/install.sh --link .

  # 3. Bootstrap a brand-new repository with standalone files:
  ./fde-agent-factory/install.sh --copy /path/to/new-repo
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --link)
      MODE="link"
      shift
      ;;
    --copy)
      MODE="copy"
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --verify)
      VERIFY_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Error: Unknown option '$1'" >&2
      usage
      exit 1
      ;;
    *)
      TARGET_ARG="$1"
      shift
      ;;
  esac
done

run_verification() {
  echo "==> Running fde-agent-factory PreToolUse hook unit tests..."
  python3 -m unittest discover -s "${PLUGIN_DIR}/scripts" -p "test_*.py" -v
  echo "==> All fde-agent-factory verification checks passed!"
}

if [[ "$VERIFY_ONLY" == true ]]; then
  run_verification
  exit 0
fi

# Determine TARGET_DIR
if [[ -n "$TARGET_ARG" ]]; then
  mkdir -p "$TARGET_ARG"
  TARGET_DIR="$(cd "$TARGET_ARG" && pwd)"
else
  # If invoked as ./.agents/install.sh or ./fde-agent-factory/install.sh from parent
  PARENT_DIR="$(cd "${PLUGIN_DIR}/.." && pwd)"
  if [[ "$(pwd)" != "$PLUGIN_DIR" ]]; then
    TARGET_DIR="$(pwd)"
  else
    TARGET_DIR="$PARENT_DIR"
  fi
fi

echo "=============================================================================="
echo "Cloud AI FDE Agent Software Factory Installer"
echo "  Plugin Source : ${PLUGIN_DIR}"
echo "  Target Repo   : ${TARGET_DIR}"
echo "  Install Mode  : ${MODE}"
echo "=============================================================================="

# Helper to compute relative path from a source directory to a target path using python3
relpath() {
  local from_dir="$1"
  local to_path="$2"
  python3 -c "import os, sys; print(os.path.relpath(sys.argv[2], sys.argv[1]))" "$from_dir" "$to_path"
}

# Helper to link or copy a file/directory
install_item() {
  local src="$1"
  local dst="$2"
  local dst_parent
  dst_parent="$(dirname "$dst")"
  mkdir -p "$dst_parent"

  if [[ "$MODE" == "link" ]]; then
    local rel_src
    rel_src="$(relpath "$dst_parent" "$src")"
    rm -rf "$dst"
    ln -s "$rel_src" "$dst"
    echo "  [LINK] ${dst#${TARGET_DIR}/} -> ${rel_src}"
  else
    rm -rf "$dst"
    cp -a "$src" "$dst"
    echo "  [COPY] ${dst#${TARGET_DIR}/}"
  fi
}

# Helper to seed project-specific starter files only if missing (or --force)
seed_if_missing() {
  local src="$1"
  local dst="$2"
  local dst_parent
  dst_parent="$(dirname "$dst")"
  mkdir -p "$dst_parent"

  if [[ ! -e "$dst" || "$FORCE" == true ]]; then
    cp -a "$src" "$dst"
    echo "  [SEED] ${dst#${TARGET_DIR}/}"
  else
    echo "  [SKIP] ${dst#${TARGET_DIR}/} (already exists; use --force to overwrite)"
  fi
}

# 1. Install .agents/ customization directory
if [[ "$PLUGIN_DIR" == "${TARGET_DIR}/.agents" ]]; then
  echo "==> [1/5] Plugin is already cloned directly at ${TARGET_DIR}/.agents (in-place mode)."
elif [[ "$MODE" == "link" ]]; then
  echo "==> [1/5] Linking .agents/ directory to plugin repository..."
  install_item "$PLUGIN_DIR" "${TARGET_DIR}/.agents"
else
  echo "==> [1/5] Copying .agents/ components into ${TARGET_DIR}/.agents/..."
  mkdir -p "${TARGET_DIR}/.agents"
  for item in hooks.json README.md plugin.json scripts skills skill-library workflows; do
    if [[ -e "${PLUGIN_DIR}/${item}" ]]; then
      install_item "${PLUGIN_DIR}/${item}" "${TARGET_DIR}/.agents/${item}"
    fi
  done
fi

# 2. Install .gemini/commands/ slash command TOML definitions
echo "==> [2/5] Installing Gemini CLI slash commands (.gemini/commands/)..."
mkdir -p "${TARGET_DIR}/.gemini"
install_item "${PLUGIN_DIR}/commands" "${TARGET_DIR}/.gemini/commands"

# 3. Install AGENTS.md and .gitmessage.txt governance rules
echo "==> [3/5] Installing repository governance (AGENTS.md & .gitmessage.txt)..."
install_item "${PLUGIN_DIR}/rules/AGENTS.md" "${TARGET_DIR}/AGENTS.md"
install_item "${PLUGIN_DIR}/templates/.gitmessage.txt" "${TARGET_DIR}/.gitmessage.txt"

if [[ -d "${TARGET_DIR}/.git" ]]; then
  git -C "$TARGET_DIR" config commit.template .gitmessage.txt || true
  echo "  [GIT]  Configured git commit.template = .gitmessage.txt"
fi

# 4. Install OpenSpec Spec-Driven Development structure
echo "==> [4/5] Ensuring OpenSpec directory structure (openspec/)..."
mkdir -p "${TARGET_DIR}/openspec/specs" "${TARGET_DIR}/openspec/changes"
seed_if_missing "${PLUGIN_DIR}/templates/openspec/config.yaml" "${TARGET_DIR}/openspec/config.yaml"

# 5. Install Google OKF Specification, Templates & Starter Mermaid Architecture Docs
echo "==> [5/5] Installing Google OKF templates & Mermaid architecture starter kit (docs/)..."
mkdir -p "${TARGET_DIR}/docs/knowledge_base/cloudtop_env" \
         "${TARGET_DIR}/docs/knowledge_base/codebase" \
         "${TARGET_DIR}/docs/knowledge_base/deployed_gcp_assets"

install_item "${PLUGIN_DIR}/docs/knowledge_base/OKF_SPEC.md" "${TARGET_DIR}/docs/knowledge_base/OKF_SPEC.md"
install_item "${PLUGIN_DIR}/docs/knowledge_base/TEMPLATE.md" "${TARGET_DIR}/docs/knowledge_base/TEMPLATE.md"
install_item "${PLUGIN_DIR}/docs/knowledge_base/templates" "${TARGET_DIR}/docs/knowledge_base/templates"

seed_if_missing "${PLUGIN_DIR}/docs/architecture.md" "${TARGET_DIR}/docs/architecture.md"
seed_if_missing "${PLUGIN_DIR}/docs/architecture_diagram.mmd" "${TARGET_DIR}/docs/architecture_diagram.mmd"
seed_if_missing "${PLUGIN_DIR}/docs/knowledge_base/README.md" "${TARGET_DIR}/docs/knowledge_base/README.md"

# If no OKF entries exist yet in any category, seed the starter plugin entry so pre-push checks pass out of the box
EXISTING_OKF_COUNT=$(find "${TARGET_DIR}/docs/knowledge_base/cloudtop_env" \
                          "${TARGET_DIR}/docs/knowledge_base/codebase" \
                          "${TARGET_DIR}/docs/knowledge_base/deployed_gcp_assets" \
                          -maxdepth 2 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$EXISTING_OKF_COUNT" -eq 0 ]]; then
  seed_if_missing "${PLUGIN_DIR}/docs/knowledge_base/cloudtop_env/fde-agent-factory-plugin.md" \
                  "${TARGET_DIR}/docs/knowledge_base/cloudtop_env/fde-agent-factory-plugin.md"
fi

echo "=============================================================================="
echo "Installation complete! Running hook verification suite..."
run_verification
