#!/usr/bin/env bash
# CodeDNA Stop hook — reminds agent to update .codedna session log.
set -euo pipefail

CHANGED=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb|cs|php)$' || true)
STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '\.(py|ts|go|rs|java|kt|swift|rb|cs|php)$' || true)

if [[ -n "$CHANGED" ]] || [[ -n "$STAGED" ]]; then
  echo ""
  echo "[CodeDNA] Source files modified. Remember to:"
  echo "  1. Append agent_sessions: entry to .codedna"
  echo "  2. Use git trailers: AI-Agent, AI-Provider, AI-Session, AI-Visited, AI-Message"
fi

exit 0
