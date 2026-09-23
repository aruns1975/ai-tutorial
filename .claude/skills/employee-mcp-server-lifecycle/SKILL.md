---
name: employee-mcp-server-lifecycle
description: >
  Start, stop, or check the status of this project's employee CRUD MCP
  server (employee_mcp_server/, served via run_employee_mcp_server.py)
  using scripts/start_employee_mcp_server.sh,
  scripts/stop_employee_mcp_server.sh, and
  scripts/status_employee_mcp_server.sh. This is a second, independent
  MCP server from the project's original one (mcp_server/) — use this
  skill ANY time the user asks to start, stop, restart, or check the
  status of the employee MCP server specifically. Triggers on: "start
  the employee mcp server", "stop the employee mcp server", "employee
  mcp server status", "is the employee mcp server running", "restart the
  employee mcp server", or any combination of start/stop/status/restart
  for this project's employee MCP server. Always use this skill — never
  run run_employee_mcp_server.py/kill commands manually without it.
triggers:
  - "start the employee mcp server"
  - "stop the employee mcp server"
  - "employee mcp server status"
  - "is the employee mcp server running"
  - "restart the employee mcp server"
  - "start employee mcp server"
  - "stop employee mcp server"
  - "status employee mcp server"
argument-hint: "[start|stop|status|restart]"
---

# Employee MCP Server Lifecycle Skill — ai_tutorial employee MCP server

Manages the start, stop, and status of this project's employee CRUD MCP
server (`employee_mcp_server/`, exposing create/get/update/delete/list
employee tools over streamable-http, run via
`run_employee_mcp_server.py`) using the project's shell scripts. This is
a separate process from both the FastAPI app (see the `app-lifecycle`
skill) and the project's original MCP server (see the
`mcp-server-lifecycle` skill) — all three run independently.

## Project paths

All commands run from the repo root (the session's working directory).

| Item          | Path                                        |
|---------------|----------------------------------------------|
| Start script  | `scripts/start_employee_mcp_server.sh`       |
| Stop script   | `scripts/stop_employee_mcp_server.sh`        |
| Status script | `scripts/status_employee_mcp_server.sh`      |
| PID file      | `.employee_mcp_server.pid`                    |
| Log file      | `.employee_mcp_server.log`                    |
| Default port  | `18384` (see `.env`'s `EMPLOYEE_MCP_SERVER_PORT`) |
| MCP endpoint  | `http://localhost:18384/mcp`                 |

## Operations

### Start

```bash
scripts/start_employee_mcp_server.sh
```

- Resolves any missing secrets via `scripts/lib/env.sh` first (same
  resolution as `scripts/start_app.sh` — this server itself needs none,
  but the shared `.env` may still prompt for unrelated values on a fresh
  clone; see the `infra-lifecycle` skill).
- Guards against double-start: exits cleanly with "Already running" if
  the PID file points at a live process.
- Runs `uv run python run_employee_mcp_server.py` in the background
  (`nohup ... &`), writes the PID to `.employee_mcp_server.pid`, and
  streams logs to `.employee_mcp_server.log`.

### Stop

```bash
scripts/stop_employee_mcp_server.sh
```

- No-ops safely ("Not running") if the server isn't running or the PID
  is stale.
- Sends a plain `kill` to the PID and removes `.employee_mcp_server.pid`.

### Status

```bash
scripts/status_employee_mcp_server.sh
```

- Reports "Running (PID ...) on port ..." or "Not running".

### Restart

No dedicated restart script:

```bash
scripts/stop_employee_mcp_server.sh
scripts/start_employee_mcp_server.sh
```

## Decision rules

| User intent                                            | Actions (in order) |
|----------------------------------------------------------|---------------------|
| "start the employee mcp server"                         | start               |
| "stop the employee mcp server"                          | stop                |
| "employee mcp server status" / "is it running"          | status              |
| "restart the employee mcp server"                       | stop → start        |

Always follow the table — never skip steps. If the user just says "start
the mcp server" with no mention of "employee", that means the *original*
MCP server — use the `mcp-server-lifecycle` skill instead.

## Error handling

| Symptom                                              | Fix                                                                 |
|-------------------------------------------------------|----------------------------------------------------------------------|
| Port already in use                                   | `scripts/status_employee_mcp_server.sh` to check for a stale PID; `scripts/stop_employee_mcp_server.sh` then retry. |
| Need to see why it crashed                            | `tail -50 .employee_mcp_server.log`                                 |

## Verifying it's actually up

```bash
scripts/status_employee_mcp_server.sh
# expect "Running (PID ...) on port 18384"
```

The employee MCP server speaks the MCP protocol, not plain HTTP
GET/JSON — no FastAPI endpoint calls into it yet (there's no
`langchain_demo`/`langgraph_demo` client concept for it), so use
`docs/employee-mcp-server.md`'s "Verifying it works" section (a direct
`MultiServerMCPClient` script) to actually exercise it, not a bare
`curl` against port 18384.