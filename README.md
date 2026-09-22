# ai_tutorial

A FastAPI application that teaches core LangChain and LangGraph concepts,
one endpoint per concept, running against local Ollama models — no
external LLM API keys required for the core demos.

## Prerequisites

- Python 3.13, [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com) installed and running locally, with these
  models pulled:
  ```bash
  ollama pull llama3.2
  ollama pull gemma4
  ollama pull qwen3-embedding:0.6b
  ```
- Docker + Docker Compose — only needed for the RAG concept's `redis` and
  `postgres` vector store backends (the `memory` backend needs nothing extra)
- Optional: Google Custom Search credentials in `.env` for the `web_search`
  tool used by the tool-calling/agents demos — see `tools/search_tools.py`

## Setup

```bash
uv sync
```

### Secrets and `.env`

`.env` is committed and holds **no real secrets** — it's also the single
source of truth for every variable name the app/infra uses. Non-sensitive
config (usernames, host/port, etc.) is a plain committed value; only
genuinely sensitive values (Postgres passwords, API keys) are indirected to
an external environment variable instead of hardcoded, e.g.:

```
POSTGRES_APP_PASSWORD=${RAG_DEMO_PG_APP_PASSWORD:-}
```

You never need to hand-edit these. `scripts/start_app.sh` and
`scripts/start_infra.sh` check every such indirection: if the external
variable isn't already set in your shell, they prompt for it once (input
is masked for anything password/secret/key-like) and save it to a
gitignored `.env.local` file, so you're only asked the first time. See
`scripts/lib/env.sh` for the mechanics.

`.env.local` is a **local-dev convenience only** — it's not a deployment
artifact, and it's not the source of truth for what variables exist. `.env`
already documents every required variable name (search it for `${` to get
the exact list); deleting `.env.local` or cloning fresh loses none of that
knowledge, only the cached secret values. A real deployment would supply
`RAG_DEMO_PG_ROOT_PASSWORD`/`RAG_DEMO_PG_APP_PASSWORD` via whatever secret
mechanism that platform uses instead.

### Local infra (RAG's `redis`/`postgres` backends)

```bash
scripts/start_infra.sh   # docker compose up -d, prompts for Postgres creds first run
scripts/status_infra.sh  # docker compose ps
scripts/stop_infra.sh    # docker compose down
```

The `memory` RAG backend needs none of this.

## Running the app

Via the provided scripts (backgrounds the process, tracks a PID/log file):

```bash
scripts/start_app.sh    # prompts for any missing Postgres creds first run, then starts the app
scripts/status_app.sh
scripts/stop_app.sh
```

Or directly (bypasses the prompt — export the required variables yourself
first, or run `scripts/start_app.sh` once so `.env.local` is populated):

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 18282
```

PyCharm's existing "Python.FastAPI" run configuration (targeting `main.py`)
also works unchanged, under the same caveat.

### Running the MCP server

The `/langchain/mcp/*` and `/langgraph/mcp` endpoints (see below) connect
to this project's own MCP server — a separate process, started the same
way:

```bash
scripts/start_mcp_server.sh    # port 18383 (MCP_SERVER_PORT in .env)
scripts/status_mcp_server.sh
scripts/stop_mcp_server.sh
```

See [docs/mcp-server.md](docs/mcp-server.md) for what it exposes (tools,
a prompt, two resources) and why it's `run_mcp_server.py` at the root, not
`mcp.py` (naming collision with the installed `mcp` package).

### Using Claude Code? Skip the scripts

This repo ships project-level Claude Code skills and slash commands (in
`.claude/`) that wrap the scripts above — they travel with the repo on
clone, so anyone opening this project in Claude Code gets them for free.

```
/app start | stop | status | restart      (or just ask: "start the app")
/infra start | stop | status | restart    (or just ask: "start the infra")
/mcp start | stop | status | restart      (or just ask: "start the mcp server")
```

## LangChain concepts and endpoints

| Concept | Endpoint | Docs |
|---|---|---|
| Prompts & Output Parsers | `POST /langchain/prompts`, `POST /langchain/prompts/structured` | [docs/langchain/01-prompts-and-parsers.md](docs/langchain/01-prompts-and-parsers.md) |
| LCEL Chains | `POST /langchain/chains/pipe`, `POST /langchain/chains/parallel` | [docs/langchain/02-lcel-chains.md](docs/langchain/02-lcel-chains.md) |
| Tool Calling | `POST /langchain/tool-calling` | [docs/langchain/03-tool-calling.md](docs/langchain/03-tool-calling.md) |
| Structured Output | `POST /langchain/structured-output` | [docs/langchain/04-structured-output.md](docs/langchain/04-structured-output.md) |
| Memory / Conversation | `POST/GET/DELETE /langchain/memory/{session_id}` | [docs/langchain/05-memory-conversation.md](docs/langchain/05-memory-conversation.md) |
| Agents (ReAct) | `POST /langchain/agents` | [docs/langchain/06-react-agents.md](docs/langchain/06-react-agents.md) |
| RAG | `POST /langchain/rag/ingest`, `POST /langchain/rag/query` | [docs/langchain/07-rag/00-overview.md](docs/langchain/07-rag/00-overview.md) |
| Streaming | `POST /langchain/streaming` | [docs/langchain/08-streaming.md](docs/langchain/08-streaming.md) |
| MCP client | `POST /langchain/mcp/tool-calling`, `POST /langchain/mcp/agent`, `POST /langchain/mcp/prompt`, `GET /langchain/mcp/resource` | [docs/langchain/09-mcp-client.md](docs/langchain/09-mcp-client.md) |

Each doc page has a full curl example. Quick start:

```bash
curl -s -X POST localhost:18282/langchain/prompts \
  -H 'Content-Type: application/json' -d '{"topic": "black holes"}'
```

### Choosing a model

Every endpoint above accepts an optional `model` **query parameter**
(`?model=...`, not a body field) — `"llama3.2"` (default) or `"gemma4"`.
Omit it to use the default, or pass it to compare how a different model
handles the same request:

```bash
curl -s -X POST "localhost:18282/langchain/prompts?model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "black holes"}'
```

An invalid value (anything other than the two above) gets rejected with a
`422` — see `models/chat_models/ollama_models.py`'s `SupportedModel` enum
for the source of truth. Adding a third model only requires changes there
(instantiate it, add it to the enum, add it to `fetch_all_models([...])`)
— every concept and controller already resolves models generically through
`get_chat_model(model)`, so nothing else needs to change.

## LangGraph concepts and endpoints

A second, sibling set of concepts demonstrates LangGraph itself (the
graph-orchestration layer LangChain's own prebuilt agent above is built
on), mounted under `/langgraph/**`:

| Concept | Endpoint | Docs |
|---|---|---|
| StateGraph basics | `POST /langgraph/stategraph` | [docs/langgraph/01-stategraph-basics.md](docs/langgraph/01-stategraph-basics.md) |
| Conditional edges / branching | `POST /langgraph/branching` | [docs/langgraph/02-branching.md](docs/langgraph/02-branching.md) |
| Cycles / loops | `POST /langgraph/cycles` | [docs/langgraph/03-cycles.md](docs/langgraph/03-cycles.md) |
| Streaming graph execution | `POST /langgraph/streaming` | [docs/langgraph/04-streaming-graph.md](docs/langgraph/04-streaming-graph.md) |
| Human-in-the-loop / interrupts | `POST /langgraph/interrupts/start`, `POST /langgraph/interrupts/resume` | [docs/langgraph/05-interrupts.md](docs/langgraph/05-interrupts.md) |
| Persistence / checkpointers | `POST /langgraph/persistence/{session_id}` | [docs/langgraph/06-persistence.md](docs/langgraph/06-persistence.md) |
| Multi-agent / subgraphs | `POST /langgraph/multi-agent` | [docs/langgraph/07-multi-agent.md](docs/langgraph/07-multi-agent.md) |
| RAG (query rewriter + retriever + generator sub-graphs) | `POST /langgraph/rag/{session_id}` | [docs/langgraph/08-rag.md](docs/langgraph/08-rag.md) |
| MCP client | `POST /langgraph/mcp`, `POST /langgraph/mcp/agent` | [docs/langgraph/09-mcp-client.md](docs/langgraph/09-mcp-client.md) |

Same `model` query parameter convention as above. `persistence` and
`interrupts` additionally accept `memory_backend` (`"memory"` default,
`"redis"`, or `"postgres"`) — same infra as the LangChain concepts'
Redis/Postgres options. `rag` additionally accepts `history_backend` and
`vector_backend` (each `"memory"` default, `"redis"`, or `"postgres"`,
chosen independently), plus three independent flags — `rewrite_eval`,
`rerank`, `generation_eval` (each `false` by default) — that need a
`COHERE_API_KEY` in `.env` only when turned on. See
[docs/langgraph/00-overview.md](docs/langgraph/00-overview.md) for how
this package relates to `langchain_demo/`.

**New to this repo?** See [docs/TESTING.md](docs/TESTING.md) — a curated
walkthrough of every concept with specific example inputs and an
explanation of *why* each one demonstrates the concept, so you can run
through it end-to-end and understand what's happening at each step.

**Prefer to learn by tinkering?** Every concept also has a Jupyter notebook —
[docs/langchain/jupyter/](docs/langchain/jupyter/) and
[docs/langgraph/jupyter/](docs/langgraph/jupyter/) — that builds it from
scratch in isolated, editable cells (not through the FastAPI app), ending in
a "🧪 Playground" section with starter experiments. No server needs to be
running except `scripts/start_mcp_server.sh` for the two `09-mcp-client.ipynb`
notebooks.

## Local infra for RAG

The RAG concept's `redis` and `postgres` backends need `scripts/start_infra.sh`
(services defined in `docker-compose.yml`); the `memory` backend needs
nothing. See [docs/langchain/07-rag/](docs/langchain/07-rag/) for backend-
specific details, including how the Postgres table is indexed and how the
Postgres root/app user split works.

## This project's own MCP server

The MCP client concepts (`/langchain/mcp/*`, `/langgraph/mcp`) connect to
an MCP server this same repo hosts, over streamable-http on port `18383`
(`MCP_SERVER_PORT` in `.env`) — a separate process from the main app, no
Docker needed. See [docs/mcp-server.md](docs/mcp-server.md) for what it
exposes and `scripts/start_mcp_server.sh`/`scripts/status_mcp_server.sh`/
`scripts/stop_mcp_server.sh` (or `/mcp start|status|stop`) to run it.

## Known gaps

- `test_main.http` still points at the stale port `8000` (the app now runs
  on `18282` — see `.env`'s `PORT`); not fixed here.
