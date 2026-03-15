#!/usr/bin/env bash
# CodeDNA v0.3 — Integration Installer
# Works in two modes:
#   1. Via curl:  bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh)
#   2. Local:     bash integrations/install.sh [tool]
#
# Optional argument: claude | cursor | copilot | cline | windsurf | agents | all (default: all)

set -euo pipefail

TOOL="${1:-all}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RAW_BASE="https://raw.githubusercontent.com/Larens94/codedna/main/integrations"

# Detect if running from repo (local) or via curl pipe
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [[ "$SCRIPT_PATH" == /dev/fd/* ]] || [[ -z "$SCRIPT_PATH" ]]; then
    MODE="remote"
else
    SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
    MODE="local"
fi

echo "🧬 CodeDNA v0.3 Integration Installer"
echo "   Mode:   $MODE"
echo "   Target: $REPO_ROOT"
echo ""

# Helper: get file content (local or GitHub download)
get_file() {
    local name="$1"
    if [[ "$MODE" == "local" ]] && [[ -f "$SCRIPT_DIR/$name" ]]; then
        cat "$SCRIPT_DIR/$name"
    else
        curl -fsSL "$RAW_BASE/$name"
    fi
}

install_claude() {
    get_file "CLAUDE.md" > "$REPO_ROOT/CLAUDE.md"
    echo "✅ Claude Code    → CLAUDE.md"
}

install_cursor() {
    get_file ".cursorrules" > "$REPO_ROOT/.cursorrules"
    echo "✅ Cursor         → .cursorrules"
}

install_copilot() {
    mkdir -p "$REPO_ROOT/.github"
    get_file "copilot-instructions.md" > "$REPO_ROOT/.github/copilot-instructions.md"
    echo "✅ GitHub Copilot → .github/copilot-instructions.md"
}

install_cline() {
    get_file ".clinerules" > "$REPO_ROOT/.clinerules"
    echo "✅ Cline          → .clinerules"
}

install_windsurf() {
    get_file ".windsurfrules" > "$REPO_ROOT/.windsurfrules"
    echo "✅ Windsurf       → .windsurfrules"
}

install_agents() {
    mkdir -p "$REPO_ROOT/.agents/workflows"
    curl -fsSL "$RAW_BASE/.agents/workflows/codedna.md" > "$REPO_ROOT/.agents/workflows/codedna.md"
    echo "✅ Antigravity    → .agents/workflows/codedna.md"
}

case "$TOOL" in
    claude)   install_claude ;;
    cursor)   install_cursor ;;
    copilot)  install_copilot ;;
    cline)    install_cline ;;
    windsurf) install_windsurf ;;
    agents)   install_agents ;;
    all)
        install_claude
        install_cursor
        install_copilot
        install_cline
        install_windsurf
        install_agents
        ;;
    *)
        echo "Usage: bash install.sh [claude|cursor|copilot|cline|windsurf|agents|all]"
        exit 1
        ;;
esac

echo ""
echo "🧬 Done. CodeDNA v0.3 is active in your repo."
echo ""
echo "   Verify: ask your AI to create a new file."
echo "   It should start with:  # === CODEDNA:0.3"
