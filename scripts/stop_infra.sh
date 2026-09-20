#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

if [ "${1:-}" = "--remove-volume" ]; then
    echo "Removing volumes (docker compose down -v) — data will NOT persist."
    docker compose down -v
else
    docker compose down
fi
