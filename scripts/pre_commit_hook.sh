#!/usr/bin/env bash
# research-os pre-commit hook -- error-as-guidance gate.
# Runs offline harness + unit tests before every commit; prints problem/why/fix on failure.
# Emergency bypass: git commit --no-verify
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="python3"; fi
HLOG="$(mktemp)"; PLOG="$(mktemp)"
fail() {
  echo ""
  echo "========================================================================"
  echo "  PRE-COMMIT BLOCKED: $1"
  echo "------------------------------------------------------------------------"
  echo "  WHY:  $2"
  echo "  FIX:  $3"
  echo "------------------------------------------------------------------------"
  echo "  (emergency bypass: git commit --no-verify -- use sparingly)"
  echo "========================================================================"
  exit 1
}
echo "[pre-commit] running offline harness ..."
if ! "$PY" scripts/run_harness.py >"$HLOG" 2>&1; then
  tail -n 30 "$HLOG"
  fail "harness checks did not pass" "loop_os/harness/checks.py found a violation" "fix the failing check, then rerun: $PY scripts/run_harness.py"
fi
echo "[pre-commit] running unit tests ..."
if ! "$PY" -m pytest -q >"$PLOG" 2>&1; then
  tail -n 30 "$PLOG"
  fail "unit tests failed" "a change broke a contract in tests/*.py" "reproduce: $PY -m pytest -q"
fi
echo "[pre-commit] OK -- harness green, tests green."
exit 0
