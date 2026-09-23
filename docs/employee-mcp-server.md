# The Employee MCP Server — a Second, Independent MCP Server

## What this demonstrates

This project already has one MCP server (`mcp_server/`, see
`docs/mcp-server.md`). `employee_mcp_server/` is a **second, completely
independent** MCP server — its own process, its own port, its own tools,
its own in-memory data. Nothing is shared between the two servers.

The point is to demonstrate that `langchain_mcp_adapters.client.MultiServerMCPClient`
(already used by `langchain_demo/mcp_client.py` and
`langgraph_demo/mcp_client.py`) is built to connect to *more than one*
named MCP server at once — it takes a dict keyed by server name, not a
single URL. This project just hasn't wired a client concept up to this
second server yet (see "What's not built yet" below).

## Package layout

```
employee_mcp_server/
  server.py — builds the FastMCP instance, registers tools
  tools.py  — registers the five CRUD functions via mcp.add_tool()
  store.py  — the CRUD functions themselves + the in-memory Employee store
run_employee_mcp_server.py — root entry point; runs employee_mcp_server.server.employee_mcp_app
```

Same three-layer shape as `mcp_server/` (server/tools/domain-logic), and
`employee_mcp_server/` is top-level for the same reason `mcp_server/`
is — but unlike `tools/`, `models/`, and `mcp_server/`, it is **not**
shared infrastructure imported by `langchain_demo/`/`langgraph_demo/`.
It's a standalone server any MCP client (this project's own, or an
external one like Claude Desktop) can connect to independently.

## The Employee record

```python
{
    "id": "a1b2c3d4",       # server-generated (uuid4 hex, short)
    "name": "Jane Doe",
    "department": "Engineering",
    "dob": "1990-05-12",     # ISO date, matching tools/datetime_tools.py's convention
    "salary": 95000,
    "phone": "555-0100",
    "email": "jane.doe@example.com",
}
```

`id` is never supplied by the caller — `create_employee` generates it.
Asking a tool-calling model to invent a globally-unique id itself is
unreliable, and every other CRUD tool just needs whatever id
`create_employee` already returned.

## Tools (`employee_mcp_server/store.py` + `tools.py`)

| Tool | Purpose |
|---|---|
| `create_employee(name, department, dob, salary, phone, email)` | Create a new employee, return it (with its new `id`) |
| `get_employee(employee_id)` | Look up one employee by id |
| `update_employee(employee_id, ...)` | Partial update — only non-`None` args are changed |
| `delete_employee(employee_id)` | Delete an employee, return the deleted record |
| `list_employees()` | Return every employee currently in the store |

All five are plain functions defined in `store.py`, registered onto the
server with `mcp.add_tool(fn)` in `tools.py` — the same registration
style `mcp_server/tools.py` uses for its `tools/*.py` subset (see
`docs/mcp-server.md`'s "Tools" section for the other registration style,
`@mcp.tool()`, and when each makes sense). Each function follows this
project's `tools/*.py` docstring convention (one-line summary, "Call
this tool for..." with trigger phrases, few-shot examples) even though
it doesn't live in `tools/*.py`, since that's what a tool-calling client
reads to pick the right tool regardless of where the function lives.

The store itself (`create_employee_store()`'s closure over a private
`_employees` dict) is in-memory only — it resets whenever this server
restarts. There's no Redis/Postgres backend for it, unlike this
project's RAG/Memory/Agent concepts; adding one would be a reasonable
next step if this data needs to survive a restart, but isn't needed to
demonstrate a second independent MCP server.

## Transport, port, and local infra prerequisites

Same `streamable-http` transport as `mcp_server/` (see that doc's
"Transport" section for why), on its own port:

```python
# employee_mcp_server/server.py
mcp = FastMCP("ai-tutorial-employees", host="0.0.0.0", port=port)
```

| | |
|---|---|
| Port | `EMPLOYEE_MCP_SERVER_PORT` in `.env`, default `18384` |
| MCP endpoint | `http://localhost:18384/mcp` |
| Local infra needed | None — the store is in-process memory |

## Starting/stopping it

Use the `employee-mcp-server-lifecycle` skill (or `/employee-mcp start|stop|status|restart`) —
never run `run_employee_mcp_server.py`/`kill` manually:

```bash
scripts/start_employee_mcp_server.sh    # port 18384 (EMPLOYEE_MCP_SERVER_PORT in .env), logs to .employee_mcp_server.log
scripts/stop_employee_mcp_server.sh
scripts/status_employee_mcp_server.sh
```

## Verifying it works

There's no FastAPI endpoint wired up to this server yet (see below), so
exercise it directly with a `MultiServerMCPClient` script, the same
client class `langchain_demo/mcp_client.py` uses:

```bash
uv run python -c "
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    client = MultiServerMCPClient({
        'ai_tutorial_employees': {'transport': 'streamable_http', 'url': 'http://localhost:18384/mcp'},
    })
    tools = await client.get_tools(server_name='ai_tutorial_employees')
    by_name = {t.name: t for t in tools}

    created = await by_name['create_employee'].ainvoke(
        {'name': 'Jane Doe', 'department': 'Engineering', 'dob': '1990-05-12',
         'salary': 95000, 'phone': '555-0100', 'email': 'jane.doe@example.com'}
    )
    print('created:', created)

asyncio.run(main())
"
```

Expect a JSON employee record back with a freshly-generated `id`.

## What's not built yet (optional next step)

Neither `langchain_demo/mcp_client.py` nor `langgraph_demo/mcp_client.py`
connects to this server — both still only talk to `mcp_server/`. Wiring
one of them up to both servers at once (via `MultiServerMCPClient`'s
multi-server dict) would be the natural way to turn this into an actual
demo endpoint, and is the reason this server exists as a second,
independent process rather than just more tools on the first one — but
it's a separate concept-level change, not part of standing the server up.

## Want to see the raw protocol?

See [docs/mcp-protocol.md](mcp-protocol.md) for real `curl` commands
against this exact server and the actual JSON-RPC request/response pairs
captured live — `initialize`, `tools/list`, `tools/call` (success and
error), and the two transport-level rejections a malformed request gets.

## Gotchas

- The store is in-memory and per-process: restarting the employee MCP
  server (or the whole machine) discards every employee created.
- `create_employee` always generates a new `id` — passing an `id`
  argument yourself has no effect (it isn't one of the function's
  parameters), matching the reasoning in "The Employee record" above.
- `update_employee`'s unset fields must be omitted (or passed as
  `None`), not sent as empty strings — an empty string would overwrite
  the field with `""` rather than leaving it unchanged.