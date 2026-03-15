#!/usr/bin/env bash
# CodeDNA v0.3 — Integration installer
# Usage: bash install.sh [--tool claude|cursor|copilot|cline|windsurf|all]
# Default: installs all available integrations

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TOOL="${1:-all}"

install_claude() {
    cp "$SCRIPT_DIR/CLAUDE.md" "$REPO_ROOT/CLAUDE.md"
    echo "✅ Claude Code: CLAUDE.md installed"
}
install_cursor() {
    cp "$SCRIPT_DIR/.cursorrules" "$REPO_ROOT/.cursorrules"
    echo "✅ Cursor: .cursorrules installed"
}
install_copilot() {
    mkdir -p "$REPO_ROOT/.github"
    cp "$SCRIPT_DIR/copilot-instructions.md" "$REPO_ROOT/.github/copilot-instructions.md"
    echo "✅ GitHub Copilot: .github/copilot-instructions.md installed"
}
install_cline() {
    cp "$SCRIPT_DIR/.clinerules" "$REPO_ROOT/.clinerules"
    echo "✅ Cline: .clinerules installed"
}
install_windsurf() {
    cp "$SCRIPT_DIR/.windsurfrules" "$REPO_ROOT/.windsurfrules"
    echo "✅ Windsurf: .windsurfrules installed"
}
install_agents() {
    mkdir -p "$REPO_ROOT/.agents/workflows"
    cp "$SCRIPT_DIR/.agents/workflows/codedna.md" "$REPO_ROOT/.agents/workflows/codedna.md"
    echo "✅ Antigravity/.agents: .agents/workflows/codedna.md installed"
}

echo "🧬 CodeDNA v0.3 Integration Installer"
echo "Target: $REPO_ROOT"
echo ""

case "$TOOL" in
    claude)    install_claude ;;
    cursor)    install_cursor ;;
    copilot)   install_copilot ;;
    cline)     install_cline ;;
    windsurf)  install_windsurf ;;
    agents)    install_agents ;;
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
echo "🧬 Done. Your AI tools now follow CodeDNA v0.3."
echo "   Verify: ask your AI to create a new file — it should start with # === CODEDNA:0.3"
