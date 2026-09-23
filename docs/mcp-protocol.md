# MCP, Under the Hood: the Raw Protocol Conversation

`langchain_demo/mcp_client.py`, `langgraph_demo/mcp_client.py`, and the
verification script in `docs/employee-mcp-server.md` all talk to this
project's MCP servers through `langchain_mcp_adapters.client.MultiServerMCPClient`
— a Python object with `.get_tools()`/`.ainvoke()` methods. That's the
right layer to build on, but it hides exactly what's going over the
wire. This doc peels that back: real `curl` commands against a running
server, and the real JSON-RPC responses that came back, captured live
against `employee_mcp_server` (port `18384`) while it was running with
its default in-memory store.

Everything here applies identically to this project's original MCP
server (`mcp_server/`, port `18383`, see `docs/mcp-server.md`) — both are
built with the same `mcp.server.fastmcp.FastMCP` class on the same
`streamable-http` transport. Only the tool names/schemas differ.

## The shape of it: JSON-RPC 2.0 over one HTTP endpoint

MCP's `streamable-http` transport is JSON-RPC 2.0 messages, all POSTed to
a single URL (`/mcp`, FastMCP's default `streamable_http_path`). Every
request body looks like:

```json
{"jsonrpc": "2.0", "id": 1, "method": "...", "params": {...}}
```

...and every response (wrapped in an `event: message` / `data: ...`
Server-Sent-Events envelope, since the transport keeps the connection
open for streaming) looks like:

```json
{"jsonrpc": "2.0", "id": 1, "result": {...}}
```

Two things curl has to get right that a bare `Content-Type: application/json`
request wouldn't automatically satisfy:

1. **`Accept` header** must list *both* `application/json` and
   `text/event-stream` — the server replies over SSE even to a
   single-shot POST, so it insists the client says it can read that.
2. **`Mcp-Session-Id`** — the first response (to `initialize`) returns
   this in a response header. Every request after that must send it back
   as a request header, or the server has no way to know which
   client/session is talking.

Skip either one and the server rejects the request before it ever reaches
your tool code — see "Transport-level rejections" below for what that
looks like.

## Step 1 — `initialize`

The handshake every MCP session starts with: the client declares which
protocol version and capabilities it speaks, the server replies with its
own.

```bash
curl -s -D - -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {"name": "curl-demo", "version": "0.0.1"}
    }
  }'
```

Real response (headers + body):

```
HTTP/1.1 200 OK
content-type: text/event-stream
mcp-session-id: 1d0e2122be4f4e51a6d5a10fb58d0139
...

event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"ai-tutorial-employees","version":"1.30.0"}}}
```

`serverInfo.name` is the first argument to `FastMCP(...)` in
`employee_mcp_server/server.py` (`"ai-tutorial-employees"`) — not the
`server_name` key `MultiServerMCPClient` uses to look the server up in
its own config dict; those are two independent names that happen to
often look similar. `mcp-session-id` (`1d0e2122be4f4e51a6d5a10fb58d0139`
here — yours will differ every run) is what every following request in
this walkthrough reuses.

## Step 2 — `notifications/initialized`

### Why two separate calls instead of one?

`initialize` and `notifications/initialized` do two genuinely different
jobs, and JSON-RPC has two genuinely different message shapes for them:

- **`initialize` is a *request*** — it needs an answer. Its whole job is
  **negotiation**: the client proposes a protocol version and lists what
  it supports (`capabilities`); the server answers with what *it*
  actually supports (its own `protocolVersion` and `capabilities`, seen
  in Step 1's response above). Neither side can safely do anything else
  until this round-trip completes, because neither side yet knows what
  the other can do.
- **`notifications/initialized` is a *notification*** — no `id`, no
  reply. Its job is for the **client** to say "I've seen what you can
  do, I've finished whatever local setup that implied, and I'm ready for
  normal traffic now." There's nothing for the server to answer, because
  the client isn't asking anything — it's just flipping the session from
  "negotiating" to "live."

The reason this can't just be folded into the `initialize` response
itself is that the response only tells the *client* something (what the
server supports) — it says nothing about when the *client* is done
reacting to that information. A server that started sending
requests/notifications the instant it sent its `initialize` response
would be racing ahead of a client that might still be setting up
handlers for the capabilities it just learned about. The separate
notification is the client's explicit "go" signal, sent on its own
schedule.

This is the same two-step shape the Language Server Protocol (LSP) uses
— MCP's lifecycle is explicitly modeled on it — for exactly the same
reason: version/capability negotiation is a question-and-answer (needs a
response), but "I'm ready" is an announcement (doesn't).

**In practice, you never hand-write this.** `mcp.client.session.ClientSession.initialize()`
— what `MultiServerMCPClient` calls under the hood — does both steps for
you as one Python call:

```python
# mcp/client/session.py (this project's installed mcp==1.30.0)
async def initialize(self) -> types.InitializeResult:
    result = await self.send_request(types.InitializeRequest(...), types.InitializeResult)
    ...
    await self.send_notification(types.InitializedNotification())
    return result
```

This walkthrough splits it into two separate `curl` commands purely
because curl has no notion of "one logical handshake" — each HTTP POST
is its own request, so the two JSON-RPC messages `initialize()` sends
become two separate `curl` invocations here.

**A verified gotcha:** the spec expects a server not to treat a session
as fully live until it's received `notifications/initialized` — but
`employee_mcp_server`'s underlying `mcp==1.30.0` server implementation
was verified live to **not** actually enforce that ordering: sending
`tools/list` immediately after `initialize`, with `notifications/initialized`
never sent at all, still returned a normal `200` with the full tool
list. Don't take this as license to skip it, though — it's this
particular server implementation being lenient, not something the spec
guarantees, and `MultiServerMCPClient` always sends it anyway (see
above), so a well-behaved client never needs to rely on that leniency.

On the wire, it's the smallest possible message — no `id`, no `params` —
and gets back a `202 Accepted` with an empty body, not a JSON-RPC result:

```bash
curl -s -D - -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Mcp-Session-Id: 1d0e2122be4f4e51a6d5a10fb58d0139' \
  -d '{"jsonrpc": "2.0", "method": "notifications/initialized"}'
```

```
HTTP/1.1 202 Accepted
mcp-session-id: 1d0e2122be4f4e51a6d5a10fb58d0139
content-length: 0
```

## Step 3 — `tools/list`

Asks the server for every registered tool's name, description, and JSON
Schema — this is the call `MultiServerMCPClient.get_tools()` makes under
the hood, and exactly what a tool-calling LLM's `bind_tools([...])`
schema comes from.

```bash
curl -s -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Mcp-Session-Id: 1d0e2122be4f4e51a6d5a10fb58d0139' \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
```

One entry from the real response (`create_employee` — the full response
lists all five `employee_mcp_server/store.py` tools):

```json
{
  "name": "create_employee",
  "description": "\nCreate a new employee record and return it, including a\nserver-generated id.\n\nCall this tool for requests like \"add a new employee\"...",
  "inputSchema": {
    "properties": {
      "name": {"title": "Name", "type": "string"},
      "department": {"title": "Department", "type": "string"},
      "dob": {"title": "Dob", "type": "string"},
      "salary": {"title": "Salary", "type": "number"},
      "phone": {"title": "Phone", "type": "string"},
      "email": {"title": "Email", "type": "string"}
    },
    "required": ["name", "department", "dob", "salary", "phone", "email"],
    "title": "create_employeeArguments",
    "type": "object"
  }
}
```

`description` is the function's docstring, verbatim, whitespace and all
— confirming live what `docs/mcp-server.md` and `docs/employee-mcp-server.md`
say about `tools/*.py`'s docstring convention: this is literally what a
tool-calling model reads. `inputSchema` is built entirely from the
function's parameter names/types/defaults — `update_employee`'s optional
params (`name: str | None = None`, etc.) show up as
`"anyOf": [{"type": "string"}, {"type": "null"}], "default": null` for
each one, which is how the schema communicates "this argument is
optional" to a caller.

**A schema nuance worth calling out:** only `list_employees` — the one
function annotated `-> list[dict]` — got an extra `outputSchema` key in
its `tools/list` entry, describing the shape of its return value. The
four functions annotated `-> dict` (`create_employee`, `get_employee`,
`update_employee`, `delete_employee`) didn't. This is the `mcp` SDK's
`structured_output` auto-detection (see `MCPServer.add_tool()`'s
docstring: `structured_output: bool | None` — `None` auto-detects from
the return type annotation) doing something with `list[X]` it doesn't do
with a bare `dict`. Nothing in this project's code requests this
difference — it falls out of the return-type hints already needed for
the tool to work at all.

## Step 4 — `tools/call` (success)

Actually invoking a tool: `params.name` picks the tool, `params.arguments`
is the JSON object matching its `inputSchema`.

```bash
curl -s -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Mcp-Session-Id: 1d0e2122be4f4e51a6d5a10fb58d0139' \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "create_employee",
      "arguments": {
        "name": "Jane Doe",
        "department": "Engineering",
        "dob": "1990-05-12",
        "salary": 95000,
        "phone": "555-0100",
        "email": "jane.doe@example.com"
      }
    }
  }'
```

Real response:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {"type": "text", "text": "{\n  \"id\": \"01a02c96\",\n  \"name\": \"Jane Doe\",\n  \"department\": \"Engineering\",\n  \"dob\": \"1990-05-12\",\n  \"salary\": 95000.0,\n  \"phone\": \"555-0100\",\n  \"email\": \"jane.doe@example.com\"\n}"}
    ],
    "isError": false
  }
}
```

Note `result.content` is a *list of content blocks* — here one text
block whose `text` is the function's return value, JSON-encoded as a
string. This is why `langchain_demo/mcp_client.py`'s tools come back as
`langchain_core.messages.ToolMessage(content=result, ...)` rather than a
raw Python dict: the MCP wire format is always "a list of content
blocks," regardless of what the underlying Python function returned.

For `list_employees` specifically (the `structured_output`-eligible one
from Step 3), the real response carries *both* the usual `content` text
block *and* a `structuredContent` field with the actual parsed JSON
array — a client that wants structured data can read `structuredContent`
directly instead of re-parsing `content[0].text`:

```
{
  "content": [{"type": "text", "text": "<employee 1 as a JSON string>"}, {"type": "text", "text": "<employee 2 as a JSON string>"}],
  "structuredContent": {"result": [{"id": "d3440af7", "name": "Arun", "...": "..."}, {"id": "e5ed3629", "name": "Satish", "...": "..."}]},
  "isError": false
}
```

## Step 5 — `tools/call` (tool-level error)

Calling `get_employee` with an id that doesn't exist:

```bash
curl -s -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Mcp-Session-Id: 1d0e2122be4f4e51a6d5a10fb58d0139' \
  -d '{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "get_employee", "arguments": {"employee_id": "doesnotexist"}}}'
```

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "content": [{"type": "text", "text": "Error executing tool get_employee: No employee found with id 'doesnotexist'"}],
    "isError": true
  }
}
```

The `ValueError` raised inside `store.py`'s `get_employee` did **not**
become a JSON-RPC-level error (there's no top-level `"error"` key, and
the HTTP status is still `200`) — it became a normal `result` with
`isError: true` and the exception message as text. This is the same
"catch and hand back as a string/error content block" behavior
`langchain_demo/tool_utils.py`'s `create_tool_caller` relies on for
locally-bound tools (see the project root `CLAUDE.md`'s "Verified facts"
section) — MCP does the equivalent thing for you automatically for tools
reached over the protocol, at the transport layer.

## Transport-level rejections

Two failure modes that never reach `store.py`'s Python code at all —
the transport itself rejects the request:

**Missing `Accept: text/event-stream`:**

```bash
curl -s -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc": "2.0", "id": 6, "method": "tools/list"}'
```
```json
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept both application/json and text/event-stream"}}
```
(HTTP `406 Not Acceptable`)

**Missing `Mcp-Session-Id` on a post-`initialize` request:**

```bash
curl -s -X POST http://localhost:18384/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc": "2.0", "id": 7, "method": "tools/list"}'
```
```json
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Bad Request: Missing session ID"}}
```
(HTTP `400 Bad Request`)

Both come back with `"id": "server-error"` instead of echoing the
request's real `id` — a sign these are rejected before the server even
looks at the request body's `id` field.

## How this maps back to the Python layer

Everything above is exactly what `MultiServerMCPClient` does for you:

| Wire-level step | `MultiServerMCPClient` equivalent |
|---|---|
| `initialize` + `notifications/initialized` | Done once per connection, inside `client.get_tools(...)`/`.get_prompt(...)`/`.get_resources(...)` — not something you call directly |
| `Mcp-Session-Id` bookkeeping | Handled internally per session; never appears in `mcp_client.py` code |
| `tools/list` | `await client.get_tools(server_name=...)` |
| `tools/call` | `await tool.ainvoke(arguments)` on one of `get_tools()`'s returned `BaseTool` objects |
| `result.content[0].text` string | What `ainvoke()` hands back as the tool's result — `mcp_client.py`'s nodes pass it straight into a `ToolMessage(content=result, ...)` |

`docs/mcp-server.md` and `docs/employee-mcp-server.md`'s "Verifying it
works" sections use `MultiServerMCPClient` rather than raw `curl`
specifically because it's the layer this project's actual code is built
on — this doc exists so you can see what that layer is doing for you,
not to replace it.