#!/usr/bin/env bash
# CodeDNA PreToolUse hook — reminds agent to read docstring before editing Python files.
set -euo pipefail

EVENT=$(cat)

FILE=$(echo "$EVENT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    path = (data.get('tool_input') or {}).get('file_path', '')
    print(path)
except Exception:
    print('')
" 2>/dev/null || true)

if [[ -z "$FILE" ]]; then
  exit 0
fi

# Only source files
case "$FILE" in
  *.py|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.go|*.rs|*.java|*.kt|*.kts|*.swift|*.rb|*.cs|*.php) ;;
  *) exit 0 ;;
esac

if [[ ! -f "$FILE" ]]; then
  exit 0
fi

# Check if file has CodeDNA header
HAS=$(head -15 "$FILE" | grep -c "exports:" 2>/dev/null || echo "0")

if [[ "$HAS" -gt 0 ]]; then
  TODAY=$(date +%Y-%m-%d)
  echo "[CodeDNA] Python file. Before editing: (1) read the docstring, (2) verify exports/used_by/rules/agent, (3) plan agent: update with the current session."
fi

exit 0
