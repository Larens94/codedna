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
# Supported AI tools: claude claude-hooks cursor copilot cline windsurf opencode
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
do_claude_hooks() {
    TOOLS_RAW="https://raw.githubusercontent.com/Larens94/codedna/main/tools"
    mkdir -p "$REPO_ROOT/tools"
    curl -fsSL "$TOOLS_RAW/claude_hook_codedna.sh" > "$REPO_ROOT/tools/claude_hook_codedna.sh"
    chmod +x "$REPO_ROOT/tools/claude_hook_codedna.sh"
    curl -fsSL "$TOOLS_RAW/claude_hook_stop.sh" > "$REPO_ROOT/tools/claude_hook_stop.sh"
    chmod +x "$REPO_ROOT/tools/claude_hook_stop.sh"
    curl -fsSL "$TOOLS_RAW/validate_manifests.py" > "$REPO_ROOT/tools/validate_manifests.py"
    echo "  OK  Claude Hooks   -> tools/claude_hook_codedna.sh, claude_hook_stop.sh"
    # Create .claude/settings.local.json with hooks if it doesn't exist
    SETTINGS="$REPO_ROOT/.claude/settings.local.json"
    if [[ ! -f "$SETTINGS" ]]; then
        mkdir -p "$REPO_ROOT/.claude"
        cat > "$SETTINGS" << 'SETTINGSEOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.8 — validating annotations..." }]
      },
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.8 — validating annotations..." }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_stop.sh", "timeout": 5, "statusMessage": "CodeDNA v0.8 — checking session end protocol..." }]
      }
    ]
  }
}
SETTINGSEOF
        echo "  OK  Settings       -> .claude/settings.local.json (hooks configured)"
    else
        echo "  !!  .claude/settings.local.json already exists — add hooks manually"
        echo "      See: https://github.com/Larens94/codedna#claude-code-hooks"
    fi
}

case "$TOOL" in
    claude)   do_claude ;;
    cursor)   do_cursor ;;
    copilot)  do_copilot ;;
    cline)    do_cline ;;
    windsurf) do_windsurf ;;
    agents)   do_agents ;;
    opencode)      do_opencode ;;
    claude-hooks)  do_claude_hooks ;;
    all)           do_claude; do_cursor; do_copilot; do_cline; do_windsurf; do_agents; do_opencode; do_claude_hooks ;;
    *) echo "Usage: install.sh [claude|claude-hooks|cursor|copilot|cline|windsurf|agents|opencode|all]"; exit 1 ;;
esac

echo ""
echo "Done. For full enforcement, install the CLI:"
echo "  pip install git+https://github.com/Larens94/codedna.git && codedna install"
