#!/usr/bin/env bash

# ============================================================
# Micro Analyst – Development Launcher
# ============================================================

set -euo pipefail

BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

echo -e "${BLUE}=== Micro Analyst Dev Launcher ===${RESET}"

# --------------------------
# Move to project directory
# --------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
cd "${PROJECT_ROOT}"

echo -e "${GREEN}Project root:${RESET} ${PROJECT_ROOT}"

# --------------------------
# Auto-load .env if present
# --------------------------
if [[ -f ".env" ]]; then
  echo -e "${BLUE}Loading .env environment variables...${RESET}"
  # Export all vars automatically
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo -e "${YELLOW}No .env file found — running with default environment.${RESET}"
fi

# --------------------------
# Setup virtual environment
# --------------------------
if [[ ! -d ".venv" ]]; then
  echo -e "${BLUE}Creating virtual environment...${RESET}"
  python3 -m venv .venv
fi

echo -e "${BLUE}Activating virtual environment...${RESET}"
# shellcheck disable=SC1091
source .venv/bin/activate

echo -e "${BLUE}Installing dependencies...${RESET}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# --------------------------
# Start MCP services (one per terminal)
# --------------------------

echo -e "${BLUE}Starting MCP microservices...${RESET}"
echo -e "${YELLOW}Each MCP will run in its own background process.${RESET}"

# Kill old processes if they exist
pkill -f "python.*mcp_" 2>/dev/null || true

# MCP definitions: [script] [port]
declare -a SERVICES=(
  "mcp_web_scrape:8001"
  "mcp_seo_probe:8002"
  "mcp_tech_stack:8003"
  "mcp_reviews_snapshot:8004"
  "mcp_social_snapshot:8005"
  "mcp_careers_intel:8006"
  "mcp_ads_snapshot:8007"
)

for entry in "${SERVICES[@]}"; do
  svc="${entry%%:*}"
  port="${entry##*:}"
  echo -e "${GREEN}Launching ${svc} on port ${port}${RESET}"
  nohup python -u "mcp_services/${svc}.py" --port "${port}" > "logs_${svc}.txt" 2>&1 &
done

sleep 1

# --------------------------
# Start main agent
# --------------------------
echo -e "${BLUE}Starting Micro Analyst Agent...${RESET}"
AGENT_PORT="${MICRO_ANALYST_PORT:-8000}"

# Kill old agent if running
pkill -f "uvicorn.*micro_analyst" 2>/dev/null || true

nohup uvicorn agent.micro_analyst:app --port "${AGENT_PORT}" --reload > agent_logs.txt 2>&1 &

echo -e "${GREEN}All services launched successfully!${RESET}"
echo -e ""
echo -e "${BLUE}MCP Cluster:${RESET}"
echo -e "${GREEN}- Web Scrape:        http://localhost:8001/run${RESET}"
echo -e "${GREEN}- SEO Probe:         http://localhost:8002/run${RESET}"
echo -e "${GREEN}- Tech Stack:        http://localhost:8003/run${RESET}"
echo -e "${GREEN}- Reviews Snapshot:  http://localhost:8004/run${RESET}"
echo -e "${GREEN}- Social Snapshot:   http://localhost:8005/run${RESET}"
echo -e "${GREEN}- Careers Intel:     http://localhost:8006/run${RESET}"
echo -e "${GREEN}- Ads Snapshot:      http://localhost:8007/run${RESET}"
echo -e ""
echo -e "${BLUE}Agent:${RESET} ${GREEN}http://localhost:${AGENT_PORT}/analyze${RESET}"
echo -e ""
echo -e "${BLUE}To tail logs:${RESET}"
echo -e "  tail -f agent_logs.txt"
echo -e "  tail -f logs_mcp_web_scrape.txt"
echo -e "  ... etc."
echo -e ""
echo -e "${GREEN}Done. Your local environment is live.${RESET}"
