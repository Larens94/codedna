#!/usr/bin/env bash
# CodeDNA SessionStart hook — reads .codedna, detects mode, reminds agent.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"

# No .codedna — first time setup needed
if [[ ! -f "$REPO_ROOT/.codedna" ]]; then
  echo "[CodeDNA] No .codedna found. Run /codedna:init to set up this project."
  echo "  Ask the user which mode they prefer:"
  echo "    - human:  annotations are minimal, semantic naming off, for human-written code"
  echo "    - semi:   annotations on new code, semantic naming on new variables, for human+AI workflows (recommended)"
  echo "    - agent:  full annotations everywhere, semantic naming enforced, for AI-first codebases"
  exit 0
fi

# Read mode
MODE=$(grep '^mode:' "$REPO_ROOT/.codedna" 2>/dev/null | head -1 | awk '{print $2}' || echo "")

# Mode not configured — ask user
if [[ -z "$MODE" ]]; then
  PKGS=$(grep -c "purpose:" "$REPO_ROOT/.codedna" 2>/dev/null || echo "0")
  echo "[CodeDNA] Project: $(basename "$REPO_ROOT") — $PKGS documented modules."
  echo "[CodeDNA] Mode not configured. Ask the user which mode they want:"
  echo "    - human:  L1 headers only, no semantic naming, Rules: on critical functions only"
  echo "    - semi:   L1+L2 on new code, semantic naming on new variables (recommended)"
  echo "    - agent:  full protocol everywhere, rename variables, all functions get Rules:"
  echo "  Then add 'mode: <choice>' to .codedna"
  exit 0
fi

# Mode configured — give context
HINTS="[CodeDNA] Project: $(basename "$REPO_ROOT") — mode: $MODE."

case "$MODE" in
  human)
    HINTS="$HINTS Human mode: L1 headers required, L2 Rules: on critical functions only, no semantic naming."
    ;;
  semi)
    HINTS="$HINTS Semi mode: L1+L2 on all new/edited code, semantic naming on new variables, inline Rules: on complex logic."
    ;;
  agent)
    HINTS="$HINTS Agent mode: full protocol — L1+L2 everywhere, semantic naming enforced, rename variables when touching a function, inline Rules: on all non-trivial logic."
    ;;
esac

HINTS="$HINTS Read .codedna and module docstrings before editing."
echo "$HINTS"

exit 0
