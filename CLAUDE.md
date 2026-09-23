# ai_tutorial — Architecture & Conventions

A FastAPI app teaching LangChain and LangGraph concepts against local
Ollama models, one concept per file, one router per concept. LangChain
concepts live in `langchain_demo/`, mounted under `/langchain/**`.
LangGraph concepts live in a sibling package, `langgraph_demo/`, mounted
under `/langgraph/**` — see `docs/langgraph/00-overview.md` for why
they're deliberately separate packages rather than one.

## Architecture map

- `tools/` — pure-function library (math, string, datetime, list,
  conversion, geometry, web search). Top-level, shared, not tied to
  LangChain. Each function's docstring is written for LLM tool-calling
  (see convention below) — this is the source tool definitions for
  `langchain_demo/tool_calling.py` and `langchain_demo/react_agent.py`.
- `models/` — LLM/embedding singleton instances (`models/chat_models/`,
  `models/embedding_models/`), plus `models/model_utils.py` (the
  `fetch_all_models` factory) and `models/chat_models/ollama_models.py`'s
  `SupportedModel` enum + `get_chat_model` fetcher. Top-level, shared.
- `mcp_server/` — this project's own MCP server: `server.py` builds the
  `FastMCP` instance, `tools.py`/`prompts.py`/`resources.py` register a
  curated `tools/*.py` subset (via `mcp.add_tool(fn)`) plus one
  `@mcp.tool()`-decorated, MCP-only tool (`server_uptime_seconds`), one
  prompt, and two resources onto it. Top-level, shared (like
  `tools/`/`models/`) since both `langchain_demo/` and `langgraph_demo/`
  connect to it. `run_mcp_server.py` (project root) is the thin entry
  point that runs it — see `docs/mcp-server.md` for the full design,
  including why it's not named `mcp.py` (shadows the
  installed `mcp` package).
- `employee_mcp_server/` — a **second, independent** MCP server (CRUD on
  an in-memory Employee record: id/name/department/dob/salary/phone/email).
  Same three-layer shape as `mcp_server/` (`server.py`/`tools.py` +
  `store.py` for the domain logic), but deliberately NOT shared
  infrastructure like `tools/`/`models/`/`mcp_server/` — its own process,
  own port (`EMPLOYEE_MCP_SERVER_PORT`, default `18384`), own data,
  nothing imported by `langchain_demo/`/`langgraph_demo/`. Exists to
  demonstrate `MultiServerMCPClient` connecting to more than one MCP
  server (it's keyed by server name, not a single URL) — see
  `docs/employee-mcp-server.md`, including the "What's not built yet"
  section: no `langchain_demo`/`langgraph_demo` client concept connects
  to it yet, that would be a separate, later change.
- `langchain_demo/` — one file per LangChain concept. Framework-agnostic:
  plain functions returning dicts/Pydantic models/async generators. Never
  imports FastAPI. Memory and Agents are both partial exceptions to "one
  file per concept": `memory_conversation.py` is the entry point (and
  owns the `MemoryBackend` enum + in-memory closure),
  `memory_conversation_redis.py`/`memory_conversation_postgres.py` hold
  the other two backends' storage-specific code. `react_agent.py` is the
  entry point (owns `AgentMemoryBackend` + the in-memory closure),
  `react_agent_redis.py`/`react_agent_postgres.py` hold the other two
  checkpointer backends' setup code. Both mirror `rag_demo.py`'s
  multi-backend pattern, but as separate files per backend instead of one
  file with branching.
- `langgraph_demo/` — one file per LangGraph concept (StateGraph basics,
  branching, cycles, streaming, interrupts, persistence, multi-agent),
  same framework-agnostic rule as `langchain_demo/`. `persistence.py` and
  `interrupts.py` are the two concepts needing a checkpointer; they share
  `langgraph_demo/checkpointers.py`'s Redis/Postgres/memory builders
  rather than each getting their own backend-file pair — see that file's
  docstring for why this differs from `langchain_demo`'s per-concept
  split. `langgraph_demo/rag/` is the one concept big enough to be a
  sub-package rather than a file: `state.py` (per-sub-graph `TypedDict`s),
  `cohere_client.py` (rerank + LLM-judge eval), `graph.py` (the parent
  graph), plus three submodules —
  `sub_graphs/` (`query_rewriter.py`/`retriever.py`/`generator.py`, each a
  standalone compiled `StateGraph`), `history_stores/` and
  `vector_stores/` (the `memory`/`redis`/`postgres` backend selectors —
  see `docs/langgraph/08-rag.md` for the full design and diagrams, and
  that doc's "Customizable backends" section for why history stores get
  fresh per-backend files while vector stores are one wholesale re-export
  from `langchain_demo.rag_demo`).
- `controllers/` — one FastAPI router per concept, thin: request/response
  Pydantic models + calling into `langchain_demo`/`langgraph_demo` +
  shaping the response. No LangChain/LangGraph logic lives here.
  `langgraph_*_controller.py` naming distinguishes LangGraph concepts'
  controllers from the unprefixed LangChain ones.
- `main.py` — mounts `controllers.router` via a single `app.include_router(...)`
  call, plus the original two demo routes (`/`, `/hello/{name}`).

## Established conventions — preserve these

- **`tools/*.py` docstrings**: module docstring + per-function (1) one-line
  summary, (2) a "Call this tool for..." paragraph listing natural-language
  trigger phrases (and explicitly routing away to a different tool when one
  fits better), (3) a "Few-shot examples (phrase -> tool call):" block. Any
  new tool must follow this — it's what makes tool-calling/agent demos work.
- **`models/*` LLM/embedding instances are plain module-level singletons**
  (e.g. `llama3_2_llm`, `gemma4_llm`, `qwen3_embedding_model`) — never
  constructed inside a function. The one exception is fetching *which*
  chat model to use: since every concept now accepts a `model` request
  param, `models/chat_models/ollama_models.py` exposes `get_chat_model`,
  built once via `models/model_utils.py`'s `fetch_all_models([...])`
  (same closure-factory shape as `langchain_demo/tool_utils.py`'s
  `create_tool_caller`) — concept files call `get_chat_model(model)` to
  resolve the request's chosen model instead of an if/elif chain or a
  new accessor per model. Don't hardcode a specific `*_llm` inside a
  concept function; go through `get_chat_model`.
- **New chat model = one place to register it**: instantiate it in
  `models/chat_models/ollama_models.py`, add it to the `SupportedModel`
  enum (value must equal Ollama's `.model` tag, e.g. `"gemma4"`), and add
  it to the list passed to `fetch_all_models([...])`. No other file needs
  to change — every concept/controller already resolves models through
  `get_chat_model`/the `SupportedModel` enum.
- **`langchain_demo/*.py` and `langgraph_demo/*.py` stay FastAPI-free** —
  testable/importable outside the web layer.
- **Closures encapsulate private mutable state; plain dicts are fine for
  static registries.** This project deliberately uses the same
  build-once-return-a-closure shape in several places —
  `tool_utils.create_tool_caller`, `model_utils.fetch_all_models`,
  `memory_conversation.create_memory_history_store`,
  `memory_conversation_redis.create_history_cache`,
  `react_agent.create_agent_cache`, and every `langgraph_demo/*.py`
  concept's `create_graph_cache()` — each one wraps a private dict that
  only the returned function(s) can reach, so unrelated code can't mutate
  it directly (stronger than "please don't touch this module-level
  name"). `memory_conversation.py` and `react_agent.py` both keep the
  **non-closure version commented out directly above** the closure
  version specifically so both are visible side by side — don't delete
  those comment blocks when editing either file; extend them if you
  change the closure version's behavior. Conversely, `_HISTORY_PROVIDERS`
  (in `memory_conversation.py`) and `_CHECKPOINTER_BUILDERS` (in
  `react_agent.py`) are deliberately plain `{backend: function}` dicts,
  not closures — they're static lookup tables with nothing to protect, so
  wrapping either in a closure would be indirection with no payoff. Don't
  "fix" them into one.
- **Sync vs async route handlers**: LangChain concepts 1–6's controllers
  use plain `def` handlers (blocking `.invoke()` calls dispatch to
  FastAPI's threadpool automatically); `rag` and `streaming` use
  `async def` (their `langchain_demo` functions are already async). All
  seven `langgraph_*_controller.py` files use plain `def` too — every
  `langgraph_demo/*.py` concept is sync (`graph.invoke(...)`) — **except**
  `langgraph_streaming_controller.py`, which is `async def` since
  `streaming_graph.py`'s `stream_stategraph_demo` is an async generator
  (`graph.astream(...)`), `langgraph_rag_controller.py`, which is
  `async def` since `rag/graph.py`'s `run_rag_demo` calls the `retriever`
  sub-graph's `.ainvoke()` (its `retrieve` node is async, to support the
  Postgres vector backend's async driver), and `langgraph_mcp_controller.py`,
  which is `async def` since `mcp_client.py`'s single node awaits the MCP
  client. `mcp_client_controller.py` (LangChain side) is likewise
  `async def` for the same reason — every one of its three route
  functions awaits `langchain_demo/mcp_client.py`'s `MultiServerMCPClient`
  calls.
- **`.env` holds no real secrets** — it's committed to git, and it is the
  single source of truth for every variable name the app/infra uses
  (including for deployment: grep it for `${` to get the exact list of
  external vars a deployment must supply). Only genuinely sensitive values
  (passwords, API keys) are indirected to an external environment variable
  instead of hardcoded, e.g. `POSTGRES_APP_PASSWORD=${RAG_DEMO_PG_APP_PASSWORD:-}`.
  Non-secret config — including usernames like `POSTGRES_APP_USER` — stays
  a plain committed value; don't indirect something just because it's
  *related* to a secret. Always use the `:-` empty-default form on anything
  indirected so plain `source .env` under `set -u` never crashes when the
  external var isn't set. `scripts/lib/env.sh`'s `resolve_env()` is what
  actually resolves/prompts-for these — see below. Loaded via
  `python-dotenv`'s `load_dotenv()` in code (see `tools/search_tools.py`,
  `langchain_demo/rag_demo.py`).

## Adding a 10th concept

1. `langchain_demo/<slug>.py` — the concept function(s). Accept
   `model: SupportedModel = SupportedModel.llama3_2` and call
   `get_chat_model(model)` — never hardcode a `*_llm` instance.
2. `controllers/<slug>_controller.py` — an `APIRouter` with `prefix="/langchain/<slug>"`.
   The route function needs a `model: SupportedModel = SupportedModel.llama3_2`
   parameter **alongside** the body `payload` param, NOT a field inside the
   Pydantic body model — FastAPI treats a plain (non-BaseModel) parameter as
   a query param automatically, which is the point: `model` (and, for the
   prompts endpoint, `structured_output`) are `?model=...`/`?structured_output=...`
   query params, never JSON body fields. Every route function also needs a
   one-line docstring — `"""Calls \`langchain_demo.<slug>.<function_name>\`."""` —
   FastAPI surfaces this as the OpenAPI `description`, so `/docs` (Swagger UI)
   always shows exactly which source function an endpoint traces to.
3. Add it to the tuple in `controllers/__init__.py`.
4. `docs/langchain/<NN>-<slug>.md` — concept explanation, code walkthrough,
   infra prerequisites, curl example, gotchas.
5. A row in `README.md`'s endpoint table.
6. A section in `docs/TESTING.md` — at least one deliberately-chosen input
   value plus a "why this input demonstrates the concept" note (not just a
   smoke-test curl). This is the file a new person is pointed at first.

Never add ad hoc routes directly in `main.py`.

## Adding a 10th LangGraph concept

Same shape as above, in the sibling package:

1. `langgraph_demo/<slug>.py` — build the graph in a `_build_graph(model)`
   (or `_build_graph(model, memory_backend)` if it needs a checkpointer)
   function, cache compiled graphs per model/backend via a
   `create_graph_cache()` closure (see `stategraph_basics.py` for the
   simplest example), and expose a plain `run_<slug>_demo(...)` entry
   point. If it needs persistence, use `langgraph_demo/checkpointers.py`'s
   `build_checkpointer(memory_backend)` rather than adding a new
   redis/postgres file pair.
2. `controllers/langgraph_<slug>_controller.py` — same query-param and
   docstring conventions as LangChain controllers, prefix
   `"/langgraph/<slug>"`.
3. Add it to the tuple in `controllers/__init__.py`.
4. `docs/langgraph/<NN>-<slug>.md`, matching the LangChain doc page shape.
5. A row in both `README.md`'s LangGraph table and
   `docs/langgraph/00-overview.md`'s concept table.
6. A section in `docs/TESTING.md`.

## Infra dependencies

- RAG's `redis`/`postgres` backends AND the Memory concept's
  `redis`/`postgres` `memory_backend` options share the same
  `scripts/start_infra.sh` infra (`docker compose up -d`; services in
  root `docker-compose.yml`). Both concepts' `memory` backend/option
  needs nothing extra. Note the naming collision: "RAG's `memory`
  backend" and "the Memory concept's `memory_backend=memory`" are
  unrelated features that happen to share the word "memory" — don't
  conflate them when reading code/docs.
- Memory's Postgres backend (`memory_conversation_postgres.py`) uses its
  own table (`ai_tutorial_chat_history`), separate from RAG's
  `ai_tutorial_rag_chunks`; Memory's Redis backend
  (`memory_conversation_redis.py`) uses its own key prefix
  (`ai_tutorial_memory:`) and search index (`idx:chat_history`), separate
  from RAG's `ai_tutorial_rag` index. Both self-provision on first use —
  no docker-compose/init-script changes needed for either.
- Agents' `redis`/`postgres` `memory_backend` options share the same
  infra too. `react_agent_postgres.py`'s `PostgresSaver` and
  `react_agent_redis.py`'s `RedisSaver` each self-provision their own
  tables/indexes via `.setup()` — separate from both RAG's and Memory's
  tables/indexes. Four unrelated features (RAG, Memory, Agents,
  `langgraph_demo`'s `persistence.py`/`interrupts.py`) now each have their
  own `redis`/`postgres` backend option, all sharing one
  `docker-compose.yml` — don't assume "the redis backend" or "the
  postgres backend" without checking which concept's docs you're reading.
- **Exception to the above**: `langgraph_demo/checkpointers.py`'s
  Postgres checkpointer and `langchain_demo/react_agent_postgres.py`'s
  DO share physical tables (`checkpoints`, `checkpoint_writes`, etc.) —
  `PostgresSaver`'s table names are fixed, not parameterized. This is
  normal/intended (LangGraph expects one shared checkpoint schema per
  app); isolation between the two concepts' threads comes from using
  distinct `thread_id`s, not distinct tables. Same idea for
  `checkpointers.py`'s Redis checkpointer, which uses its own
  `ai_tutorial_langgraph_checkpoint` prefix (distinct from
  `react_agent_redis.py`'s `ai_tutorial_agent_checkpoint`).
- Postgres's `vector` extension (`docker/postgres/init/001-enable-pgvector.sql`)
  and the app user role (`docker/postgres/init/002-create-app-user.sh`) only
  run against a **fresh** volume — `scripts/stop_infra.sh --remove-volume`
  (then `scripts/start_infra.sh`) if either ever needs to re-run; this is
  the sanctioned way to do `docker compose down -v` for this project's
  infra, not raw `docker compose` commands.
- Postgres has a **root/app user split**: `POSTGRES_ROOT_USER`/`_PASSWORD`
  only bootstrap the container; the app connects as `POSTGRES_APP_USER`/
  `_PASSWORD` (a least-privilege role created by the init script). Never
  point `langchain_demo/rag_demo.py`'s `_get_pg_engine()` at the root
  credentials. The usernames themselves (`ai_tutorial_root`/`ai_tutorial_app`)
  are plain values in `.env` — only the two passwords are indirected/secret.
- Don't hand-write the pgvector table DDL — `langchain-postgres`'s
  `PGEngine.ainit_vectorstore_table(...)` owns that schema (see
  `langchain_demo/rag_demo.py` and `docs/langchain/07-rag/03-postgres-backend.md`).
- `ainit_vectorstore_table`/`aapply_vector_index` raise if the table/index
  already exist — `rag_demo.py` catches and ignores that specific case so
  repeated app starts against an already-provisioned database are safe.

## Secrets flow (`scripts/lib/env.sh`)

- `.env` indirects only genuinely sensitive values to an external var (see
  above). `resolve_env()` finds each `${EXTERNAL_VAR}` reference, loads any
  previously-answered values from gitignored `.env.local`, prompts
  (masked, if the name matches `*PASSWORD*`/`*SECRET*`/`*KEY*`) for
  anything still unset, appends new answers to `.env.local`, then sources
  `.env` so the indirected keys resolve.
- Called by `scripts/start_app.sh` and `scripts/start_infra.sh` only — `stop*`/
  `status*` scripts don't need secrets and shouldn't call it.
- **`.env.local` is a local-dev convenience cache, not a deployment
  artifact and not the source of truth for what variables exist.** `.env`
  (committed) already documents every required variable name via its
  `${EXTERNAL_VAR}` references — deleting `.env.local` or cloning fresh
  loses no information about *what* must be supplied, only the cached
  *values*. A real deployment supplies the same external var names
  (`RAG_DEMO_PG_ROOT_PASSWORD`, etc.) via whatever secret mechanism that
  platform uses (k8s secrets, CI secret store, ...) — it does not read
  `.env.local`.
- Never add a new secret as a plain `KEY=value` in `.env` — always indirect
  it (`KEY=${SOME_EXTERNAL_NAME:-}`). But don't indirect non-secret config
  (usernames, hostnames, ports) just because it sits next to a secret —
  only passwords/API keys/tokens need this treatment.

## What must not break

- `main.py` must stay directly runnable via `uv run uvicorn main:app`
  (PyCharm's existing "Python.FastAPI" run config depends on this, and has
  no `ENV_FILES` configured — it relies on `python-dotenv`/shell `source .env`).
  Running this way bypasses `resolve_env()`'s prompt, so it only works if
  the required external vars are already exported or `.env.local` already
  has them (e.g. after running `scripts/start_app.sh` once).
- `scripts/start_app.sh|stop_app.sh|status_app.sh`,
  `scripts/start_infra.sh|stop_infra.sh|status_infra.sh`,
  `scripts/start_mcp_server.sh|stop_mcp_server.sh|status_mcp_server.sh`, and
  `scripts/start_employee_mcp_server.sh|stop_employee_mcp_server.sh|status_employee_mcp_server.sh`
  must keep working unmodified.
- `tools/`, `models/`, and `mcp_server/` must stay top-level (not nested
  under `langchain_demo/` or `langgraph_demo/`) — all three are
  intentionally shared/reused as-is by both packages. `employee_mcp_server/`
  is also top-level, but for a different reason (see the architecture map
  above) — it's a standalone second server, not shared infrastructure.
- The root entry point for the MCP server must never be named `mcp.py` —
  verified this shadows the installed `mcp` PyPI package and breaks every
  `from mcp.server...` import in the project. It's `run_mcp_server.py`
  (and, for the employee MCP server, `run_employee_mcp_server.py`).
- `langgraph_demo/branching.py` and `langgraph_demo/multi_agent.py` both
  import `langchain_demo.tool_utils.create_tool_caller`, and
  `langgraph_demo/mcp_client.py` imports
  `langchain_demo.react_agent.AGENT_SYSTEM_PROMPT` — these cross-package
  imports are intentional (genuinely generic utilities, same status as
  importing from `models/`), unlike the checkpointer/persistence code
  which was deliberately *not* shared across packages that way (each
  package keeps its own `AgentMemoryBackend`/`CheckpointBackend` and
  redis/postgres builders).
- `.env` must never regain a hardcoded secret — indirection is the point.
- `.claude/skills/app-lifecycle/`, `.claude/skills/infra-lifecycle/`,
  `.claude/skills/mcp-server-lifecycle/`, and
  `.claude/skills/employee-mcp-server-lifecycle/`, plus
  `.claude/commands/app.md`/`infra.md`/`mcp.md`/`employee-mcp.md`, are
  project-level (committed, travel with the repo). They reference the
  twelve lifecycle scripts by their current names — if a script is ever
  renamed again, update these too.

## Verified facts (don't "fix" these again)

- `gemma4` and `qwen3-embedding` are real, pullable Ollama model tags — not
  typos.
- `qwen3_embedding_model` (in `models/embedding_models/ollama_models.py`) is
  pinned to the **`0.6b`** tag specifically (1024-dim output), not a larger
  one — pgvector's HNSW index has a hard 2000-dimension limit, and larger
  tags (e.g. `4b` → 2560 dims) exceed it and fail index creation.
- `langchain_demo/prompts_and_parsers.py`'s `run_pydantic_parser_demo` binds
  the model with `format="json"` — without it, small local models
  occasionally emit syntactically malformed JSON that the parser can't
  recover from.
- `langchain_demo/tool_utils.py`'s `create_tool_caller` catches exceptions
  raised by the invoked tool and returns them as a string result instead of
  letting them propagate. Without this, `tool_calling.py`'s endpoint 500s
  whenever the model calls `web_search` without Google credentials
  configured (a common occurrence for ordinary general-knowledge
  questions) — don't remove this try/except.
- RAG ingestion uses stable, content-derived chunk ids (`uuid.uuid5(uuid.NAMESPACE_URL, chunk)`)
  and passes them explicitly per backend (`ids=` for Postgres, `keys=` for
  Redis, auto-detected `Document.id` for the in-memory store) so
  re-ingestion upserts instead of duplicating rows/keys across app restarts.
- `gemma4`'s streaming output (`/langchain/streaming?model=gemma4`)
  legitimately includes many empty-string chunks
  interleaved with real ones (verified: real emoji/word tokens are still
  there if you don't truncate the output) — not a bug in
  `streaming_demo.py`, just how `ChatOllama.astream()` tokenizes this
  model's output.
- `langchain_demo/react_agent.py` caches one compiled agent graph per
  `(model, memory_backend)` pair via `create_agent_cache()`'s closure
  rather than rebuilding `create_react_agent(...)` on every request —
  don't remove this cache when adding more models/backends.
- `react_agent_postgres.py`'s psycopg connection must be opened with
  `autocommit=True, prepare_threshold=0, row_factory=dict_row` — this is
  the exact configuration `PostgresSaver.from_conn_string` uses
  internally; `PostgresSaver`'s cursor/migration code assumes an
  autocommit connection and never calls `.commit()` itself.
- Postgres-backed agent memory (`memory_backend=postgres`) was verified
  to survive a full `scripts/stop_app.sh && scripts/start_app.sh` restart
  — the checkpoint really is persisted, not just cached in the process.
- `memory_conversation_redis.py`'s `RedisChatMessageHistory(..., overwrite_index=True)`
  is a required workaround for a real bug in the installed
  `langchain_redis==0.2.5`: constructing it when the search index already
  exists crashes (`AttributeError: 'dict' object has no attribute
  'index'`) unless that flag is set — don't remove it as "seems
  unnecessary." Per-session caching in `create_history_cache()` is
  equally required: without it, `overwrite_index=True` on every call
  re-triggers a background reindex that races reads and returns an
  incomplete message list — verified live (a 4-message history came back
  as 1 message without the cache).
- `memory_conversation_postgres.py` hashes session ids with
  `uuid.uuid5(uuid.NAMESPACE_URL, session_id)` before passing them to
  `PostgresChatMessageHistory` — its backing table's `session_id` column
  is `UUID`-typed, but this concept accepts arbitrary string session ids
  everywhere else.
- `langgraph_demo/interrupts.py`'s `resume_approval_demo` checks
  `graph.get_state(config).next` before calling
  `graph.invoke(Command(resume=...), config)` — without this check, a
  `session_id`/`model`/`memory_backend` combination with no pending
  interrupt (most commonly a `model`/`memory_backend` mismatch between
  the `/start` and `/resume` calls) raises a raw `KeyError` deep inside
  LangGraph's executor. `resume_approval_demo` raises a clear `ValueError`
  instead, which `langgraph_interrupts_controller.py` turns into a `400` —
  verified live (mismatched `model` between start/resume used to 500,
  now returns a clean 400 with an explanatory message).
- `langgraph_demo/persistence.py`'s `run_persistence_demo` invokes with
  an **empty dict**, not `{"count": 0, "history": []}` — passing explicit
  initial values would overwrite the checkpointed state back to its
  starting point on every call instead of accumulating. The node reads
  `state.get("count", 0)` so a brand-new thread still defaults correctly.
- `langgraph_demo/cycles.py`'s retry loop feeds the *previous* attempt's
  text and word count back into the next attempt's prompt — without this
  feedback, llama3.2 doesn't reliably converge on a stricter word limit
  even after several retries (verified: the version without feedback
  used all `max_attempts` and still failed on some topics; the version
  with feedback converges in 1 attempt on the same topics).
- `mcp_server/tools.py`'s `mcp.add_tool(fn)` correctly builds a JSON
  schema from `tools/math_tools.py`'s `int | float` union parameter
  types with no changes needed to those functions — verified live via
  the MCP server's actual tool list, not assumed from docs.
- `mcp_server/tools.py`'s `@mcp.tool()`-decorated `server_uptime_seconds`
  (an MCP-only tool with no `tools/*.py` counterpart) builds and invokes
  identically to the `mcp.add_tool(fn)`-registered tools from a client's
  point of view — verified live via `/langchain/mcp/tool-calling` with
  "how long has the MCP server been running?", which correctly called
  `server_uptime_seconds()` and got a real elapsed-seconds result back.
- `employee_mcp_server/`'s full CRUD cycle (create/get/update/list/delete)
  was verified live end-to-end via a direct `MultiServerMCPClient`
  connection to `http://localhost:18384/mcp` — including that
  `update_employee`'s partial-update semantics (only non-`None` args
  change) work correctly, and that a post-delete `get_employee` call
  surfaces the raised `ValueError` as clean error text rather than a raw
  exception. No FastAPI endpoint exercises this server yet, so this
  direct-client script (see `docs/employee-mcp-server.md`'s "Verifying
  it works") is the only verification path until one exists.
- `langchain_demo/mcp_client.py` and `langgraph_demo/mcp_client.py`
  connect to the MCP server unreachable-safely: `MultiServerMCPClient(...)`
  never raises at construction time (no connection happens until
  `get_tools()`/`get_prompt()`/`get_resources()` is actually called), and
  when the server IS down, the underlying failure surfaces as a generic
  `ExceptionGroup` (not a specific catchable type) — both controllers
  catch broadly and return a `503` pointing at
  `scripts/start_mcp_server.sh`, verified live to no longer 500.
- `langchain_demo/mcp_client.py`'s `run_mcp_agent_demo` originally
  shipped stateless (no `session_id`) — fixed by giving it the same
  `session_id`/`memory_backend` shape as `react_agent.py`'s
  `run_agent_demo` (reusing that file's `AgentMemoryBackend` and
  redis/postgres checkpointer builders directly). This alone was **not**
  sufficient, and don't re-diagnose it as the fix: with `session_id`
  correctly wired and gemma4 correctly recalling the previous turn's
  result, `create_react_agent`'s default ReAct loop was still verified
  live to re-call a tool with IDENTICAL arguments over a dozen times
  after already getting the correct result, before finally emitting a
  plain-text final message (`react_agent.py`, `/langchain/agents`,
  `session_id=ses123`, gemma4, "what is 3+4?" then "what happens when I
  add 5 to it?" — `steps` showed `adder(7, 5)` repeated ~14 times). The
  real fix is `react_agent.py`'s `AGENT_SYSTEM_PROMPT` — an explicit
  "respond directly once you have the answer; never repeat an identical
  tool call" instruction passed as `create_react_agent(..., prompt=...)`
  — verified live to bring the same two-turn conversation down to
  exactly one `adder` call per turn, reproduced clean across 3 separate
  sessions. `AGENT_SYSTEM_PROMPT` is deliberately public (not
  underscore-prefixed) and reused verbatim by `langchain_demo/mcp_client.py`'s
  `run_mcp_agent_demo` too (both it and `react_agent.py` go through
  `langgraph.prebuilt.create_react_agent`) — don't let them drift into
  separately-maintained copies of the same instruction. Both agents also
  pass an explicit `recursion_limit=15` (instead of LangGraph's default
  25) as a backstop in case the prompt instruction ever doesn't hold for
  some input — `agents_controller.py` and
  `controllers/mcp_client_controller.py`'s `_agent_error` both catch
  `GraphRecursionError` and report it distinctly from an unreachable MCP
  server, since folding it into the generic connectivity-error handling
  would mislabel a stuck agent as a down server.
- `langgraph_demo/mcp_client.py`'s `run_mcp_agent_demo` does NOT use
  `create_react_agent` — deliberately hand-built as an explicit two-node
  `StateGraph` (`call_model` <-> `call_tools`, using the core
  `langgraph.graph.MessagesState` primitive) instead, since a
  `langgraph_demo` concept should show the reason/act loop itself, not
  hide it behind a prebuilt (same reasoning `multi_agent.py` already
  gives for hand-building over relying on a prebuilt agent). This was a
  deliberate correction — an earlier version of this function did use
  `create_react_agent`; don't reintroduce it here. Building the loop by
  hand enabled a fix a prebuilt can't easily offer:
  `_find_prior_tool_result` checks accumulated message history for a
  tool already called with identical name/args and reuses that result
  instead of re-invoking the tool — verified live (repeated calls return
  the identical cached MCP response object, not a fresh one). This makes
  a repeat *cheap*, but doesn't stop the model from *asking* again, so
  `_AGENT_RECURSION_LIMIT` was raised to `20` (from `15`) once this cache
  existed — a wasted step is now one extra LLM call, not a real tool
  re-invocation. Reuses `AGENT_SYSTEM_PROMPT` from
  `langchain_demo.react_agent` still (see "must not break" above), but
  NOT `create_react_agent` itself.
  Only supports `memory_backend=memory` — verified live that
  `memory_backend=redis`/`postgres` raise a bare `NotImplementedError`
  from `BaseCheckpointSaver.aget_tuple`, because this graph is invoked
  via `.ainvoke()` (MCP calls are async) but
  `langgraph_demo/checkpointers.py`'s `RedisSaver`/`PostgresSaver`
  builders are sync-only and don't implement the async checkpoint
  interface. Async-capable classes exist
  (`langgraph.checkpoint.redis.AsyncRedisSaver`,
  `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver`) but aren't
  wired up — don't add them to `checkpointers.py` casually; that file's
  builders are shared with `persistence.py`/`interrupts.py`, which are
  sync (`.invoke()`) and must keep working unmodified. `run_mcp_agent_demo`
  raises a clear `ValueError` (→ `400` via `langgraph_mcp_controller.py`)
  for any backend other than `memory` instead of leaking the raw
  `NotImplementedError`.
- `langgraph_demo/mcp_client.py` importing
  `langchain_demo.react_agent.AGENT_SYSTEM_PROMPT` is intentional
  cross-package reuse of a small, genuinely generic instruction string —
  same category as `branching.py`/`multi_agent.py` importing
  `langchain_demo.tool_utils.create_tool_caller` (see "What must not
  break" above). It does NOT reuse `AgentMemoryBackend` or any
  redis/postgres checkpointer code from `langchain_demo` — those stay
  package-local per the existing split (`langgraph_demo` uses its own
  `checkpointers.py`).
