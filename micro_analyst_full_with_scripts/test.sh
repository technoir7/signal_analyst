#!/usr/bin/env bash
set -euo pipefail

BLUE="\033[34m"
GREEN="\033[32m"
RESET="\033[0m"

echo -e "${BLUE}=== Running Micro Analyst Tests ===${RESET}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

# -----------------------------
# Auto-load .env if present
# -----------------------------
if [[ -f ".env" ]]; then
  echo -e "${BLUE}Loading .env...${RESET}"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# -----------------------------
# Ensure venv
# -----------------------------
if [[ ! -d ".venv" ]]; then
  echo -e "${BLUE}Creating virtual environment...${RESET}"
  python3 -m venv .venv
fi

echo -e "${BLUE}Activating environment...${RESET}"
# shellcheck disable=SC1091
source .venv/bin/activate

echo -e "${BLUE}Installing requirements...${RESET}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# -----------------------------
# Run test suite
# -----------------------------
echo -e "${BLUE}Running pytest...${RESET}"
pytest tests

echo -e "${GREEN}All tests finished.${RESET}"
