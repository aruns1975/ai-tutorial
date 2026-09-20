# MCP (Model Context Protocol) Client, Inside a Graph

## Concept

The LangGraph-flavored counterpart to `docs/langchain/09-mcp-client.md`,
in two parts: a single-node `StateGraph` (`run_mcp_client_demo`) that calls
tools fetched from this project's own MCP server (`mcp_server/`, see
`docs/mcp-server.md`) instead of a locally-imported `tools/*.py` function,
and a memory-backed agent (`run_mcp_agent_demo`) that hands those same
tools to LangGraph's prebuilt `create_react_agent` with a checkpointer
attached. Once fetched, an MCP tool is just a LangChain `BaseTool`
regardless of which framework's execution model calls it — that's true for
both parts here, same as the LangChain-side concept.

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
def create_mcp_agent_cache():
    agents: dict[tuple[SupportedModel, CheckpointBackend], object] = {}

    async def get_agent(model, memory_backend):
        key = (model, memory_backend)
        if key not in agents:
            tools = await _client.get_tools(server_name=_SERVER_NAME)
            checkpointer = build_checkpointer(memory_backend)
            agents[key] = create_react_agent(
                get_chat_model(model), tools=tools, checkpointer=checkpointer, prompt=AGENT_SYSTEM_PROMPT
            )
        return agents[key]

    return get_agent
```

The LangGraph-native sibling of `langchain_demo/mcp_client.py`'s
`run_mcp_agent_demo`, and the `create_react_agent` counterpart to this
file's single-node `run_mcp_client_demo` — same relationship
`react_agent.py` has to `tool_calling.py`. Two deliberate reuse choices:

- **Checkpointer**: `langgraph_demo/checkpointers.py`'s
  `CheckpointBackend`/`build_checkpointer` — this package's own shared
  persistence story (used by `persistence.py`/`interrupts.py` too), *not*
  `langchain_demo.react_agent`'s `AgentMemoryBackend`/per-backend files.
  This is the deliberate cross-package split documented in the project
  root `CLAUDE.md` — each package keeps its own persistence story.
- **`AGENT_SYSTEM_PROMPT`**: imported directly from
  `langchain_demo.react_agent` — a small, genuinely generic instruction
  (not persistence logic), so it's reused rather than re-derived. Without
  it, `create_react_agent`'s default loop was found to re-call a tool with
  identical arguments many times after already having the answer — see
  `docs/langchain/06-react-agents.md`'s Gotchas for the original
  reproduction.

`session_id` is LangGraph's `thread_id`, same shape as
`langchain_demo/mcp_client.py`'s agent: omit it for a stateless
single-shot call, pass the same value across calls for multi-turn memory.

## Why both are `.ainvoke()`, not `.invoke()`

Both `call_mcp_tools` and `run_mcp_agent_demo`'s agent invocation are
async (they await the MCP client), so this is one of the few
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
- `run_mcp_client_demo`'s per-model cache (`create_graph_cache()`) caches
  the compiled graph, not the fetched tool list — tools are re-fetched
  from the MCP server on every invocation of `call_mcp_tools`, so a change
  to `mcp_server/tools.py` (after restarting the MCP server) is picked up
  without needing to restart the FastAPI app or clear any cache here.
  `run_mcp_agent_demo`'s cache works differently: tools ARE baked into the
  compiled agent at first use per `(model, memory_backend)` pair (required
  by `create_react_agent`), so a `mcp_server/tools.py` change needs a
  FastAPI app restart to be picked up there.
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
