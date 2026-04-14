#!/usr/bin/env bash
# claude_hook_codedna.sh — Claude Code PostToolUse hook for CodeDNA v0.8 enforcement.
#
# Receives JSON on stdin from Claude Code with tool_name, tool_input, tool_output.
# Validates that Python/TS/Go/etc files have a CodeDNA v0.8 header after Write or Edit.
#
# Exit 0 = OK (feedback shown to agent)
# Exit 2 = block (prevents the tool action — only for PreToolUse, not PostToolUse)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
VALIDATOR="$REPO_ROOT/tools/validate_manifests.py"

# Read JSON from stdin
INPUT=$(cat)

# Extract file_path from tool_input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('file_path', ''))
" 2>/dev/null || echo "")

# No file path — nothing to check
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only check source files
if ! echo "$FILE_PATH" | grep -qE '\.(py|ts|tsx|js|jsx|go|rs|java|kt|swift|rb|cs|php)$'; then
    exit 0
fi

# Skip test files, __init__.py, migrations, experiments/runs
BASENAME=$(basename "$FILE_PATH")
if [[ "$BASENAME" == "__init__.py" ]] || \
   [[ "$BASENAME" == "conftest.py" ]] || \
   [[ "$FILE_PATH" == *"/migrations/"* ]] || \
   [[ "$FILE_PATH" == *"/experiments/runs/"* ]] || \
   [[ "$FILE_PATH" == *"/node_modules/"* ]] || \
   [[ "$FILE_PATH" == *"/venv/"* ]] || \
   [[ "$FILE_PATH" == *"/.venv/"* ]]; then
    exit 0
fi

# Check if validator exists
if [[ ! -f "$VALIDATOR" ]]; then
    echo "⚠ CodeDNA: validate_manifests.py not found — skipping check"
    exit 0
fi

# Run validation
OUTPUT=$(python3 "$VALIDATOR" "$FILE_PATH" 2>&1) || true

if echo "$OUTPUT" | grep -q "^FAIL "; then
    # Extract errors
    ERRORS=$(echo "$OUTPUT" | grep -E "error:|missing:" | head -5)
    echo ""
    echo "━━━ CodeDNA v0.8 — annotation missing or incomplete ━━━"
    echo "File: $FILE_PATH"
    echo "$ERRORS" | sed 's/^/  /'
    echo ""
    echo "Required header (Python):"
    echo '  """filename.py — purpose ≤15 words.'
    echo ""
    echo "  exports: function(arg) -> type"
    echo "  used_by: caller.py → caller_fn"
    echo "  rules:   constraint"
    echo '  agent:   model-id | YYYY-MM-DD | what you did'
    echo '  """'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    # Exit 0 — PostToolUse can't block, but feedback goes to the agent
    exit 0
fi

# L2 check: public functions without Rules: docstring (Python only)
if [[ "$FILE_PATH" == *.py ]]; then
    L2_ISSUES=$(python3 -c "
import ast, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith('_'):
                continue
            doc = ast.get_docstring(node) or ''
            if 'Rules:' not in doc:
                print(f'  L2: {node.name}() (line {node.lineno}) — missing Rules: docstring')
except Exception:
    pass
" "$FILE_PATH" 2>/dev/null || true)

    if [[ -n "$L2_ISSUES" ]]; then
        echo ""
        echo "━━━ CodeDNA v0.8 — L2 function annotations ━━━"
        echo "File: $FILE_PATH"
        echo "$L2_ISSUES"
        echo ""
        echo "Add Rules: and message: to public function docstrings:"
        echo '  def my_function():'
        echo '      """Short description.'
        echo ''
        echo '      Rules:   constraint the agent must respect'
        echo '      message: model-id | YYYY-MM-DD | observation for next agent'
        echo '      """'
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
fi

exit 0
