#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/micro_analyst_full_with_scripts"
pytest -q
