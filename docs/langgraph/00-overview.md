# LangGraph Concepts — Overview

## Why a separate package from `langchain_demo`

`langchain_demo/` demonstrates LangChain primitives: prompts, chains,
tool calling, parsers. `langgraph_demo/` demonstrates LangGraph itself —
the graph-based orchestration layer LangChain's own prebuilt agent
(`langchain_demo/react_agent.py`) is built on top of. The two packages
are siblings for a reason: LangGraph concepts (state, nodes, edges,
cycles, interrupts, checkpointers) exist independently of any LangChain
chain and deserve their own uncluttered examples, mounted under a
separate `/langgraph/**` route prefix.

## Concepts

| Concept | File | Endpoint | Docs |
|---|---|---|---|
| StateGraph basics | `stategraph_basics.py` | `POST /langgraph/stategraph` | [01-stategraph-basics.md](01-stategraph-basics.md) |
| Conditional edges / branching | `branching.py` | `POST /langgraph/branching` | [02-branching.md](02-branching.md) |
| Cycles / loops | `cycles.py` | `POST /langgraph/cycles` | [03-cycles.md](03-cycles.md) |
| Streaming graph execution | `streaming_graph.py` | `POST /langgraph/streaming` | [04-streaming-graph.md](04-streaming-graph.md) |
| Human-in-the-loop / interrupts | `interrupts.py` | `POST /langgraph/interrupts/start`, `POST /langgraph/interrupts/resume` | [05-interrupts.md](05-interrupts.md) |
| Persistence / checkpointers | `persistence.py` | `POST /langgraph/persistence/{session_id}` | [06-persistence.md](06-persistence.md) |
| Multi-agent / subgraphs | `multi_agent.py` | `POST /langgraph/multi-agent` | [07-multi-agent.md](07-multi-agent.md) |
| RAG (query rewriter + retriever + generator sub-graphs) | `rag/` | `POST /langgraph/rag/{session_id}` | [08-rag.md](08-rag.md) |

Every concept file lives in `langgraph_demo/`; every endpoint is wired up
by a matching `controllers/langgraph_<slug>_controller.py`, following the
exact same architecture as the LangChain concepts (see the project root
`CLAUDE.md`).

## Shared infrastructure

- `langgraph_demo/checkpointers.py` — shared Redis/Postgres/in-memory
  checkpointer builders used by `persistence.py` and `interrupts.py` (the
  two concepts that need a checkpointer). Unlike `langchain_demo`'s
  per-concept backend file pairs, these two concepts share one
  persistence story, so their backend code lives in one file rather than
  being duplicated per concept — see that file's docstring for the full
  reasoning.
- Concepts needing a chat model all accept the same `model` query
  parameter as the LangChain concepts (`"llama3.2"` default or
  `"gemma4"`), resolved through the same `get_chat_model()` fetcher in
  `models/chat_models/ollama_models.py`.
- `persistence.py` and `interrupts.py` also accept `memory_backend`
  (`"memory"` default, `"redis"`, or `"postgres"`) — `redis`/`postgres`
  need `scripts/start_infra.sh`, the same infra every other concept's
  Redis/Postgres backend uses.

## Compare to the equivalent LangChain concepts

| LangGraph concept | Closest LangChain equivalent | The difference |
|---|---|---|
| StateGraph basics | `lcel_chains.py`'s pipe chain | A chain is a linear pipe; a graph is nodes + a shared, mutable state any node can read/write. |
| Streaming graph execution | `streaming_demo.py` | LangChain streams *tokens* from one call; a graph streams one *event per node* as it executes. |
| Persistence / checkpointers | `memory_conversation.py` | `RunnableWithMessageHistory` (used there) is deprecated upstream specifically in favor of LangGraph's checkpointers (used here). |
| Multi-agent / subgraphs | `react_agent.py`'s prebuilt agent | The prebuilt agent is one graph LangGraph ships for you; this concept hand-builds a small multi-graph system to show what's underneath it. |
| RAG sub-graphs | `rag_demo.py` | The LangChain version is one straight-line function; this concept decomposes the same pipeline into three independently-compiled, independently-testable sub-graphs (query rewriter, retriever, generator) stitched together by a parent graph. |
