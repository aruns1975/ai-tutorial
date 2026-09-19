---
description: Start, stop, restart, or check the status of the ai_tutorial FastAPI app
argument-hint: "[start|stop|status|restart]"
---

Run the app lifecycle action requested in `$ARGUMENTS` (default to `status`
if empty) for this project's FastAPI app, using the exact scripts below —
never run `uvicorn`/`kill` manually instead.

- `start` → `scripts/start_app.sh`
- `stop` → `scripts/stop_app.sh`
- `status` → `scripts/status_app.sh`
- `restart` → `scripts/stop_app.sh` then `scripts/start_app.sh`

If `$ARGUMENTS` doesn't match one of these, ask which action was meant.

For full details (PID/log file locations, error handling, how to verify the
app actually came up), follow the `app-lifecycle` skill.
