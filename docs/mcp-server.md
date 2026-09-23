# This Project's Own MCP Server

## What MCP is, and why this project has its own server

The [Model Context Protocol](https://modelcontextprotocol.io) is a standard
way for an LLM application to reach tools, prompts, and resources that live
on a separate server, over a network protocol, instead of being imported
directly into the calling process. `tools/*.py`'s functions,
`langchain_demo/tool_calling.py`'s prompt templates, and
`langchain_demo/rag_corpus.md`'s sample document are all things this project
already has, defined as plain local Python — hosting them behind an MCP
server and connecting to that server from `langchain_demo/mcp_client.py`
and `langgraph_demo/mcp_client.py` demonstrates what changes (only *how*
they're reached) and what doesn't (the tools/prompts/resources themselves)
when the same content is exposed over MCP.

This is genuinely a separate process from the FastAPI app: `main.py`
(port `18282`, started by `scripts/start_app.sh`) is the demo application;
`run_mcp_server.py` (port `18383`, started by `scripts/start_mcp_server.sh`)
is the MCP server the two `mcp_client.py` concepts connect *to*, over HTTP,
the same way any external MCP client (e.g. Claude Desktop, an IDE
extension) would.

## Package layout

```
mcp_server/
  server.py     — builds the FastMCP instance, registers tools/prompts/resources
  tools.py      — registers a curated tools/*.py subset via mcp.add_tool(),
                  plus one @mcp.tool()-decorated, MCP-only tool
  prompts.py    — one prompt: explain_concept
  resources.py  — two resources: rag-corpus (static file), models (dynamic)
run_mcp_server.py — root entry point; runs mcp_server.server.mcp_app
```

`mcp_server/` is top-level, shared infrastructure — the same status as
`tools/` and `models/` — not nested under `langchain_demo/` or
`langgraph_demo/`, since both packages' `mcp_client.py` concepts connect to
it.

**Why `run_mcp_server.py`, not `mcp.py`:** a root-level `mcp.py` would shadow
the installed `mcp` PyPI package itself. Verified directly — once a
repo-root `mcp.py` exists, `from mcp.server.fastmcp import FastMCP` breaks
everywhere in the project with `ModuleNotFoundError: No module named
'mcp.server'; 'mcp' is not a package`, because Python resolves the local
same-named file in the script's own directory before site-packages.
`run_mcp_server.py` avoids the collision entirely while still mirroring
`main.py`'s "thin root entry point + package that does the real work" shape.

## Transport: streamable-http

```python
# mcp_server/server.py
mcp = FastMCP("ai-tutorial", host="0.0.0.0", port=port)
...
# run_mcp_server.py
mcp_app.run(transport="streamable-http")
```

FastMCP's `streamable-http` transport serves the MCP protocol over plain
HTTP at `POST/GET/DELETE /mcp` (the default `streamable_http_path`) — this
is what `MultiServerMCPClient` (used by both `mcp_client.py` concepts)
speaks. The alternative transports (`stdio`, `sse`) aren't used here: `stdio`
assumes the client spawns the server as a subprocess (not the case — this
server runs as its own long-lived process via `scripts/start_mcp_server.sh`),
and `sse` is the transport streamable-http superseded.

## Tools (`mcp_server/tools.py`)

Two ways to register a tool, shown side by side:

```python
_MCP_TOOLS = [adder, subtractor, multiplier, divider, reverse_text, word_count,
              is_palindrome, current_date, days_between, circle_area,
              rectangle_area, celsius_to_fahrenheit, km_to_miles, web_search]

def register_tools(mcp: FastMCP) -> None:
    for tool in _MCP_TOOLS:
        mcp.add_tool(tool)

    @mcp.tool()
    def server_uptime_seconds() -> float:
        """..."""
        return time.monotonic() - _SERVER_START_TIME
```

**`mcp.add_tool(fn)`** — every entry in `_MCP_TOOLS` is a plain, undecorated
function imported straight from `tools/*.py` — the exact same functions
`langchain_demo/tool_calling.py` and `langchain_demo/react_agent.py` bind via
`bind_tools([...])`. This is the right choice whenever a tool is (or could
be) also used outside MCP: `tools/*.py` must stay a framework-agnostic
library, so its functions can't be decorated with an MCP-specific decorator.

**`@mcp.tool()`** — used for `server_uptime_seconds`, an MCP-only tool with
no reason to live in `tools/*.py`: its answer depends on this server
process's own start time (`_SERVER_START_TIME`, set once at import time),
not on inputs a shared, reusable function could take. Decorating it in
place and `mcp.add_tool(fn)` build the exact same kind of `Tool` — both read
the name/description/schema from the function's name, docstring, and type
hints — so which one to reach for comes down to "does this function have
another caller to share it with," not a capability difference.

Either way, `tools/*.py`'s docstring convention (module docstring + "Call
this tool for..." + few-shot examples — see the project root `CLAUDE.md`)
is what a tool-calling model reads to pick the right tool, so
`server_uptime_seconds` follows it too even though it isn't in `tools/*.py`.

## Prompts (`mcp_server/prompts.py`)

One prompt, `explain_concept(topic: str) -> str`, themed around this
project's own subject matter (explaining a LangChain/LangGraph concept)
rather than a generic example.

## Resources (`mcp_server/resources.py`)

Two resources, chosen to show both shapes:

| URI | Kind | Source |
|---|---|---|
| `data://ai-tutorial/rag-corpus` | Static file | `langchain_demo/rag_demo.py`'s `CORPUS_PATH` — the exact file the RAG concept ingests, re-exposed as-is |
| `data://ai-tutorial/models` | Dynamic | Computed on each read from `SupportedModel`, so it always reflects whichever chat models this project currently supports |

## Local infra prerequisites

None to start the server itself. `web_search` (one of the registered
tools) additionally needs `GOOGLE_API_KEY`/`GOOGLE_CSE_ID` in `.env` to
actually succeed, same as everywhere else it's used — see
`tools/search_tools.py`.

## Starting/stopping it

Use the `mcp-server-lifecycle` skill (or `/mcp start|stop|status|restart`) —
never run `run_mcp_server.py`/`kill` manually:

```bash
scripts/start_mcp_server.sh    # port 18383 (MCP_SERVER_PORT in .env), logs to .mcp_server.log
scripts/stop_mcp_server.sh
scripts/status_mcp_server.sh
```

## How the two client concepts connect

See `docs/langchain/09-mcp-client.md` and `docs/langgraph/09-mcp-client.md`
for the client side. Both connect via
`langchain_mcp_adapters.client.MultiServerMCPClient` at
`http://localhost:$MCP_SERVER_PORT/mcp` — building the client doesn't open
a connection by itself; a session is opened per `get_tools()`/
`get_prompt()`/`get_resources()` call, so both concept modules can hold
one client singleton safely even before the MCP server has started.

## Gotchas

- If the MCP server isn't running, both client concepts' endpoints return a
  clean `503` ("Couldn't reach the MCP server... Start it with
  scripts/start_mcp_server.sh") rather than a raw `500` — the underlying
  connection failure surfaces from `langchain-mcp-adapters` as a generic
  `ExceptionGroup`, not a specific catchable exception type, so the
  controllers catch broadly and translate it into one clear message.
- `mcp.add_tool()` builds a JSON schema from each function's type hints —
  verified this handles `tools/math_tools.py`'s `int | float` union
  parameter types without any changes needed.
- The `data://ai-tutorial/models` resource returns a JSON-formatted string
  (FastMCP serializes non-string return values), not a raw Python list —
  `langchain_demo/mcp_client.py`'s `run_mcp_resource_demo` passes it
  through as-is rather than re-parsing it.
