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
#   1. pip install codedna  — CLI tool with multi-language support (9 languages + templates)
#   2. codedna install      — pre-commit hook + AI tool prompt + .codedna manifest
#
# Supported AI tools: claude claude-hooks cursor cursor-hooks copilot copilot-hooks cline cline-hooks windsurf opencode opencode-hooks
# Supported languages: Python, TypeScript/JS, Go, PHP, Java, Kotlin, Ruby, Rust, C#

set -euo pipefail

TOOL="${1:-all}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RAW="https://raw.githubusercontent.com/Larens94/codedna/main/integrations"

# ── Check if codedna CLI is available ─────────────────────────────────────────

if command -v codedna &>/dev/null; then
    echo "CodeDNA CLI detected — using 'codedna install' (recommended path)"
    echo ""
    # Per le varianti *-hooks, installare anche il prompt base
    case "$TOOL" in
        claude-hooks)  codedna install --path "$REPO_ROOT" --tools claude claude-hooks ;;
        cursor-hooks)  codedna install --path "$REPO_ROOT" --tools cursor cursor-hooks ;;
        copilot-hooks) codedna install --path "$REPO_ROOT" --tools copilot copilot-hooks ;;
        cline-hooks)   codedna install --path "$REPO_ROOT" --tools cline cline-hooks ;;
        opencode-hooks) codedna install --path "$REPO_ROOT" --tools opencode opencode-hooks ;;
        all)           codedna install --path "$REPO_ROOT" --tools all ;;
        *)             codedna install --path "$REPO_ROOT" --tools "$TOOL" ;;
    esac
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

do_cline_hooks() {
    mkdir -p "$REPO_ROOT/.clinerules/hooks"
    curl -fsSL "$RAW/cline-hooks/PostToolUse.sh" > "$REPO_ROOT/.clinerules/hooks/PostToolUse.sh"
    chmod +x "$REPO_ROOT/.clinerules/hooks/PostToolUse.sh"
    curl -fsSL "$RAW/cline-hooks/TaskStart.sh" > "$REPO_ROOT/.clinerules/hooks/TaskStart.sh"
    chmod +x "$REPO_ROOT/.clinerules/hooks/TaskStart.sh"
    echo "  OK  Cline Hooks    -> .clinerules/hooks/ (PostToolUse, TaskStart)"
    echo "      Requires: Cline v3.36+"
}

do_copilot_hooks() {
    mkdir -p "$REPO_ROOT/.github/hooks"
    curl -fsSL "$RAW/copilot-hooks/hooks.json" > "$REPO_ROOT/.github/hooks/hooks.json"
    curl -fsSL "$RAW/copilot-hooks/codedna.sh" > "$REPO_ROOT/.github/hooks/codedna.sh"
    chmod +x "$REPO_ROOT/.github/hooks/codedna.sh"
    echo "  OK  Copilot Hooks  -> .github/hooks/hooks.json + codedna.sh"
    echo "      Requires: GitHub Copilot with hooks support"
}

do_cursor_hooks() {
    TOOLS_RAW="https://raw.githubusercontent.com/Larens94/codedna/main/tools"
    mkdir -p "$REPO_ROOT/.cursor/hooks" "$REPO_ROOT/tools"
    curl -fsSL "$RAW/cursor-hooks/after-file-edit.sh" > "$REPO_ROOT/.cursor/hooks/after-file-edit.sh"
    chmod +x "$REPO_ROOT/.cursor/hooks/after-file-edit.sh"
    curl -fsSL "$RAW/cursor-hooks/stop.sh" > "$REPO_ROOT/.cursor/hooks/stop.sh"
    chmod +x "$REPO_ROOT/.cursor/hooks/stop.sh"
    curl -fsSL "$TOOLS_RAW/validate_manifests.py" > "$REPO_ROOT/tools/validate_manifests.py"
    echo "  OK  Cursor Hooks   -> .cursor/hooks/ (after-file-edit, stop)"
    echo "      Requires: Cursor v1.7+"
}
do_opencode() {
    curl -fsSL "$RAW/AGENTS.md" > "$REPO_ROOT/AGENTS.md"
    echo "  OK  OpenCode       -> AGENTS.md"
}
do_opencode_hooks() {
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
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "codedna=\".codedna\"; if [[ -f \"$codedna\" ]]; then pkgs=$(grep -c 'purpose:' \"$codedna\"); proj=$(grep '^project:' \"$codedna\" | head -1 | cut -d' ' -f2-); echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"SessionStart\\\",\\\"additionalContext\\\":\\\"[CodeDNA] Project: $proj — $pkgs documented modules. Read .codedna and CLAUDE.md before editing Python files. Every .py edit requires updating agent: with today's date.\\\"}}\"; fi",
          "timeout": 5
        }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "f=$(python3 -c \"import json,sys;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))\" 2>/dev/null || true); case \"$f\" in *.py|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.go|*.rs|*.java|*.kt|*.kts|*.swift|*.rb|*.cs|*.php) [[ -f \"$f\" ]] && head -15 \"$f\" | grep -q 'exports:' && echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PreToolUse\\\",\\\"additionalContext\\\":\\\"[CodeDNA] Source file. Before editing: (1) read the docstring, (2) verify exports/used_by/rules/agent, (3) plan agent: update with the current session.\\\"}}\" ;; esac; true",
          "timeout": 5
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.8 — validating annotations..." }]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "f=$(python3 -c \"import json,sys;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))\" 2>/dev/null || true); case \"$f\" in *.py|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.go|*.rs|*.java|*.kt|*.kts|*.swift|*.rb|*.cs|*.php) [[ -f \"$f\" ]] && { today=$(date +%Y-%m-%d); header=$(head -30 \"$f\"); issues=(); echo \"$header\" | grep -q 'exports:' || issues+=(\"missing exports:\"); echo \"$header\" | grep -q 'used_by:' || issues+=(\"missing used_by:\"); echo \"$header\" | grep -q 'rules:' || issues+=(\"missing rules:\"); echo \"$header\" | grep -q 'agent:' || issues+=(\"missing agent:\"); echo \"$header\" | grep -q \"$today\" || issues+=(\"agent: not updated to $today\"); if [[ ${#issues[@]} -gt 0 ]]; then msg=$(IFS=', '; echo \"${issues[*]}\"); echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PostToolUse\\\",\\\"additionalContext\\\":\\\"[CodeDNA] $f — $msg\\\"}}\"; fi; } ;; esac; true",
          "timeout": 5
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_stop.sh", "timeout": 5, "statusMessage": "CodeDNA v0.8 — checking session end protocol..." }]
      },
      {
        "hooks": [{
          "type": "command",
          "command": "echo '{\"systemMessage\": \"[CodeDNA] Remember: update .codedna with a new agent_sessions entry (agent, provider, date, session_id, task, changed, visited, message).\"}'",
          "timeout": 5
        }]
      }
    ]
  }
}
SETTINGSEOF
        echo "  OK  Settings       -> .claude/settings.local.json (hooks configured)"
        echo "      Requires: jq (brew install jq / apt install jq)"
    else
        echo "  !!  .claude/settings.local.json already exists — merge hooks manually"
        echo "      Copy the 'hooks' block from: integrations/README.md#manual-setup"
        echo "      or from: https://github.com/Larens94/codedna/tree/main/integrations#claude-code-hooks"
        echo "      IMPORTANT: merge into the existing file, do not replace it"
    fi
}

case "$TOOL" in
    claude)         do_claude ;;
    cursor)         do_cursor ;;
    copilot)        do_copilot ;;
    cline)          do_cline ;;
    windsurf)       do_windsurf ;;
    agents)         do_agents ;;
    opencode)       do_opencode ;;
    claude-hooks)   do_claude; do_claude_hooks ;;
    cline-hooks)    do_cline; do_cline_hooks ;;
    copilot-hooks)  do_copilot; do_copilot_hooks ;;
    cursor-hooks)   do_cursor; do_cursor_hooks ;;
    opencode-hooks) do_opencode; do_opencode_hooks ;;
    all)            do_claude; do_cursor; do_copilot; do_cline; do_windsurf; do_agents; do_opencode; do_claude_hooks; do_cline_hooks; do_copilot_hooks; do_cursor_hooks; do_opencode_hooks ;;
    *) echo "Usage: install.sh [claude|claude-hooks|cursor|cursor-hooks|copilot|copilot-hooks|cline|cline-hooks|windsurf|agents|opencode|opencode-hooks|all]"; exit 1 ;;
esac

echo ""
echo "Done. For full enforcement, install the CLI:"
echo "  pip install git+https://github.com/Larens94/codedna.git && codedna install"
