#!/usr/bin/env bash
# CodeDNA v0.5 — Integration Installer
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh)
#   bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cursor
#
# Installs CodeDNA rules for: claude cursor copilot cline windsurf agents (default: all)

set -euo pipefail

TOOL="${1:-all}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RAW="https://raw.githubusercontent.com/Larens94/codedna/main/integrations"

echo "🧬 CodeDNA v0.5 Integration Installer"
echo "   Target: $REPO_ROOT"
echo ""

do_claude()   { curl -fsSL "$RAW/CLAUDE.md"               > "$REPO_ROOT/CLAUDE.md";                          echo "✅ Claude Code    → CLAUDE.md"; }
do_cursor()   { curl -fsSL "$RAW/.cursorrules"             > "$REPO_ROOT/.cursorrules";                       echo "✅ Cursor         → .cursorrules"; }
do_copilot()  { mkdir -p "$REPO_ROOT/.github"; curl -fsSL "$RAW/copilot-instructions.md" > "$REPO_ROOT/.github/copilot-instructions.md"; echo "✅ GitHub Copilot → .github/copilot-instructions.md"; }
do_cline()    { curl -fsSL "$RAW/.clinerules"              > "$REPO_ROOT/.clinerules";                        echo "✅ Cline          → .clinerules"; }
do_windsurf() { curl -fsSL "$RAW/.windsurfrules"           > "$REPO_ROOT/.windsurfrules";                     echo "✅ Windsurf       → .windsurfrules"; }
do_agents()   { mkdir -p "$REPO_ROOT/.agents/workflows"; curl -fsSL "$RAW/.agents/workflows/codedna.md" > "$REPO_ROOT/.agents/workflows/codedna.md"; echo "✅ Antigravity    → .agents/workflows/codedna.md"; }

case "$TOOL" in
    claude)   do_claude ;;
    cursor)   do_cursor ;;
    copilot)  do_copilot ;;
    cline)    do_cline ;;
    windsurf) do_windsurf ;;
    agents)   do_agents ;;
    all)      do_claude; do_cursor; do_copilot; do_cline; do_windsurf; do_agents ;;
    *) echo "Usage: install.sh [claude|cursor|copilot|cline|windsurf|agents|all]"; exit 1 ;;
esac

echo ""
echo "🧬 Done. Verify: ask your AI to create a file — it should start with a CodeDNA v0.5 module docstring."
