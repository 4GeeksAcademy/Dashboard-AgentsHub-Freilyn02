#!/usr/bin/env bash
set -euo pipefail

step=""

on_error() {
  local exit_code=$?
  printf '\n[ERROR] Step failed: %s\n' "$step" >&2
  printf '[ERROR] Exit code: %s\n' "$exit_code" >&2
  exit "$exit_code"
}
trap on_error ERR

printf '[INFO] Starting local validation...\n'

step="clean cache"
printf '[INFO] Cleaning Python cache artifacts...\n'
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

step="lint"
printf '[INFO] Running linter...\n'
if python3 -m ruff --version >/dev/null 2>&1; then
  python3 -m ruff check .
elif python3 -m flake8 --version >/dev/null 2>&1; then
  python3 -m flake8 .
else
  printf '[WARN] No Python linter found (ruff/flake8). Running strict syntax check as fallback.\n'
  python3 -m py_compile server.py smtp_quick_test.py tests/test_resilience.py
fi

step="build"
printf '[INFO] Building project (bytecode compile)...\n'
python3 -m py_compile server.py smtp_quick_test.py tests/test_resilience.py

step="unit tests"
printf '[INFO] Running unit tests...\n'
python3 -m unittest discover -s tests -v

printf '\n[OK] Validation completed successfully.\n'