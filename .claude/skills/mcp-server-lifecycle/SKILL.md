---
name: mcp-server-lifecycle
description: >
  Start, stop, or check the status of this project's own MCP server
  (mcp_server/, served via run_mcp_server.py) using
  scripts/start_mcp_server.sh, scripts/stop_mcp_server.sh, and
  scripts/status_mcp_server.sh. Use this skill ANY time the user asks to
  start, stop, restart, or check the status of the MCP server for this
  project. Triggers on: "start the mcp server", "stop the mcp server",
  "mcp server status", "is the mcp server running", "restart the mcp
  server", or any combination of start/stop/status/restart for this
  project's MCP server. Always use this skill — never run
  run_mcp_server.py/kill commands manually without it.
triggers:
  - "start the mcp server"
  - "stop the mcp server"
  - "mcp server status"
  - "is the mcp server running"
  - "restart the mcp server"
  - "start mcp server"
  - "stop mcp server"
  - "status mcp server"
argument-hint: "[start|stop|status|restart]"
---

# MCP Server Lifecycle Skill — ai_tutorial MCP server

Manages the start, stop, and status of this project's own MCP server
(`mcp_server/`, exposing tools/prompts/resources over streamable-http,
run via `run_mcp_server.py`) using the project's shell scripts. This is
a separate process from the FastAPI app — see the `app-lifecycle` skill
for that one.

## Project paths

All commands run from the repo root (the session's working directory).

| Item          | Path                              |
|---------------|------------------------------------|
| Start script  | `scripts/start_mcp_server.sh`      |
| Stop script   | `scripts/stop_mcp_server.sh`       |
| Status script | `scripts/status_mcp_server.sh`     |
| PID file      | `.mcp_server.pid`                   |
| Log file      | `.mcp_server.log`                   |
| Default port  | `18383` (see `.env`'s `MCP_SERVER_PORT`) |
| MCP endpoint  | `http://localhost:18383/mcp`       |

## Operations

### Start

```bash
scripts/start_mcp_server.sh
```

- Resolves any missing secrets via `scripts/lib/env.sh` first (same
  resolution as `scripts/start_app.sh` — see the `infra-lifecycle` skill
  if it prompts for Postgres/Cohere values you don't need for the MCP
  server itself).
- Guards against double-start: exits cleanly with "Already running" if
  the PID file points at a live process.
- Runs `uv run python run_mcp_server.py` in the background
  (`nohup ... &`), writes the PID to `.mcp_server.pid`, and streams logs
  to `.mcp_server.log`.

### Stop

```bash
scripts/stop_mcp_server.sh
```

- No-ops safely ("Not running") if the server isn't running or the PID
  is stale.
- Sends a plain `kill` to the PID and removes `.mcp_server.pid`.

### Status

```bash
scripts/status_mcp_server.sh
```

- Reports "Running (PID ...) on port ..." or "Not running".

### Restart

No dedicated restart script:

```bash
scripts/stop_mcp_server.sh
scripts/start_mcp_server.sh
```

## Decision rules

| User intent                                  | Actions (in order) |
|-----------------------------------------------|---------------------|
| "start the mcp server"                        | start               |
| "stop the mcp server"                         | stop                |
| "mcp server status" / "is it running"         | status              |
| "restart the mcp server"                      | stop → start        |

Always follow the table — never skip steps.

## Error handling

| Symptom                                              | Fix                                                                 |
|-------------------------------------------------------|----------------------------------------------------------------------|
| Port already in use                                   | `scripts/status_mcp_server.sh` to check for a stale PID; `scripts/stop_mcp_server.sh` then retry. |
| `langchain_demo/mcp_client.py` / `langgraph_demo/mcp_client.py` calls fail | The MCP server isn't running — start it with this skill first; those concepts connect to `http://localhost:18383/mcp` and don't start the server themselves. |
| Need to see why it crashed                            | `tail -50 .mcp_server.log`                                          |

## Verifying it's actually up

```bash
scripts/status_mcp_server.sh
# expect "Running (PID ...) on port 18383"
```

The MCP server speaks the MCP protocol, not plain HTTP GET/JSON — use
`docs/TESTING.md`'s MCP section (via `/langchain/mcp/*` or
`/langgraph/mcp` on the main FastAPI app) to actually exercise it, not
a bare `curl` against port 18383.
