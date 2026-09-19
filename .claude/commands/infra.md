---
description: Start, stop, restart, or check the status of the local Docker infra (Redis + Postgres/pgvector)
argument-hint: "[start|stop|status|restart]"
---

Run the infra lifecycle action requested in `$ARGUMENTS` (default to
`status` if empty) for this project's local Docker Compose stack, using the
exact scripts below — never run `docker compose` manually instead.

- `start` → `scripts/start_infra.sh` (may prompt for Postgres secrets the
  first time on a fresh clone — masked input, cached to gitignored
  `.env.local` so it only asks once)
- `stop` → `scripts/stop_infra.sh` (does **not** wipe data)
- `status` → `scripts/status_infra.sh`
- `restart` → `scripts/stop_infra.sh` then `scripts/start_infra.sh`

If `$ARGUMENTS` doesn't match one of these, ask which action was meant.
Never run `docker compose down -v` (wipes volumes) unless the user
explicitly asks for a full data reset.

For full details (project paths, error handling, how to verify the
containers actually came up healthy), follow the `infra-lifecycle` skill.
