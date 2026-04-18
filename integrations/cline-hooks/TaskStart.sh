#!/usr/bin/env bash
# CodeDNA v0.9 — Cline TaskStart hook
# Place in: .clinerules/hooks/TaskStart.sh (make executable)
# Requires: Cline v3.36+
#
# Fires when a new task begins. Reads .codedna and injects
# project context (name, module count) into the session.

set -euo pipefail

CODEDNA=".codedna"

if [[ -f "$CODEDNA" ]]; then
    PKGS=$(grep -c 'purpose:' "$CODEDNA" 2>/dev/null || echo "0")
    PROJ=$(grep '^project:' "$CODEDNA" | head -1 | cut -d' ' -f2- | tr -d '"')
    MSG="[CodeDNA] Project: $PROJ — $PKGS documented modules. Read .codedna and the module docstring before editing any source file. Every edit requires updating agent: with today's date."
    echo "{\"output\": \"$MSG\"}"
fi

exit 0
