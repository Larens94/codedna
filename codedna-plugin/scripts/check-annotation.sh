#!/usr/bin/env bash
# CodeDNA post-write annotation checker.
# Receives PostToolUse event JSON on stdin.
# Checks L1 (module header) and L2 (function Rules:/message:) annotations.

set -euo pipefail

# Read event JSON from stdin
EVENT=$(cat)

# Extract file path
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
  *.py|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.go|*.rs|*.java|*.kt|*.kts|*.swift|*.rb|*.cs|*.php) ;;
  *) exit 0 ;;
esac

# Skip if file does not exist
if [[ ! -f "$FILE" ]]; then
  exit 0
fi

# Check L1 (module header) and L2 (function docstrings) annotations
python3 - "$FILE" <<'PYEOF'
import sys, ast

filepath = sys.argv[1]

try:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        src = f.read()
except Exception:
    sys.exit(0)

notices = []

# ── L1: Module header ──
if filepath.endswith('.py'):
    try:
        tree = ast.parse(src)
        if (tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)):
            doc = tree.body[0].value.value
            if 'exports:' not in doc or 'used_by:' not in doc:
                notices.append("L1: module docstring missing exports: or used_by:")
        else:
            notices.append("L1: no module docstring — add CodeDNA header")
    except SyntaxError:
        sys.exit(0)

    # ── L2: Function-level Rules: and message: ──
    try:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private/dunder methods
                if node.name.startswith('_'):
                    continue
                # Get docstring
                func_doc = ast.get_docstring(node) or ""
                if 'Rules:' not in func_doc:
                    notices.append(f"L2: {node.name}() (line {node.lineno}) — missing Rules: docstring")
    except Exception:
        pass

else:
    # Non-Python: check first 20 lines for L1
    lines = src.splitlines()[:20]
    block = '\n'.join(lines)
    if 'exports:' not in block or 'used_by:' not in block:
        notices.append("L1: no CodeDNA comment block found")

if notices:
    print("")
    print("CODEDNA NOTICE: " + filepath)
    for n in notices:
        print("  " + n)
    if any("L2:" in n for n in notices):
        print("")
        print("  Add a Rules: docstring to public functions:")
        print('    def my_function():')
        print('        """Short description.')
        print('')
        print('        Rules:   constraint the agent must respect')
        print('        message: model-id | YYYY-MM-DD | observation for next agent')
        print('        """')
    print("")

sys.exit(0)
PYEOF

exit 0
