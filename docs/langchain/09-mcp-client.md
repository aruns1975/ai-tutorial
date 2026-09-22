# MCP (Model Context Protocol) Client

> 🧪 **Try it hands-on:** [`jupyter/09-mcp-client.ipynb`](jupyter/09-mcp-client.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

Everywhere else in this project, an LLM reaches a tool or a prompt template
because the calling code imported it directly (`tool_calling.py`'s
`_TOOLS` list, `prompts_and_parsers.py`'s `ChatPromptTemplate`). MCP
inverts that: tools, prompts, and resources live on a separate server, and
a client fetches them over a standard protocol instead of importing them.
This concept connects to **this project's own MCP server**
(`mcp_server/`, see `docs/mcp-server.md`) and exercises all three MCP
primitives it exposes.

Once fetched, an MCP tool is just a LangChain `BaseTool` — so
`run_mcp_tool_calling_demo` below is `tool_calling.py`'s
`run_tool_calling_demo` almost line for line; the only real difference is
`await client.get_tools(...)` in place of a local `_TOOLS` list.
`run_mcp_agent_demo` is the same relationship one level up: it hands the
MCP-fetched tools to LangGraph's prebuilt `create_react_agent` instead of
hand-executing a single round, mirroring how `react_agent.py` relates to
`tool_calling.py` for locally-imported tools.

## Code walkthrough

See `langchain_demo/mcp_client.py`.

```python
_client = MultiServerMCPClient({_SERVER_NAME: {"transport": "streamable_http", "url": _MCP_SERVER_URL}})

async def run_mcp_tool_calling_demo(user_message, model=SupportedModel.llama3_2) -> dict:
    tools = await _client.get_tools(server_name=_SERVER_NAME)
    ...
    ai_message = llm.bind_tools(tools).invoke(messages)
```

Four functions — direct tool calling and its agent counterpart, plus one
per remaining MCP primitive:

- **`run_mcp_tool_calling_demo(user_message, model)`** — fetches tools,
  binds them, executes whichever the model calls (via each `BaseTool`'s
  `.ainvoke(args)`, since the MCP round-trip is async), feeds results back,
  re-invokes for a final answer. Exactly one reasoning round, hand-written.
- **`run_mcp_agent_demo(user_message, model, memory_backend, session_id)`**
  — fetches the same tools, but hands them to
  `create_react_agent(get_chat_model(model), tools=tools, checkpointer=...)`
  and lets it decide how many tool-call rounds it needs, instead of the
  single hand-executed round above. Same `session_id`/`memory_backend`
  shape as `react_agent.py`'s `run_agent_demo`, reusing its
  `AgentMemoryBackend` enum and redis/postgres checkpointer builders
  directly (same package, already-debugged setup code) — omit
  `session_id` for a stateless single-shot call, or pass the same value
  across calls for multi-turn memory.
- **`run_mcp_prompt_demo(topic)`** — fetches the server's `explain_concept`
  prompt filled in with `topic`, via `client.get_prompt(server_name,
  prompt_name, arguments={...})`.
- **`run_mcp_resource_demo(uri)`** — reads a resource by URI via
  `client.get_resources(server_name, uris=[uri])`.

Building `MultiServerMCPClient` doesn't connect to anything — a session
opens per call, so this module's client singleton is safe to hold even
before the MCP server has started (you'll only see a failure once you
actually call one of the four functions above).

## Choosing a model

`run_mcp_tool_calling_demo` and `run_mcp_agent_demo` both accept an
optional `model` **query parameter** (`?model=...`): `"llama3.2"`
(default) or `"gemma4"`. `run_mcp_agent_demo` additionally accepts
`memory_backend` (`"memory"` default, `"redis"`, or `"postgres"`) and
`session_id` — same as `/langchain/agents`.

## Local infra prerequisites

`scripts/start_mcp_server.sh` (port `18383`) — every endpoint below
returns a `503` with a message telling you to start it, rather than a raw
`500`, if it isn't running.

## How to call it

```bash
# Tools: MCP-sourced tool calling, one hand-executed round.
curl -s -X POST localhost:18282/langchain/mcp/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "what is 12 times 7?"}'

# Agent: same MCP-sourced tools, but a full ReAct loop decides the rounds.
# session_id carries memory across calls — the second question needs it
# to know what "the result" refers to.
curl -s -X POST "localhost:18282/langchain/mcp/agent?session_id=demo" \
  -H 'Content-Type: application/json' -d '{"message": "what is 3+4?"}'
curl -s -X POST "localhost:18282/langchain/mcp/agent?session_id=demo" \
  -H 'Content-Type: application/json' -d '{"message": "what happens if I add 5 to the result?"}'

# Prompts: fetch the explain_concept prompt filled in with a topic.
curl -s -X POST localhost:18282/langchain/mcp/prompt \
  -H 'Content-Type: application/json' -d '{"topic": "RAG"}'

# Resources: read the dynamic models list (default) or the static corpus.
curl -s localhost:18282/langchain/mcp/resource
curl -s "localhost:18282/langchain/mcp/resource?uri=data://ai-tutorial/rag-corpus"
```

## Gotchas

- The `uri` query parameter on `/langchain/mcp/resource` isn't validated
  against the server's actual resource list before the call — an unknown
  URI surfaces as the same `503`-style error as an unreachable server,
  since both come back through the same `except Exception` in the
  controller. `mcp_server/resources.py` is the source of truth for what
  URIs exist.
- Same tool-execution-error handling as `tool_calling.py`: a tool call that
  raises (e.g. `web_search` without Google credentials) is caught and fed
  back to the model as the tool's result string, not left to crash the
  request — see that concept's Gotchas for the live example, which applies
  identically here since it's the same underlying `web_search` function.
- `run_mcp_agent_demo`'s agent sometimes does part of a multi-step request
  in its head instead of calling a second tool (e.g. "multiply then add 5"
  may call `multiplier` once and add 5 itself in the final message rather
  than also calling `adder`) — a small-model reasoning quirk, not a bug in
  the MCP wiring; `steps` shows exactly which tool calls actually happened
  so you can see this live.
- Omitting `session_id` on a follow-up question gets a fresh thread with
  zero history, so "what happens if I add 5 to the result?" on its own
  has no idea what "the result" is — always pass the same `session_id`
  across a multi-turn conversation, same as `/langchain/agents`.
- **`session_id` alone isn't enough to prevent a tool-call repeat loop —
  `AGENT_SYSTEM_PROMPT` (reused from `react_agent.py`) is what actually
  prevents it.** Verified live: even with `session_id` correctly passed
  and gemma4 correctly recalling the previous turn's result, LangGraph's
  default `create_react_agent` loop re-called `adder` with **identical**
  arguments ~14 times after already getting the right answer, before
  finally responding in plain text — see
  `docs/langchain/06-react-agents.md`'s Gotchas for the full
  reproduction (same underlying `create_react_agent` mechanism, first
  found via `/langchain/agents`). `AGENT_SYSTEM_PROMPT` fixed it here
  too, reproduced clean across repeated runs. `_AGENT_RECURSION_LIMIT`
  (15) is only a backstop for if that instruction ever doesn't hold —
  hitting it raises `GraphRecursionError`, surfaced as a `500` (not the
  connectivity `503`).
