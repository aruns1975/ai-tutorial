# MCP (Model Context Protocol) Client, Inside a Graph

## Concept

The LangGraph-flavored counterpart to `docs/langchain/09-mcp-client.md`,
in two parts: a single-node `StateGraph` (`run_mcp_client_demo`) that calls
tools fetched from this project's own MCP server (`mcp_server/`, see
`docs/mcp-server.md`) instead of a locally-imported `tools/*.py` function,
and a memory-backed agent (`run_mcp_agent_demo`) that's a genuinely
hand-built LangGraph reason/act loop — an explicit two-node `StateGraph`
(`call_model` <-> `call_tools`) with a checkpointer attached at compile
time. Once fetched, an MCP tool is just a LangChain `BaseTool` regardless
of which framework's execution model calls it — that's true for both
parts here, same as the LangChain-side concept.

**Why not `langgraph.prebuilt.create_react_agent` here** (unlike
`langchain_demo/mcp_client.py`'s own `run_mcp_agent_demo`, which does use
it): a prebuilt hides the reason/act loop behind one call — fine for a
LangChain-flavored concept, but it defeats the point of a `langgraph_demo`
concept, which should show the graph itself. Same reasoning
`docs/langgraph/07-multi-agent.md` already gives for hand-building a
multi-graph system instead of relying on a prebuilt agent.

Compare to `branching.py`'s `solve_math` node (binds `tools/math_tools.py`
functions directly via `bind_tools`) and `multi_agent.py` (subgraphs as
specialists): this file binds the same *kind* of tools as `branching.py`,
just fetched over MCP instead of imported.

## Code walkthrough — single-node graph (`run_mcp_client_demo`)

See `langgraph_demo/mcp_client.py`.

```python
class MCPToolState(TypedDict):
    question: str
    answer: str

async def call_mcp_tools(state: MCPToolState) -> dict:
    tools = await _client.get_tools(server_name=_SERVER_NAME)
    ai_message = llm.bind_tools(tools).invoke([HumanMessage(content=state["question"])])
    ...
```

```
START -> call_mcp_tools -> END
```

One node, `call_mcp_tools`, does everything `langchain_demo/mcp_client.py`'s
`run_mcp_tool_calling_demo` does — fetch tools, bind, execute any tool
call via `.ainvoke(args)`, re-invoke for a final answer — as a single
graph node instead of a plain function. Stateless: no session memory.

## Code walkthrough — memory-backed agent (`run_mcp_agent_demo`)

```python
async def call_model(state: MessagesState) -> dict:
    tools = await _client.get_tools(server_name=_SERVER_NAME)
    response = llm.bind_tools(tools).invoke([SystemMessage(content=AGENT_SYSTEM_PROMPT), *state["messages"]])
    return {"messages": [response]}

async def call_tools(state: MessagesState) -> dict:
    tools = await _client.get_tools(server_name=_SERVER_NAME)
    tools_by_name = {tool.name: tool for tool in tools}
    last_message = state["messages"][-1]

    tool_messages = []
    for tool_call in last_message.tool_calls:
        cached_result = _find_prior_tool_result(state["messages"][:-1], tool_call["name"], tool_call["args"])
        if cached_result is not None:
            result = cached_result
        else:
            tool = tools_by_name[tool_call["name"]]
            try:
                result = await tool.ainvoke(tool_call["args"])
            except Exception as exc:
                result = f"Error calling tool '{tool_call['name']}': {exc}"
        tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
    return {"messages": tool_messages}

graph = StateGraph(MessagesState)
graph.add_node("call_model", call_model)
graph.add_node("call_tools", call_tools)
graph.add_edge(START, "call_model")
graph.add_conditional_edges("call_model", route_after_model)  # "call_tools" or END
graph.add_edge("call_tools", "call_model")
return graph.compile(checkpointer=build_checkpointer(memory_backend))
```

```
START -> call_model --[tool_calls present]--> call_tools --> call_model (loop)
                     --[no tool_calls]-------> END
```

`MessagesState` (`langgraph.graph.MessagesState`) is a core LangGraph
primitive — a `TypedDict` with `messages: Annotated[list, add_messages]`
— not a LangChain agent abstraction; this is the same reason/act loop
`create_react_agent` runs internally, just written out as explicit nodes
and edges. Two deliberate reuse choices, same as before:

- **Checkpointer**: `langgraph_demo/checkpointers.py`'s
  `CheckpointBackend`/`build_checkpointer` — this package's own shared
  persistence story (used by `persistence.py`/`interrupts.py` too), *not*
  `langchain_demo.react_agent`'s `AgentMemoryBackend`/per-backend files.
  This is the deliberate cross-package split documented in the project
  root `CLAUDE.md` — each package keeps its own persistence story.
- **`AGENT_SYSTEM_PROMPT`**: imported directly from
  `langchain_demo.react_agent` — a small, genuinely generic instruction
  (not persistence logic), so it's reused rather than re-derived. It's
  prepended to the message list at inference time in `call_model`, never
  persisted into `state["messages"]` itself (so it isn't duplicated on
  every turn).

**`_find_prior_tool_result` — a benefit hand-building buys you.**
`call_tools` checks the accumulated message history for a tool already
called with the exact same name/args and, if found, reuses that result
instead of re-invoking the tool. `AGENT_SYSTEM_PROMPT` alone (see
`docs/langchain/06-react-agents.md`'s Gotchas) was found to reduce but
not eliminate gemma4 re-calling a tool with identical arguments several
times in a longer conversation — this is a hard, deterministic backstop
for exactly that case, something you can't easily add to a prebuilt
`create_react_agent` without reaching into its internals. It makes a
repeat *cheap* (no real tool re-invocation — verified live: repeated
calls return the identical cached MCP response object, not a fresh one),
but doesn't stop the model from *asking* again, which is why
`_AGENT_RECURSION_LIMIT` still matters — see Gotchas below.

`session_id` is LangGraph's `thread_id`, same shape as
`langchain_demo/mcp_client.py`'s agent: omit it for a stateless
single-shot call, pass the same value across calls for multi-turn memory.

## Why both are `.ainvoke()`, not `.invoke()`

`call_mcp_tools`, and both `call_model`/`call_tools` in the agent graph,
are async (they await the MCP client), so this is one of the few
`langgraph_demo/*.py` concepts — alongside `streaming_graph.py` and
`rag/graph.py` — invoked via `.ainvoke()` rather than `.invoke()`. Every
other concept's node functions are plain sync functions.

## Choosing a model, backend, and session

`run_mcp_client_demo` accepts an optional `model` **query parameter**
(`?model=...`): `"llama3.2"` (default) or `"gemma4"`.

`run_mcp_agent_demo` additionally accepts `memory_backend` and
`session_id` — but **only `memory_backend=memory` is actually supported**
(see Gotchas below).

## Local infra prerequisites

`scripts/start_mcp_server.sh` (port `18383`) — both endpoints return a
`503` with a message telling you to start it, rather than a raw `500`, if
it isn't running.

## How to call it

```bash
# Single-node, stateless.
curl -s -X POST localhost:18282/langgraph/mcp \
  -H 'Content-Type: application/json' -d '{"question": "what is 100 divided by 4?"}'

# Agent, memory-backed. session_id carries context across calls.
curl -s -X POST "localhost:18282/langgraph/mcp/agent?session_id=demo" \
  -H 'Content-Type: application/json' -d '{"question": "what is 3+4?"}'
curl -s -X POST "localhost:18282/langgraph/mcp/agent?session_id=demo" \
  -H 'Content-Type: application/json' -d '{"question": "what happens when I add 5 to it?"}'
```

## Gotchas

- Same as `docs/langchain/09-mcp-client.md`: a tool call that raises is
  caught and fed back to the model as the tool's result string, not left
  to crash the request.
- Both `create_graph_cache()` and `create_mcp_agent_cache()` cache only
  the *compiled graph*, not the fetched tool list — `call_mcp_tools`,
  `call_model`, and `call_tools` all re-fetch tools from the MCP server
  on every node execution, so a change to `mcp_server/tools.py` (after
  restarting the MCP server) is picked up without needing to restart the
  FastAPI app or clear any cache here. This is unlike
  `langchain_demo/mcp_client.py`'s `create_react_agent`-based agent,
  where tools ARE baked in at compile time (required by that prebuilt) —
  one benefit of the hand-built graph here.
- **A repeated tool call is cheap, not eliminated.**
  `_find_prior_tool_result`'s cache means a duplicate `adder(4, 5)`
  request doesn't re-invoke the real MCP tool, but the model can still
  *ask* for it several times in a row, and each ask still consumes one
  graph step — verified live: a 3-turn gemma4 conversation ending in a
  question needing 2 new tool calls sometimes needed 4-6 total tool-call
  steps in that final turn (extra ones all served from cache) before
  converging on the correct answer. `_AGENT_RECURSION_LIMIT = 20` (raised
  from an initial `15` once the cache was added — a wasted step is now
  just one extra LLM call, not a real tool re-invocation) is the backstop
  for cases that don't converge in time; hitting it raises
  `GraphRecursionError` → `500`, not the connectivity `503`.
- **`memory_backend=redis`/`postgres` raise a clean `400`, not
  `NotImplementedError`.** `run_mcp_agent_demo` is invoked via
  `.ainvoke()` (MCP calls are async), but `checkpointers.py`'s
  redis/postgres builders return `langgraph.checkpoint.redis.RedisSaver` /
  `langgraph.checkpoint.postgres.PostgresSaver` — sync-only checkpointers
  that don't implement the async checkpoint interface `.ainvoke()`
  requires. Verified directly: calling `.ainvoke()` with one raises a bare
  `NotImplementedError` from `BaseCheckpointSaver.aget_tuple`. Async-capable
  equivalents exist (`langgraph.checkpoint.redis.AsyncRedisSaver`,
  `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver`) but aren't wired
  up here — `run_mcp_agent_demo` raises a clear `ValueError` (→ `400`)
  instead of letting that `NotImplementedError` leak through. Only
  `memory_backend=memory` works for this specific concept; `/langchain/agents`,
  `/langgraph/persistence`, and `/langgraph/interrupts` are unaffected —
  they're all sync (`.invoke()`), where the sync checkpointers work fine.
