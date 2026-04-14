#!/usr/bin/env bash
# CodeDNA SessionStart hook — reminds agent to read .codedna and CLAUDE.md.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"

HINTS=""

if [[ -f "$REPO_ROOT/.codedna" ]]; then
  # Count packages and sessions
  PKGS=$(grep -c "purpose:" "$REPO_ROOT/.codedna" 2>/dev/null || echo "0")
  SESSIONS=$(grep -c "^  - agent:" "$REPO_ROOT/.codedna" 2>/dev/null || echo "0")
  HINTS="[CodeDNA] Project: $(basename "$REPO_ROOT") — $PKGS documented modules."
  HINTS="$HINTS Read .codedna and CLAUDE.md before editing Python files."
  HINTS="$HINTS Every .py edit requires updating agent: with today's date."
fi

if [[ -n "$HINTS" ]]; then
  echo "$HINTS"
fi

exit 0
