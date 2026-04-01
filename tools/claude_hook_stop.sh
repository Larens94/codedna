#!/usr/bin/env bash
# claude_hook_stop.sh — Claude Code Stop hook for CodeDNA v0.8 session end protocol.
#
# Reminds the agent to update .codedna with a session entry
# if any source files were modified during the session.

set -euo pipefail

# Check if there are uncommitted changes to source files
CHANGED=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb)$' || true)
STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb)$' || true)

if [[ -n "$CHANGED" ]] || [[ -n "$STAGED" ]]; then
    echo ""
    echo "━━━ CodeDNA v0.8 — session end protocol ━━━"
    echo "Source files were modified. Remember to:"
    echo "  1. Append an agent_sessions: entry to .codedna"
    echo "  2. Include: agent, provider, date, session_id, task, changed, visited, message"
    echo "  3. Use git trailers in commit: AI-Agent, AI-Provider, AI-Session, AI-Visited, AI-Message"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

exit 0
