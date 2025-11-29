#!/bin/bash

set -e

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
MAGENTA="\033[35m"
CYAN="\033[36m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}=== Micro Analyst: Dev Menu ===${RESET}"
echo "Project root: $PROJECT_ROOT"
echo

ensure_venv() {
    if command -v conda &> /dev/null; then
        conda deactivate 2>/dev/null || true
        conda deactivate 2>/dev/null || true
    fi

    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating Python venv in .venv ...${RESET}"
        python3 -m venv .venv
    else
        echo -e "${GREEN}.venv already exists.${RESET}"
    fi

    # shellcheck disable=SC1091
    source .venv/bin/activate
}

while true; do
    echo
    echo -e "${BOLD}Choose an option:${RESET}"
    echo "  1) Setup venv + install requirements"
    echo "  2) Run tests"
    echo "  3) Run single-agent dev server (uvicorn on :8000)"
    echo "  4) Start full tmux cluster (all MCPs + agent)"
    echo "  5) Attach to tmux session (micro-analyst)"
    echo "  6) Kill tmux session (micro-analyst)"
    echo "  7) Exit"
    echo
    read -rp "Selection: " choice

    case "$choice" in
        1)
            ensure_venv
            echo -e "${BLUE}Installing requirements...${RESET}"
            pip install --upgrade pip
            pip install -r requirements.txt
            echo -e "${GREEN}Done.${RESET}"
            ;;
        2)
            ensure_venv
            echo -e "${BLUE}Running tests...${RESET}"
            if pytest -v; then
                echo -e "${GREEN}✅ Tests passed.${RESET}"
            else
                echo -e "${RED}⚠️ Tests failed.${RESET}"
            fi
            ;;
        3)
            ensure_venv
            echo -e "${CYAN}Starting micro_analyst on http://127.0.0.1:8000 ...${RESET}"
            uvicorn agent.micro_analyst:app --reload --port 8000
            ;;
        4)
            echo -e "${CYAN}Launching full tmux cluster...${RESET}"
            ./run_all_tmux.sh
            ;;
        5)
            echo -e "${BLUE}Attaching to tmux session 'micro-analyst'...${RESET}"
            tmux attach -t micro-analyst || echo -e "${RED}No such session. Did you run ./run_all_tmux.sh?${RESET}"
            ;;
        6)
            echo -e "${YELLOW}Killing tmux session 'micro-analyst'...${RESET}"
            tmux kill-session -t micro-analyst 2>/dev/null && \
                echo -e "${GREEN}Session killed.${RESET}" || \
                echo -e "${RED}No such session.${RESET}"
            ;;
        7)
            echo -e "${GREEN}Goodbye.${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice.${RESET}"
            ;;
    esac
done
