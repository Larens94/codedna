#!/usr/bin/env bash
# CodeDNA v0.9 — GitHub Copilot hooks script
# Place in: .github/hooks/codedna.sh (make executable)
# Called by .github/hooks/hooks.json for session_start, post_tool_use, session_end.
#
# Receives JSON via stdin (postToolUse). Mode passed as $1.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
VALIDATOR="$REPO_ROOT/tools/validate_manifests.py"
MODE="${1:-post_tool_use}"

case "$MODE" in

  session_start)
    CODEDNA=".codedna"
    if [[ -f "$CODEDNA" ]]; then
        PKGS=$(grep -c 'purpose:' "$CODEDNA" 2>/dev/null || echo "0")
        PROJ=$(grep '^project:' "$CODEDNA" | head -1 | cut -d' ' -f2- | tr -d '"')
        echo "[CodeDNA] Project: $PROJ — $PKGS documented modules. Read .codedna and the module docstring before editing any source file. Every edit requires updating agent: with today's date."
    fi
    ;;

  post_tool_use)
    INPUT=$(cat)
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('file_path', inp.get('path', '')))" 2>/dev/null || echo "")

    [[ -z "$FILE_PATH" ]] && exit 0
    echo "$FILE_PATH" | grep -qE '\.(py|ts|tsx|js|jsx|go|rs|java|kt|swift|rb|cs|php)$' || exit 0
    BASENAME=$(basename "$FILE_PATH")
    [[ "$BASENAME" == "__init__.py" ]] && exit 0
    [[ "$FILE_PATH" == *"/migrations/"* || "$FILE_PATH" == *"/node_modules/"* ]] && exit 0
    [[ "$FILE_PATH" == *"/venv/"* || "$FILE_PATH" == *"/.venv/"* ]] && exit 0

    if [[ ! -f "$VALIDATOR" ]]; then
        echo "⚠ CodeDNA: validate_manifests.py not found — skipping check"
        exit 0
    fi

    OUTPUT=$(python3 "$VALIDATOR" "$FILE_PATH" 2>&1) || true
    if echo "$OUTPUT" | grep -q "^FAIL "; then
        ERRORS=$(echo "$OUTPUT" | grep -E "error:|missing:" | head -5)
        echo ""
        echo "━━━ CodeDNA v0.9 — annotation missing or incomplete ━━━"
        echo "File: $FILE_PATH"
        echo "$ERRORS" | sed 's/^/  /'
        echo ""
        echo "Add exports: / used_by: / rules: / agent: to the module docstring."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
    ;;

  session_end)
    CHANGED=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb)$' || true)
    STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb)$' || true)
    if [[ -n "$CHANGED" ]] || [[ -n "$STAGED" ]]; then
        echo ""
        echo "━━━ CodeDNA v0.9 — session end protocol ━━━"
        echo "Source files were modified. Remember to:"
        echo "  1. Append an agent_sessions: entry to .codedna"
        echo "  2. Commit with AI git trailers: AI-Agent, AI-Provider, AI-Session, AI-Visited, AI-Message"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
    ;;

esac

exit 0
