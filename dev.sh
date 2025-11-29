#!/usr/bin/env bash
# dev.sh — required by meta tests.

set -e

if [ "$DEV_SH_DRY_RUN" = "1" ]; then
  echo "dev.sh dry run OK"
  exit 0
fi

cd "$(dirname "$0")/micro_analyst_full_with_scripts"
uvicorn agent.micro_analyst:app --reload --port 8000
