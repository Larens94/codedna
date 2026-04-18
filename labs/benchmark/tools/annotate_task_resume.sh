#!/usr/bin/env bash
# annotate_task_resume.sh — Add L1+L2 semantic to packages where L2=0 on an
# already-initialized codedna/. Does NOT reset control/→codedna/ — meant to be
# run AFTER annotate_task.sh to complete packages that silently failed
# (e.g. DeepSeek rate-limit → try/except swallowed → 0 LLM calls).
#
# Usage:  ./annotate_task_resume.sh <task_id> [pkg1 pkg2 ...]
# Default packages: core, template, contrib/postgres, contrib/messages, contrib/gis/db
# (i.e. everything except django/db which is usually already done).
set -e

TASK_ID="${1:?usage: $0 <bare_task_id> [pkg_paths...]}"
shift
TASK="django__django-${TASK_ID}"
CDNA="labs/benchmark/projects/${TASK}/codedna"

if [ ! -d "$CDNA" ]; then
    echo "ERROR: codedna dir missing: $CDNA (run annotate_task.sh first)"; exit 1
fi
if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo "ERROR: DEEPSEEK_API_KEY not set"; exit 1
fi

# Default package list (skip django/db which is usually already semantic)
if [ $# -eq 0 ]; then
    set -- "django/core" "django/template" "django/contrib/postgres" \
           "django/contrib/messages" "django/contrib/gis/db"
fi

echo "=== $TASK: RESUME annotation ==="
echo "  codedna dir: $CDNA"
echo "  packages:    $*"
echo ""

for PKG in "$@"; do
    if [ -d "$CDNA/$PKG" ]; then
        # Count current semantic state to decide whether to skip
        total=$(find "$CDNA/$PKG" -name "*.py" ! -path "*/migrations/*" | wc -l | tr -d ' ')
        sem=$(find "$CDNA/$PKG" -name "*.py" ! -path "*/migrations/*" \
              -exec grep -l "^exports:" {} + 2>/dev/null | \
              xargs grep -L "^rules:   none" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$total" -eq "0" ]; then
            echo "  [skip] $PKG (no .py files)"
            continue
        fi
        if [ "$sem" -ge "$total" ]; then
            echo "  [skip] $PKG (already $sem/$total semantic)"
            continue
        fi
        echo "  [init] $PKG ($sem/$total semantic → re-run)"
        python3 -m codedna_tool.cli init "$CDNA/$PKG" \
            --force --model deepseek/deepseek-chat \
            --repo-root "$CDNA" 2>&1 | tail -4
        # Brief pause between packages to avoid rate-limit bursts
        sleep 5
    else
        echo "  [skip] $PKG (directory missing)"
    fi
done

# Refresh used_by to pick up new annotations
python3 -m codedna_tool.cli refresh "$CDNA" 2>&1 | tail -1

echo ""
echo "=== $TASK: RESUME DONE ==="
