#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/env.sh
source "$DIR/scripts/lib/env.sh"
resolve_env "$DIR/.env"

cd "$DIR"
docker compose up -d
docker compose ps
