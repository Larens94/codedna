#!/usr/bin/env bash
# CodeDNA v0.8 — Cline PostToolUse hook
# Place in: .clinerules/hooks/PostToolUse.sh (make executable)
# Requires: Cline v3.36+
#
# Receives JSON via stdin with tool name and input.
# Validates CodeDNA header on every source file write/edit.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
VALIDATOR="$REPO_ROOT/tools/validate_manifests.py"

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
[[ "$FILE_PATH" == *"/migrations/"* ]] && exit 0
[[ "$FILE_PATH" == *"/node_modules/"* ]] && exit 0
[[ "$FILE_PATH" == *"/venv/"* || "$FILE_PATH" == *"/.venv/"* ]] && exit 0

if [[ ! -f "$VALIDATOR" ]]; then
    echo '{"output": "⚠ CodeDNA: validate_manifests.py not found — skipping check"}'
    exit 0
fi

OUTPUT=$(python3 "$VALIDATOR" "$FILE_PATH" 2>&1) || true

if echo "$OUTPUT" | grep -q "^FAIL "; then
    ERRORS=$(echo "$OUTPUT" | grep -E "error:|missing:" | head -5 | sed 's/^/  /')
    MSG="CodeDNA v0.8 — annotation missing or incomplete\nFile: $FILE_PATH\n$ERRORS\n\nAdd to the top of the file:\n  exports: / used_by: / rules: / agent: fields"
    echo "{\"output\": \"$(echo "$MSG" | sed 's/"/\\"/g' | tr '\n' '|')\"}"
fi

exit 0
