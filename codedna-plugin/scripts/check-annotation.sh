#!/usr/bin/env bash
# CodeDNA post-write annotation checker.
# Receives PostToolUse event JSON on stdin.
# Outputs a warning to stdout if the written file lacks a CodeDNA module annotation.

set -euo pipefail

# Read event JSON from stdin
EVENT=$(cat)

# Extract file path (Write uses file_path, Edit uses file_path)
FILE=$(echo "$EVENT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    path = (data.get('tool_input') or {}).get('file_path', '')
    print(path)
except Exception:
    print('')
" 2>/dev/null || true)

# Skip if no file path
if [[ -z "$FILE" ]]; then
  exit 0
fi

# Skip non-source files
case "$FILE" in
  *.py|*.ts|*.tsx|*.js|*.mjs|*.go|*.rs|*.java) ;;
  *) exit 0 ;;
esac

# Skip if file does not exist
if [[ ! -f "$FILE" ]]; then
  exit 0
fi

# Check for CodeDNA annotation
HAS_ANNOTATION=$(python3 - "$FILE" <<'PYEOF'
import sys, ast

filepath = sys.argv[1]

try:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        src = f.read()
except Exception:
    sys.exit(0)

# Python: check module docstring
if filepath.endswith('.py'):
    try:
        tree = ast.parse(src)
        if (tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)):
            doc = tree.body[0].value.value
            if 'exports:' in doc and 'used_by:' in doc:
                sys.exit(0)
    except Exception:
        pass
    sys.exit(1)

# Other languages: check first comment block (first 20 lines)
lines = src.splitlines()[:20]
block = '\n'.join(lines)
if 'exports:' in block and 'used_by:' in block:
    sys.exit(0)
sys.exit(1)
PYEOF
)
STATUS=$?

if [[ $STATUS -ne 0 ]]; then
  echo ""
  echo "CODEDNA NOTICE: $FILE is missing a CodeDNA module annotation."
  echo "Add a module docstring with exports:, used_by:, and rules: fields before the next commit."
  echo "See: https://github.com/Larens94/codedna#writing-new-files"
fi

exit 0
