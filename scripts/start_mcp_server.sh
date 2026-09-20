#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/env.sh
source "$DIR/scripts/lib/env.sh"
resolve_env "$DIR/.env"
MCP_SERVER_PORT="${MCP_SERVER_PORT:-18383}"
PID_FILE="$DIR/.mcp_server.pid"
LOG_FILE="$DIR/.mcp_server.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Already running (PID $(cat "$PID_FILE")) on port $MCP_SERVER_PORT"
    exit 0
fi

cd "$DIR"
nohup uv run python run_mcp_server.py > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Started (PID $(cat "$PID_FILE")) on port $MCP_SERVER_PORT, logs: $LOG_FILE"
