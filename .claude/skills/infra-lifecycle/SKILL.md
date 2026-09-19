---
name: infra-lifecycle
description: >
  Start, stop, or check the status of the local Docker infra (Redis Stack +
  Postgres/pgvector) this project's RAG concept needs, using
  scripts/start_infra.sh, scripts/stop_infra.sh, and scripts/status_infra.sh.
  Use this skill ANY time the user asks to start, stop, restart, or check
  the status of the infra/infrastructure/docker/containers/database/redis/
  postgres for this project. Triggers on: "start the infra", "stop the
  infra", "infra status", "start docker", "stop docker", "start postgres",
  "start redis", "is the database running", "restart infra", "bring up the
  containers", or any combination of start/stop/status/restart for this
  project's local Docker Compose stack. Always use this skill — never run
  docker compose commands manually without it.
triggers:
  - "start the infra"
  - "stop the infra"
  - "infra status"
  - "start docker"
  - "stop docker"
  - "start postgres"
  - "start redis"
  - "is the database running"
  - "restart infra"
  - "bring up the containers"
  - "start infra"
  - "stop infra"
  - "status infra"
argument-hint: "[start|stop|status|restart]"
---

# Infra Lifecycle Skill — ai_tutorial Docker infra (Redis + Postgres)

Manages the start, stop, and status of the local Docker Compose stack
(Redis Stack + Postgres/pgvector) that this project's RAG concept's
`redis` and `postgres` vector store backends need. The `memory` backend
needs none of this.

## Project paths

All commands run from the repo root (the session's working directory).

| Item              | Path                                              |
|-------------------|----------------------------------------------------|
| Start script      | `scripts/start_infra.sh`                          |
| Stop script       | `scripts/stop_infra.sh`                           |
| Status script     | `scripts/status_infra.sh`                         |
| Docker Compose    | `docker-compose.yml`                              |
| Postgres init     | `docker/postgres/init/001-enable-pgvector.sql`, `docker/postgres/init/002-create-app-user.sh` |
| Redis container   | `ai_tutorial_redis` (image `redis/redis-stack-server`) |
| Postgres container| `ai_tutorial_postgres` (image `pgvector/pgvector:pg16`) |
| Redis port        | `6379`                                            |
| Postgres port     | `5432` (see `.env`'s `POSTGRES_PORT`)             |

## Operations

### Start

```bash
scripts/start_infra.sh
```

- Resolves Postgres secrets via `scripts/lib/env.sh` first. On a fresh
  clone with no `.env.local` yet, this **prompts interactively** for
  `RAG_DEMO_PG_ROOT_PASSWORD` and `RAG_DEMO_PG_APP_PASSWORD` (masked
  input) and caches the answers in gitignored `.env.local` — you're only
  asked once per machine. If running non-interactively (e.g. from an
  automated agent with no TTY), these must already be set as environment
  variables or present in `.env.local` beforehand.
- Runs `docker compose up -d`, then `docker compose ps`.
- On first start against a fresh volume, Postgres's init scripts enable
  the `vector` extension and create a least-privilege `ai_tutorial_app`
  role (the app's actual connection user — never the superuser).

### Stop

```bash
scripts/stop_infra.sh
```

- Runs `docker compose down`. Does **not** need secrets resolved — stopping
  doesn't require valid credential values, just the container names.
- Does not wipe volumes (data persists) unless you separately run
  `docker compose down -v` — that's destructive and NOT what this script
  does; only use `-v` if the user explicitly wants a full reset.

### Status

```bash
scripts/status_infra.sh
```

- Runs `docker compose ps` — shows both containers' health state.

### Restart

No dedicated restart script:

```bash
scripts/stop_infra.sh
scripts/start_infra.sh
```

## Decision rules

| User intent                                    | Actions (in order) |
|--------------------------------------------------|---------------------|
| "start the infra" / "start postgres/redis"      | start               |
| "stop the infra"                                | stop                |
| "infra status" / "is the database running"      | status              |
| "restart infra"                                 | stop → start        |
| "reset the database" / "wipe and start fresh"   | `docker compose down -v` → start (confirm with the user first — destructive) |

Always follow the table — never skip steps. Never run `docker compose down -v` without the user explicitly asking for a data wipe.

## Error handling

| Symptom                                     | Fix                                                                 |
|-----------------------------------------------|------------------------------------------------------------------------|
| Docker not running                          | Start Docker Desktop / Rancher Desktop, then retry.                  |
| `start_infra.sh` hangs                      | It's waiting on an interactive password prompt — either answer it, or pre-populate `.env.local` (see `README.md`'s "Secrets and `.env`"). |
| Container unhealthy                         | `docker compose logs postgres` / `docker compose logs redis`.        |
| Port 5432 or 6379 already in use            | `lsof -i :5432` / `lsof -i :6379` to find the owner, stop it or change `POSTGRES_PORT` in `.env`. |
| Init scripts didn't run / app user missing  | They only run on a **fresh** volume — `docker compose down -v` then `start_infra.sh` to force a clean re-init (destructive, confirm with the user first). |
| App can't connect to Postgres               | Check `.env.local` has `RAG_DEMO_PG_APP_PASSWORD` set and matches what was used when the volume was created. |

## Verifying it's actually up

```bash
docker exec -it ai_tutorial_postgres psql -U ai_tutorial_root -d ai_tutorial_rag -c '\du'
# expect ai_tutorial_root (superuser) and ai_tutorial_app (not)

docker exec -it ai_tutorial_redis redis-cli ping
# expect PONG
```

See `docs/langchain/07-rag/` for backend-specific details and
`docs/TESTING.md` for end-to-end RAG examples once infra is confirmed up.
