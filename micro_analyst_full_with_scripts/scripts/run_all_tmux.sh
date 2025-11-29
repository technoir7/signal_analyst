#!/usr/bin/env bash

# ===========================================
# Launch all MCP services + Micro-Analyst agent in tmux
# ===========================================

SESSION="micro_analyst"

# Kill existing session if already running
tmux kill-session -t $SESSION 2>/dev/null

# Create a new detached session
tmux new-session -d -s $SESSION -n services

# Helper: open a new pane and run the given command
start_service () {
  tmux split-window -t $SESSION:0 "$1"
  tmux select-layout -t $SESSION:0 tiled >/dev/null
}

# Launch MCP services
start_service "uvicorn mcp_web_scrape.server:app --port 8001 --reload"
start_service "uvicorn mcp_seo_probe.server:app --port 8002 --reload"
start_service "uvicorn mcp_tech_stack.server:app --port 8003 --reload"
start_service "uvicorn mcp_reviews_snapshot.server:app --port 8004 --reload"
start_service "uvicorn mcp_social_snapshot.server:app --port 8005 --reload"
start_service "uvicorn mcp_careers_intel.server:app --port 8006 --reload"

# Launch the Micro-Analyst Agent
start_service "uvicorn agent.micro_analyst:app --port 8000 --reload"

# Attach to tmux session
tmux attach -t $SESSION
