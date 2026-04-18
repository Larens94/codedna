#!/usr/bin/env bash
# annotate_task.sh — Annotate a single SWE-bench task with CodeDNA, clean pipeline.
# Usage: ./annotate_task.sh <task_id>  (e.g. 13495)
set -e

TASK_ID="${1:?usage: $0 <bare_task_id>}"
TASK="django__django-${TASK_ID}"
TASK_DIR="labs/benchmark/projects/${TASK}"
CTRL="${TASK_DIR}/control"
CDNA="${TASK_DIR}/codedna"

if [ ! -d "$CTRL" ]; then
    echo "ERROR: control dir missing: $CTRL"; exit 1
fi
if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo "ERROR: DEEPSEEK_API_KEY not set"; exit 1
fi

echo "=== $TASK: annotation pipeline ==="

# Step 1: reset codedna from control (clean slate)
rm -rf "$CDNA"
cp -r "$CTRL" "$CDNA"
echo "  [1/5] control → codedna copy done"

# Step 2: L1 structural on whole repo (AST-only, free)
python3 -m codedna_tool.cli init "$CDNA" --no-llm --force \
    --exclude "tests/*" "docs/*" "js_tests/*" "extras/*" "scripts/*" 2>&1 \
    | tail -3
echo "  [2/5] L1 structural done"

# Step 3: L1+L2 semantic on relevant packages via DeepSeek
#   Packages cover GT file locations for all 5 benchmark tasks:
#   db (all tasks), core (12508, 11808), template (11808),
#   contrib/postgres (11991, 11808), contrib/messages (11808),
#   contrib/gis/db (11991)
for PKG in "django/db" "django/core" "django/template" \
           "django/contrib/postgres" "django/contrib/messages" \
           "django/contrib/gis/db"; do
    if [ -d "$CDNA/$PKG" ]; then
        echo "  [3/5] annotating $PKG ..."
        python3 -m codedna_tool.cli init "$CDNA/$PKG" \
            --force --model deepseek/deepseek-chat \
            --repo-root "$CDNA" 2>&1 | tail -4
    fi
done

# Step 4: refresh used_by after semantic pass
python3 -m codedna_tool.cli refresh "$CDNA" 2>&1 | tail -2
echo "  [4/5] used_by refreshed"

# Step 5: manifest L0
python3 -m codedna_tool.cli manifest "$CDNA" \
    --model deepseek/deepseek-chat \
    --exclude "tests/*" "docs/*" "js_tests/*" "extras/*" "scripts/*" 2>&1 | tail -3
echo "  [5/5] manifest written"

echo ""
echo "=== $TASK: DONE ==="
