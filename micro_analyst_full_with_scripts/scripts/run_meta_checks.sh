#!/usr/bin/env bash
set -euo pipefail

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

python3 scripts/run_meta_checks.py
