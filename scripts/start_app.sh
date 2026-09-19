#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/env.sh
source "$DIR/scripts/lib/env.sh"
resolve_env "$DIR/.env"
PORT="${PORT:-18282}"
PID_FILE="$DIR/.uvicorn.pid"
LOG_FILE="$DIR/.uvicorn.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Already running (PID $(cat "$PID_FILE")) on port $PORT"
    exit 0
fi

cd "$DIR"
nohup uv run uvicorn main:app --host 0.0.0.0 --port "$PORT" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Started (PID $(cat "$PID_FILE")) on port $PORT, logs: $LOG_FILE"