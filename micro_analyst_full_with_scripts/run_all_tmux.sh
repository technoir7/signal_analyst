#!/bin/bash

set -e

SESSION_NAME="micro-analyst"

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# --- Colors -------------------------------------------------------------------
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
MAGENTA="\033[35m"
CYAN="\033[36m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}=== Micro Analyst: tmux service launcher ===${RESET}"
echo "Project root: $PROJECT_ROOT"

# --- 0. Ensure tmux is available ----------------------------------------------
if ! command -v tmux >/dev/null 2>&1; then
    echo -e "${RED}tmux is not installed or not on PATH.${RESET}" >&2
    echo "Install tmux (e.g. 'brew install tmux' or 'sudo apt install tmux') and re-run." >&2
    exit 1
fi

# --- 1. Deactivate conda if active --------------------------------------------
if command -v conda &> /dev/null; then
    conda deactivate 2>/dev/null || true
    conda deactivate 2>/dev/null || true
fi

# --- 2. Ensure venv exists ----------------------------------------------------
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}[*] Creating Python venv in .venv ...${RESET}"
    python3 -m venv .venv
else
    echo -e "${GREEN}[*] Using existing .venv${RESET}"
fi

# --- 3. Install requirements once outside tmux --------------------------------
echo -e "${BLUE}[*] Activating venv to install requirements...${RESET}"
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
deactivate

# --- 4. Refuse to overwrite existing tmux session -----------------------------
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo -e "${RED}⚠️  tmux session '${SESSION_NAME}' already exists.${RESET}"
    echo "Attach to it with:"
    echo -e "  ${BOLD}tmux attach -t ${SESSION_NAME}${RESET}"
    echo "Or kill it first:"
    echo -e "  ${BOLD}tmux kill-session -t ${SESSION_NAME}${RESET}"
    exit 1
fi

echo -e "${BLUE}[*] Creating tmux session: ${SESSION_NAME}${RESET}"

# Helper to DRY up tmux window creation
start_service () {
    local WIN_NAME="$1"
    local CMD="$2"

    tmux new-window -t "$SESSION_NAME" -n "$WIN_NAME" \
        "cd \"$PROJECT_ROOT\"; source .venv/bin/activate; echo \"[tmux:${WIN_NAME}] running: $CMD\"; $CMD"
}

# --- 5. Create initial session with agent -------------------------------------
tmux new-session -d -s "$SESSION_NAME" -n "agent" \
    "cd \"$PROJECT_ROOT\"; source .venv/bin/activate; echo '[tmux:agent] running micro_analyst on :8000'; uvicorn agent.micro_analyst:app --reload --port 8000 --host 127.0.0.1"

# --- 6. MCP services in their own windows -------------------------------------
start_service "web_scrape"   "uvicorn mcp_web_scrape.server:app --reload --port 8001 --host 127.0.0.1"
start_service "seo_probe"    "uvicorn mcp_seo_probe.server:app --reload --port 8002 --host 127.0.0.1"
start_service "tech_stack"   "uvicorn mcp_tech_stack.server:app --reload --port 8003 --host 127.0.0.1"
start_service "reviews"      "uvicorn mcp_reviews_snapshot.server:app --reload --port 8004 --host 127.0.0.1"
start_service "social"       "uvicorn mcp_social_snapshot.server:app --reload --port 8005 --host 127.0.0.1"
start_service "careers"      "uvicorn mcp_careers_intel.server:app --reload --port 8006 --host 127.0.0.1"

# Kill the default extra window tmux sometimes creates
tmux kill-window -t "$SESSION_NAME:0" 2>/dev/null || true

echo
echo -e "${GREEN}=== All services started in tmux session '${SESSION_NAME}' ===${RESET}"
echo "Attach with:"
echo -e "  ${BOLD}tmux attach -t ${SESSION_NAME}${RESET}"
echo
echo "Inside tmux:"
echo "  - Switch windows:  Ctrl-b then number (0–7)"
echo "  - Detach:          Ctrl-b then d"
echo
echo "To kill the whole cluster:"
echo -e "  ${BOLD}tmux kill-session -t ${SESSION_NAME}${RESET}"
