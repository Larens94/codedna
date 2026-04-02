#!/usr/bin/env bash
# CodeDNA v0.8 — Cursor stop hook
# Place in: .cursor/hooks/stop.sh (make executable)
# Requires: Cursor v1.7+
#
# Fires when the agent finishes. Reminds to update .codedna.

set -euo pipefail

CHANGED=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb)$' || true)
STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb)$' || true)

if [[ -n "$CHANGED" ]] || [[ -n "$STAGED" ]]; then
    echo ""
    echo "━━━ CodeDNA v0.8 — session end protocol ━━━"
    echo "Source files were modified. Remember to:"
    echo "  1. Append an agent_sessions: entry to .codedna"
    echo "  2. Commit with AI git trailers: AI-Agent, AI-Provider, AI-Session, AI-Visited, AI-Message"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

exit 0
