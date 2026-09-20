#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$DIR/.env" ] && set -a && source "$DIR/.env" && set +a
MCP_SERVER_PORT="${MCP_SERVER_PORT:-18383}"
PID_FILE="$DIR/.mcp_server.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Running (PID $(cat "$PID_FILE")) on port $MCP_SERVER_PORT"
else
    echo "Not running"
fi
