---
description: Start, stop, restart, or check the status of the ai_tutorial MCP server
argument-hint: "[start|stop|status|restart]"
---

Run the MCP server lifecycle action requested in `$ARGUMENTS` (default to
`status` if empty) for this project's own MCP server, using the exact
scripts below — never run `run_mcp_server.py`/`kill` manually instead.

- `start` → `scripts/start_mcp_server.sh`
- `stop` → `scripts/stop_mcp_server.sh`
- `status` → `scripts/status_mcp_server.sh`
- `restart` → `scripts/stop_mcp_server.sh` then `scripts/start_mcp_server.sh`

If `$ARGUMENTS` doesn't match one of these, ask which action was meant.

For full details (PID/log file locations, error handling, how to verify the
server actually came up), follow the `mcp-server-lifecycle` skill.
