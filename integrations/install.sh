#!/usr/bin/env bash
# CodeDNA v0.8 — One-Line Installer
#
# Usage (recommended — installs CLI + hook + prompt):
#   pip install git+https://github.com/Larens94/codedna.git && codedna install
#   pip install git+https://github.com/Larens94/codedna.git && codedna install --tools claude cursor
#   pip install git+https://github.com/Larens94/codedna.git && codedna install --tools all
#
# Usage (legacy — prompt files only, no CLI):
#   bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh)
#   bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) claude
#
# What this does:
#   1. pip install codedna  — CLI tool with multi-language support (11 languages)
#   2. codedna install      — pre-commit hook + AI tool prompt + .codedna manifest
#
# Supported AI tools: claude cursor copilot cline windsurf opencode
# Supported languages: Python, TypeScript/JS, Go, PHP, Rust, Java, Kotlin, Ruby, C#, Swift

set -euo pipefail

TOOL="${1:-all}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RAW="https://raw.githubusercontent.com/Larens94/codedna/main/integrations"

# ── Check if codedna CLI is available ─────────────────────────────────────────

if command -v codedna &>/dev/null; then
    echo "CodeDNA CLI detected — using 'codedna install' (recommended path)"
    echo ""
    if [[ "$TOOL" == "all" ]]; then
        codedna install --path "$REPO_ROOT" --tools all
    else
        codedna install --path "$REPO_ROOT" --tools "$TOOL"
    fi
    exit $?
fi

# ── Fallback: curl-based install (prompt files only) ──────────────────────────

echo "CodeDNA v0.8 — Integration Installer (prompt files only)"
echo "  Target: $REPO_ROOT"
echo ""
echo "  TIP: For full setup (pre-commit hook + validation), run:"
echo "       pip install git+https://github.com/Larens94/codedna.git && codedna install"
echo ""

do_claude()   { curl -fsSL "$RAW/CLAUDE.md"               > "$REPO_ROOT/CLAUDE.md";                          echo "  OK  Claude Code    -> CLAUDE.md"; }
do_cursor()   { curl -fsSL "$RAW/.cursorrules"             > "$REPO_ROOT/.cursorrules";                       echo "  OK  Cursor         -> .cursorrules"; }
do_copilot()  { mkdir -p "$REPO_ROOT/.github"; curl -fsSL "$RAW/copilot-instructions.md" > "$REPO_ROOT/.github/copilot-instructions.md"; echo "  OK  GitHub Copilot -> .github/copilot-instructions.md"; }
do_cline()    { curl -fsSL "$RAW/.clinerules"              > "$REPO_ROOT/.clinerules";                        echo "  OK  Cline          -> .clinerules"; }
do_windsurf() { curl -fsSL "$RAW/.windsurfrules"           > "$REPO_ROOT/.windsurfrules";                     echo "  OK  Windsurf       -> .windsurfrules"; }
do_agents()   { mkdir -p "$REPO_ROOT/.agents/workflows"; curl -fsSL "$RAW/.agents/workflows/codedna.md" > "$REPO_ROOT/.agents/workflows/codedna.md"; echo "  OK  Antigravity    -> .agents/workflows/codedna.md"; }
do_opencode() {
    curl -fsSL "$RAW/AGENTS.md" > "$REPO_ROOT/AGENTS.md"
    echo "  OK  OpenCode       -> AGENTS.md"
    mkdir -p "$REPO_ROOT/.opencode/plugins"
    curl -fsSL "$RAW/opencode-plugin/codedna.js" > "$REPO_ROOT/.opencode/plugins/codedna.js"
    echo "  OK  OpenCode Plugin -> .opencode/plugins/codedna.js"
}

case "$TOOL" in
    claude)   do_claude ;;
    cursor)   do_cursor ;;
    copilot)  do_copilot ;;
    cline)    do_cline ;;
    windsurf) do_windsurf ;;
    agents)   do_agents ;;
    opencode) do_opencode ;;
    all)      do_claude; do_cursor; do_copilot; do_cline; do_windsurf; do_agents; do_opencode ;;
    *) echo "Usage: install.sh [claude|cursor|copilot|cline|windsurf|agents|opencode|all]"; exit 1 ;;
esac

echo ""
echo "Done. For full enforcement, install the CLI:"
echo "  pip install git+https://github.com/Larens94/codedna.git && codedna install"
