#!/usr/bin/env bash
# CodeDNA v0.8 — Cursor afterFileEdit hook
# Place in: .cursor/hooks/after-file-edit.sh (make executable)
# Requires: Cursor v1.7+
#
# Receives JSON via stdin with the file path that was just edited.
# Validates CodeDNA header on source files.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
VALIDATOR="$REPO_ROOT/tools/validate_manifests.py"

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('file_path', data.get('path', '')))" 2>/dev/null || echo "")

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
    echo "━━━ CodeDNA v0.8 — annotation missing or incomplete ━━━"
    echo "File: $FILE_PATH"
    echo "$ERRORS" | sed 's/^/  /'
    echo ""
    echo "Add exports: / used_by: / rules: / agent: to the module docstring."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

exit 0
