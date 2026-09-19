---
name: app-lifecycle
description: >
  Start, stop, or check the status of the ai_tutorial FastAPI application
  using scripts/start_app.sh, scripts/stop_app.sh, and scripts/status_app.sh.
  Use this skill ANY time the user asks to start, stop, restart, or check
  the status of the app/application/server for this project. Triggers on:
  "start the app", "stop the app", "app status", "is the app running",
  "restart the app", "start the server", "stop the server", "restart the
  server", or any combination of start/stop/status/restart for this
  FastAPI application. Always use this skill — never run
  uvicorn/start/stop commands manually without it.
triggers:
  - "start the app"
  - "stop the app"
  - "app status"
  - "is the app running"
  - "restart the app"
  - "start the server"
  - "stop the server"
  - "restart the server"
  - "start app"
  - "stop app"
  - "status app"
argument-hint: "[start|stop|status|restart]"
---

# App Lifecycle Skill — ai_tutorial FastAPI app

Manages the start, stop, and status of this project's FastAPI application
(the LangChain concepts demo) using the project's shell scripts.

## Project paths

All commands run from the repo root (the session's working directory).

| Item          | Path                        |
|---------------|-----------------------------|
| Start script  | `scripts/start_app.sh`      |
| Stop script   | `scripts/stop_app.sh`       |
| Status script | `scripts/status_app.sh`     |
| PID file      | `.uvicorn.pid`               |
| Log file      | `.uvicorn.log`               |
| Default port  | `18282` (see `.env`'s `PORT`) |
| Root endpoint | `http://localhost:18282/`   |

## Operations

### Start

```bash
scripts/start_app.sh
```

- Resolves any missing Postgres secrets via `scripts/lib/env.sh` first (may
  prompt interactively the first time on a fresh clone — see the
  `infra-lifecycle` skill and the project `README.md`'s "Secrets and
  `.env`" section for what this means).
- Guards against double-start: exits cleanly with "Already running" if the
  PID file points at a live process.
- Runs `uv run uvicorn main:app --host 0.0.0.0 --port "$PORT"` in the
  background (`nohup ... &`), writes the PID to `.uvicorn.pid`, and
  streams logs to `.uvicorn.log`.

### Stop

```bash
scripts/stop_app.sh
```

- No-ops safely ("Not running") if the app isn't running or the PID is stale.
- Sends a plain `kill` to the PID and removes `.uvicorn.pid`.

### Status

```bash
scripts/status_app.sh
```

- Reports "Running (PID ...) on port ..." or "Not running".

### Restart

No dedicated restart script:

```bash
scripts/stop_app.sh
scripts/start_app.sh
```

## Decision rules

| User intent                          | Actions (in order) |
|---------------------------------------|---------------------|
| "start the app" / "start the server"  | start               |
| "stop the app" / "stop the server"    | stop                |
| "app status" / "is it running"        | status              |
| "restart the app"                     | stop → start        |

Always follow the table — never skip steps.

## Error handling

| Symptom                                   | Fix                                                                 |
|--------------------------------------------|----------------------------------------------------------------------|
| Start hangs waiting for input             | The app needs Postgres secrets resolved — see the `infra-lifecycle` skill; run `scripts/start_infra.sh` first, or answer the prompt. |
| Port already in use                       | `scripts/status_app.sh` to check for a stale PID; `scripts/stop_app.sh` then retry. |
| App starts but RAG's redis/postgres calls fail | Infra isn't up — see the `infra-lifecycle` skill (`scripts/start_infra.sh`). |
| Need to see why it crashed                | `tail -50 .uvicorn.log`                                             |

## Verifying it's actually up

```bash
curl -s http://localhost:18282/
# expect {"message":"Hello World"}
```

See `docs/TESTING.md` for a full walkthrough of every endpoint once the
app is confirmed running.
