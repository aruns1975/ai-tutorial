---
description: Start, stop, restart, or check the status of the ai_tutorial employee MCP server
argument-hint: "[start|stop|status|restart]"
---

Run the MCP server lifecycle action requested in `$ARGUMENTS` (default to
`status` if empty) for this project's employee CRUD MCP server — a
second, independent server from the project's original one (see `/mcp`
for that one) — using the exact scripts below — never run
`run_employee_mcp_server.py`/`kill` manually instead.

- `start` → `scripts/start_employee_mcp_server.sh`
- `stop` → `scripts/stop_employee_mcp_server.sh`
- `status` → `scripts/status_employee_mcp_server.sh`
- `restart` → `scripts/stop_employee_mcp_server.sh` then `scripts/start_employee_mcp_server.sh`

If `$ARGUMENTS` doesn't match one of these, ask which action was meant.

For full details (PID/log file locations, error handling, how to verify the
server actually came up), follow the `employee-mcp-server-lifecycle` skill.