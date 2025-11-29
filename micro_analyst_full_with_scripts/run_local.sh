#!/usr/bin/env bash
set -euo pipefail

# Activate venv
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# Install deps (no-op if already installed)
pip install -r requirements.txt

# Start MCPs + agent in the background
uvicorn mcp_web_scrape.server:app --port 8001 &
uvicorn mcp_seo_probe.server:app --port 8002 &
uvicorn mcp_tech_stack.server:app --port 8003 &
uvicorn mcp_reviews_snapshot.server:app --port 8004 &
uvicorn mcp_social_snapshot.server:app --port 8005 &
uvicorn mcp_careers_intel.server:app --port 8006 &
uvicorn agent.micro_analyst:app --port 8000 --reload &
wait
