---
description: Start, stop, restart, or check the status of the local Docker infra (Redis + Postgres/pgvector)
argument-hint: "[start|stop|status|restart] [remove-volume]"
---

Run the infra lifecycle action requested in `$ARGUMENTS` (default to
`status` if empty) for this project's local Docker Compose stack, using the
exact scripts below — never run `docker compose` manually instead.

`$ARGUMENTS` is `<action>` optionally followed by `remove-volume`
(e.g. `stop remove-volume`, `restart remove-volume`) — only `stop` and
`restart` accept it; `start`/`status` ignore it.

- `start` → `scripts/start_infra.sh` (may prompt for Postgres secrets the
  first time on a fresh clone — masked input, cached to gitignored
  `.env.local` so it only asks once)
- `stop` → `scripts/stop_infra.sh` (retains volumes/data by default)
- `stop remove-volume` → `scripts/stop_infra.sh --remove-volume`
  (**destructive** — wipes the `redis_data`/`postgres_data` volumes;
  confirm with the user before running this)
- `status` → `scripts/status_infra.sh`
- `restart` → `scripts/stop_infra.sh` then `scripts/start_infra.sh`
  (volumes retained)
- `restart remove-volume` → `scripts/stop_infra.sh --remove-volume` then
  `scripts/start_infra.sh` (**destructive** — confirm with the user
  before running this; the following `start_infra.sh` re-runs Postgres's
  init scripts against the now-fresh volume)

If `$ARGUMENTS` doesn't match one of these, ask which action was meant.
Never run raw `docker compose down -v` — use `stop_infra.sh --remove-volume`
(via `remove-volume`) instead, and only when the user explicitly asks for
a full data reset.

For full details (project paths, error handling, how to verify the
containers actually came up healthy), follow the `infra-lifecycle` skill.
