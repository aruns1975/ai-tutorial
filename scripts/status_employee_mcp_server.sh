#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$DIR/.env" ] && set -a && source "$DIR/.env" && set +a
EMPLOYEE_MCP_SERVER_PORT="${EMPLOYEE_MCP_SERVER_PORT:-18384}"
PID_FILE="$DIR/.employee_mcp_server.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Running (PID $(cat "$PID_FILE")) on port $EMPLOYEE_MCP_SERVER_PORT"
else
    echo "Not running"
fi