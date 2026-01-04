#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------
# Micro Analyst — Multi-Service Bootstrapper
# --------------------------------------------

# Colors
GREEN="\033[0;32m"
BLUE="\033[1;34m"
NC="\033[0m" # No color

echo -e "${BLUE}▶ Starting Micro Analyst full stack...${NC}"

# --------------------------------------------
# Activate or create virtual environment
# --------------------------------------------
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}▶ Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

echo -e "${BLUE}▶ Installing dependencies (if needed)...${NC}"
pip install -q -r requirements.txt

# --------------------------------------------
# Start MCP microservices + Agent
# --------------------------------------------
start_service() {
    local name=$1
    local module=$2
    local port=$3

    echo -e "${GREEN}▶ Launching $name on port $port...${NC}"
    uvicorn "$module":app --port "$port" --host 127.0.0.1 &
    echo $! > "pid_$name"
}

# Start all MCPs
start_service "web_scrape"          "mcp_web_scrape.server"          8001
start_service "seo_probe"           "mcp_seo_probe.server"           8002
start_service "tech_stack"          "mcp_tech_stack.server"          8003
start_service "reviews_snapshot"    "mcp_reviews_snapshot.server"    8004
start_service "social_snapshot"     "mcp_social_snapshot.server"     8005
start_service "careers_intel"       "mcp_careers_intel.server"       8006

# Start main agent
start_service "agent"               "agent.micro_analyst"            8000

echo -e "${GREEN}✔ All services launched.${NC}"
echo -e "${BLUE}▶ Micro Analyst is now running at:${NC} ${GREEN}http://localhost:8000/analyze${NC}"
echo -e "${BLUE}▶ To stop: press Ctrl-C${NC}"

# --------------------------------------------
# Graceful shutdown on Ctrl-C
# --------------------------------------------
trap 'echo -e "\n${BLUE}▶ Shutting down all services...${NC}"; pkill -P $$; rm -f pid_*; exit 0' INT

# Keep script alive so trap works
while true; do sleep 1; done
