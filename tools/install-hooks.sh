#!/usr/bin/env bash
# Install CodeDNA git hooks
set -euo pipefail
HOOKS_DIR="$(git rev-parse --show-toplevel)/.git/hooks"
cp "$(git rev-parse --show-toplevel)/tools/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"
echo "✅ CodeDNA pre-commit hook installed."
