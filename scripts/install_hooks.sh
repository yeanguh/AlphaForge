#!/usr/bin/env bash
# Installs the versioned pre-commit hook. Run once after cloning:
#   bash scripts/install_hooks.sh
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
DST="$REPO_ROOT/.git/hooks/pre-commit"
cp scripts/pre_commit_hook.sh "$DST"
chmod +x "$DST"
echo "[install_hooks] pre-commit hook installed -> $DST"
