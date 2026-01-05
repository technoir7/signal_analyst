#!/usr/bin/env bash
# run_dev.sh — Single-command dev runner for Signal Analyst

set -e

# --- Configuration ---
BACKEND_PORT=8000
FRONTEND_PORT=8080
FRONTEND_DIR="micro_analyst_full_with_scripts/miniapp"
BACKEND_ROOT="micro_analyst_full_with_scripts"

# --- Pre-flight Checks ---
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required but not installed." >&2; exit 1; }
command -v uvicorn >/dev/null 2>&1 || { echo "Error: uvicorn is required but not installed (pip install uvicorn)." >&2; exit 1; }

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "Error: Frontend directory '$FRONTEND_DIR' not found." >&2
    exit 1
fi

# --- Execution ---
echo "🚀 Starting Signal Analyst Dev Stack..."
echo "   (Logs: output.log)"

# Function to start a service
start_service() {
    local name=$1
    local cmd=$2
    local port=$3
    echo "   • Starting $name (:$port)..."
    (
        cd "$BACKEND_ROOT"
        exec $cmd >/dev/null 2>&1
    ) &
    PIDS+=($!)
}

PIDS=()

# Start MCPs (Microservices)
# Note: mcp_ads_snapshot skipped (not found in directory list)
start_service "MCP:WebScrape"    "uvicorn mcp_web_scrape.server:app --port 8001" 8001
start_service "MCP:SEO"          "uvicorn mcp_seo_probe.server:app --port 8002" 8002
start_service "MCP:TechStack"    "uvicorn mcp_tech_stack.server:app --port 8003" 8003
start_service "MCP:Reviews"      "uvicorn mcp_reviews_snapshot.server:app --port 8004" 8004
start_service "MCP:Social"       "uvicorn mcp_social_snapshot.server:app --port 8005" 8005
start_service "MCP:Careers"      "uvicorn mcp_careers_intel.server:app --port 8006" 8006

# Start Backend
echo "   • Starting Backend (:$BACKEND_PORT)..."
(
  cd "$BACKEND_ROOT"
  export ENABLE_WAYBACK=1
  exec uvicorn agent.micro_analyst:app --reload --port $BACKEND_PORT
) &
BACKEND_PID=$!
PIDS+=($BACKEND_PID)

# Start Frontend
echo "   • Starting Frontend (:$FRONTEND_PORT)..."
(
  cd "$FRONTEND_DIR"
  exec python3 -m http.server $FRONTEND_PORT >/dev/null 2>&1
) &
FRONTEND_PID=$!
PIDS+=($FRONTEND_PID)

# --- Cleanup Logic ---
cleanup() {
    echo ""
    echo "🛑 Shutting down stack (${#PIDS[@]} processes)..."
    for pid in "${PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
}

trap cleanup SIGINT SIGTERM

echo ""
echo "✅ Full Stack is up!"
echo "   • Backend:  http://localhost:$BACKEND_PORT"
echo "   • Frontend: http://localhost:$FRONTEND_PORT"
echo "   • MCPs:     Ports 8000-8006 active"
echo ""
echo "Press Ctrl+C to exit."

# Wait for Backend (if it dies, we exit)
wait $BACKEND_PID
