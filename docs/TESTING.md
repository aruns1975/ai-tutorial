# Testing Guide — Try Every Concept

A curated set of test cases, one (or more) per LangChain concept. Every
input value below was **deliberately chosen** to make a specific concept
mechanic visible in the output — not just "does the endpoint respond."
Run them in order, read the "why this input" note, and you'll have
exercised (and understood) every concept this project demonstrates.

All outputs shown here are real, captured from an actual run against
`llama3.2` — small local models are not perfectly deterministic in
phrasing, so your wording will differ, but the *behavior* described will
reproduce.

**Every endpoint below also accepts an optional `model` query parameter**
(`?model=...`) — `"llama3.2"` (default, used when omitted) or `"gemma4"`.
It's a query param, not a JSON body field. None of the examples below pass
it explicitly unless the point is specifically to compare models (see
§0) — assume every request is implicitly against the default `llama3.2`
otherwise.

## Prerequisites

```bash
scripts/start_app.sh          # starts the app on :18282
scripts/start_infra.sh        # only needed for RAG's redis/postgres backends
scripts/start_mcp_server.sh   # only needed for §9/§18's MCP client concepts
```

---

## 0. Switching models — same request, different model

```bash
curl -s -X POST localhost:18282/langchain/prompts \
  -H 'Content-Type: application/json' -d '{"topic": "gravity"}'

curl -s -X POST "localhost:18282/langchain/prompts?model=gemma4" \
  -H 'Content-Type: application/json' -d '{"topic": "gravity"}'
```

**Why this input demonstrates the concept:** identical request, only the
`model` query param changes. In a real run, `gemma4`'s response comes back
noticeably different in style (markdown headers, emoji) from `llama3.2`'s
plainer prose — concrete proof `?model=...` actually routes to a different
underlying `ChatOllama` instance via `get_chat_model()`
(`models/chat_models/ollama_models.py`), not just a cosmetic parameter.
Try an invalid value, e.g. `?model=gpt-4`, and you'll get a `422` — `model`
is validated against the `SupportedModel` enum, not passed through
blindly.

---

## 1. Prompts & Output Parsers

### 1a. Same topic, different `style` — proves the prompt template actually drives the model's behavior

```bash
curl -s -X POST localhost:18282/langchain/prompts \
  -H 'Content-Type: application/json' \
  -d '{"topic": "gravity", "style": "like I am five years old"}'
```

Sample response (trimmed):
> "GRAVITY IS SO COOL! Gravity is like a big hug from the Earth! ..."

**Why this input demonstrates the concept:** the `style` field is
templated straight into the system prompt (see
`langchain_demo/prompts_and_parsers.py`). Changing it from the default
`"concise"` to `"like I am five years old"` produces a visibly different
register for the *same* topic — proof the template, not the topic alone,
shapes the answer.

### 1b. Toggle `structured_output` off — see exactly what `StrOutputParser` strips away

```bash
curl -s -X POST "localhost:18282/langchain/prompts?structured_output=false" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "gravity"}'
```

Sample response (trimmed):
```json
{
  "response": {
    "content": "Gravity is a fundamental force...",
    "response_metadata": {"model": "llama3.2", "eval_count": 176, "done_reason": "stop", ...},
    "usage_metadata": {"input_tokens": 42, "output_tokens": 176, "total_tokens": 218},
    "type": "ai", "tool_calls": [], ...
  }
}
```

**Why this input demonstrates the concept:** run this and 1a's default
request (`structured_output` omitted, defaults to `true`) side by side.
Same topic, same prompt — but `false` skips `StrOutputParser()` in the
chain entirely, so `response` is the raw `AIMessage` object (content
*plus* token counts, stop reason, model name) instead of a plain string.
That's the whole job of `StrOutputParser`: collapsing this object down to
just `.content`.

### 1c. Structured JSON extraction via `PydanticOutputParser`

```bash
curl -s -X POST localhost:18282/langchain/prompts/structured \
  -H 'Content-Type: application/json' -d '{"topic": "gravity"}'
```

Sample response:
```json
{"summary": "Gravity is a fundamental force...", "key_points": ["...", "...", "..."]}
```

**Why this input demonstrates the concept:** the response is a validated
`ConceptExplanation` object (`summary` + `key_points`), not a raw string —
the model's free-text answer got funneled through a schema. Compare this
to 1a's response, which is a plain string for an equivalent request; the
difference *is* the concept.

---

## 2. LCEL Chains

### 2a. Pipe chain — a linear transform

```bash
curl -s -X POST localhost:18282/langchain/chains/pipe \
  -H 'Content-Type: application/json' \
  -d '{"text": "Photosynthesis is the biochemical process by which chlorophyll-containing organisms convert light energy into chemical energy stored in glucose molecules."}'
```

**Why this input demonstrates the concept:** a deliberately dense,
jargon-heavy sentence was chosen so the "rewrite for a 10-year-old" prompt
has an obvious, visible job to do — you can directly compare input
complexity to output simplicity and see the `prompt | llm | parser` chain
did real work, not a no-op.

### 2b. Parallel chain — one input, three concurrent branches

```bash
curl -s -X POST localhost:18282/langchain/chains/parallel \
  -H 'Content-Type: application/json' -d '{"topic": "volcanoes"}'
```

Sample response:
```json
{
  "summary": "Volcanoes are landforms that occur when magma...",
  "questions": ["What are the main differences between shield volcanoes and stratovolcanoes?", "..."],
  "original_topic": "volcanoes"
}
```

**Why this input demonstrates the concept:** the single string `"volcanoes"`
fans out into three independent results — an LLM-generated `summary`, an
LLM-generated `questions` list, and `original_topic` which is just
`"volcanoes"` echoed back unchanged. That third field costs no LLM call at
all — it's `RunnablePassthrough()` proving the original input survives
alongside the derived branches.

---

## 3. Tool Calling

Each example below targets a *specific* piece of the tool-selection logic
documented in `tools/*.py`'s docstrings.

### 3a. Unambiguous arithmetic — the baseline case

```bash
curl -s -X POST localhost:18282/langchain/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "what is 12 times 7?"}'
```
→ `{"tool_calls":[{"name":"multiplier","args":{"a":12,"b":7},"result":84}], "final_answer":"12 × 7 = 84"}`

**Why:** confirms the simplest path — one clear tool, one clear call, the
final answer matches the tool's actual result.

### 3b. Bare "increment" — implicit "by 1"

```bash
curl -s -X POST localhost:18282/langchain/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "increment 5"}'
```
→ `{"tool_calls":[{"name":"adder","args":{"a":5,"b":1},"result":6}], ...}`

**Why this input demonstrates the concept:** `"increment 5"` never states
an amount. `tools/math_tools.py`'s `adder` docstring explicitly teaches the
model that a bare increment means "by 1" via a few-shot example — this
input is the direct test of whether that few-shot guidance actually
worked (it does: `b=1`, not a hallucinated number).

### 3c. Repeated addition — should resolve to `multiplier`, not a loop of `adder`

```bash
curl -s -X POST localhost:18282/langchain/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "add 4 to itself 6 times"}'
```
→ `{"tool_calls":[{"name":"multiplier","args":{"a":4,"b":6},"result":24}], "final_answer":"4 + 4 = 8\n8 + 4 = 12\n...\n24"}`

**Why this input demonstrates the concept:** this phrase describes
*repeated addition*, and `math_tools.py`'s docstrings specifically instruct
the model to collapse that pattern into one `multiplier` call rather than
reasoning step-by-step. The tool call proves the collapse happened — note
the final answer *narrates* it as repeated addition anyway, which is fine;
what matters is only one correctly-computed tool call occurred.

### 3d. A tool that fails — graceful degradation, not a crash

```bash
curl -s -X POST localhost:18282/langchain/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "Tell me a fun fact about space."}'
```
→ `{"tool_calls":[{"name":"web_search","args":{"query":"fun facts about space"},"result":"Error calling tool 'web_search': Missing GOOGLE_API_KEY..."}], "final_answer":"I apologize for the error! Here's a fun fact about space that I found: ..."}`

**Why this input demonstrates the concept:** without Google Search
credentials configured, `web_search` raises. `langchain_demo/tool_utils.py`'s
`create_tool_caller` catches that exception and feeds the error text back
to the model as the tool's result *instead of* crashing the request — the
model then recovers and answers from its own knowledge anyway. This input
is chosen specifically because it's the kind of general-knowledge question
that makes the model reach for `web_search` even though it isn't
configured, exercising the error path on purpose.

**Gotcha worth knowing:** small local models bound to many tools are
trigger-happy — plenty of ordinary conversational prompts (e.g. "write a
haiku about the ocean") will still produce a spurious tool call (e.g.
`is_palindrome` on unrelated text) instead of a clean no-tool response.
That's a real limitation of the model, not the tool-calling wiring — the
code path for "no tool needed" (`tool_calls: []`) exists and works, it's
just not reliably triggered by this particular small model.

---

## 4. Structured Output

```bash
curl -s -X POST localhost:18282/langchain/structured-output \
  -H 'Content-Type: application/json' -d '{"dish": "chicken tikka masala"}'
```

**Why this input demonstrates the concept:** a dish with a non-trivial,
multi-stage recipe (marinate → bake → simmer a sauce → combine) was chosen
over something trivial (like "toast") so the returned `Recipe.steps` list
has genuine structure to validate — a one-step dish wouldn't exercise the
schema's `list[str]` field meaningfully.

---

## 5. Memory / Conversation

```bash
SID="my-test-session"

curl -s -X POST "localhost:18282/langchain/memory/$SID" \
  -H 'Content-Type: application/json' \
  -d '{"message": "I am planning a trip to Japan in the spring."}'

curl -s -X POST "localhost:18282/langchain/memory/$SID" \
  -H 'Content-Type: application/json' \
  -d '{"message": "What season did I say I was traveling in?"}'

curl -s "localhost:18282/langchain/memory/$SID"      # full history
curl -s -X DELETE "localhost:18282/langchain/memory/$SID"
curl -s -i "localhost:18282/langchain/memory/$SID" | head -1   # now 404
```

Turn 2's response: *"You mentioned earlier that you're planning a trip to
Japan in the spring."*

**Why this input demonstrates the concept:** turn 2 deliberately asks a
question that is **unanswerable without turn 1's content** ("what season
did I say" — the model was never told the season in this message). A
correct answer to turn 2 is only possible if `RunnableWithMessageHistory`
actually replayed turn 1 into the prompt. The `GET`/`DELETE`/`GET`(404)
sequence at the end demonstrates the history is real, inspectable state,
not just an internal implementation detail.

### 5b. Same conversation, three different storage backends

```bash
for backend in memory redis postgres; do
  SID="backend-demo-$backend"
  curl -s -X POST "localhost:18282/langchain/memory/$SID?memory_backend=$backend" \
    -H 'Content-Type: application/json' -d '{"message": "I live in Tokyo."}' > /dev/null
  curl -s -X POST "localhost:18282/langchain/memory/$SID?memory_backend=$backend" \
    -H 'Content-Type: application/json' -d '{"message": "What city do I live in?"}'
  echo
done
```

**Why this input demonstrates the concept:** identical two-turn
conversation, only `memory_backend` changes. All three return the same
correct answer ("Tokyo") — proof `run_conversation_turn` contains **no
backend-specific logic at all**; only the `get_history(session_id)`
provider differs (a closure over a process-local dict for `memory`, a
cached `RedisChatMessageHistory` for `redis`, a `PostgresChatMessageHistory`
for `postgres` — see `docs/langchain/05-memory-conversation.md` for the
closure-vs-no-closure comparison). Kill and restart the app between the
`redis`/`postgres` calls and a follow-up `GET` and the history survives —
try the same with `memory_backend=memory` and it won't, since that
backend is process-local by design.

---

## 6. Agents (ReAct)

### 6a. Reliable single-tool-call case

```bash
curl -s -X POST localhost:18282/langchain/agents \
  -H 'Content-Type: application/json' \
  -d '{"message": "How many days are between 2026-01-01 and 2026-03-15?"}'
```
→ `{"final_answer":"...73 days.", "steps":[{"type":"tool_call","name":"days_between",...}, {"type":"tool_result","name":"days_between","result":"73"}, {"type":"ai_message",...}]}`

**Why this input demonstrates the concept:** the `steps` trace lets you
see the full reason → act → observe → answer loop explicitly, and the
final answer (73) matches the tool result (73) — a clean, verifiable
round trip.

### 6b. Multi-step chaining — a documented model limitation, not a bug

```bash
curl -s -X POST localhost:18282/langchain/agents \
  -H 'Content-Type: application/json' \
  -d '{"message": "Add 15 and 27, then multiply the result by 2."}'
```
→ `{"final_answer":"...42... 84.", "steps":[{"type":"tool_call","name":"multiplier","args":{"a":"15","b":"27"}}, {"type":"tool_result","name":"multiplier","result":"405"}, ...]}`

**Why this input demonstrates the concept — by failing:** this input is
deliberately a *two-step* calculation. Watch closely: the agent picks the
wrong tool for step one (`multiplier` instead of `adder`, giving `405`),
and then the **final answer ignores that result entirely**, inventing "42"
and "84" from nowhere. This is a real, reproducible small-model failure
mode — the trace (what the agent *actually* computed) and the final
answer (what it *claims*) can diverge. Always check `steps`, not just
`final_answer`, when debugging an agent. See
`docs/langchain/06-react-agents.md` for more on this limitation.

### 6c. Multi-turn agent memory, surviving an app restart

```bash
curl -s -X POST "localhost:18282/langchain/agents?memory_backend=postgres&session_id=demo-thread" \
  -H 'Content-Type: application/json' -d '{"message": "My favorite number is 42."}'

scripts/stop_app.sh && scripts/start_app.sh   # kill and restart the whole process

curl -s -X POST "localhost:18282/langchain/agents?memory_backend=postgres&session_id=demo-thread" \
  -H 'Content-Type: application/json' -d '{"message": "What is my favorite number?"}'
```

The second call's `final_answer` correctly says 42.

**Why this input demonstrates the concept:** restarting the whole process
between the two calls wipes anything that lived only in memory — this
proves the agent's state genuinely persisted to Postgres via its
`checkpointer` (`langgraph.checkpoint.postgres.PostgresSaver`), not just
within one long-running process. Reusing the same `session_id`
(LangGraph's `thread_id`) is what ties the two calls to the same
persisted conversation; omit it and each call gets a fresh, unrelated
thread. Swap `memory_backend=postgres` for `redis` to see the same proof
against the other persistent backend — only `memory_backend=memory` would
fail this test, by design.

### 6d. Multi-turn follow-up with gemma4 — verifying the tool-repeat-loop fix

```bash
curl -s -X POST "localhost:18282/langchain/agents?model=gemma4&session_id=testing-doc-agent-followup" \
  -H 'Content-Type: application/json' -d '{"message": "What is 3+4?"}'

curl -s -X POST "localhost:18282/langchain/agents?model=gemma4&session_id=testing-doc-agent-followup" \
  -H 'Content-Type: application/json' -d '{"message": "What happens when I add 5 to it?"}'
```

**Why this input demonstrates the concept:** count the `steps` in the
second response — it should be exactly 6 (3 from turn 1's `adder(3,4)`
call/result/message, 3 from turn 2's `adder(7,5)` call/result/message).
Before `AGENT_SYSTEM_PROMPT` was added to `react_agent.py`, this exact
input made gemma4 call `adder(7, 5)` over a dozen times *after* already
getting the correct result (12), before finally answering in plain text
— a real, reported, reproducible failure, not a hypothetical. If you
ever see a tool called with identical arguments more than once in a
row, that's this failure mode recurring, not a session/memory bug — see
`docs/langchain/06-react-agents.md`'s Gotchas.

---

## 7. RAG — compare all three backends on the same question

```bash
scripts/start_infra.sh   # if not already up

for backend in memory redis postgres; do
  curl -s -X POST "localhost:18282/langchain/rag/query?backend=$backend" \
    -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'
done
```

All three return the same grounded answer (from `langchain_demo/rag_corpus.md`):
> "RAG (Retrieval-augmented generation) is used to give a model access to
> information it was not trained on by searching a document collection for
> relevant passages and inserting them into the prompt before asking a
> question."

**Why this input demonstrates the concept:** the *same* question against
the *same* corpus through three different vector store implementations
returns near-identical answers — proof the retrieval abstraction is doing
its job identically regardless of backend, per `docs/langchain/07-rag/`.

### 7b. A question the corpus can't answer — grounding, not hallucination

```bash
curl -s -X POST "localhost:18282/langchain/rag/query?backend=memory" \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the capital of Australia?"}'
```
→ *"There is no information provided in the context about the capital of
Australia..."*

**Why this input demonstrates the concept:** this question is
*unrelated to the corpus on purpose*. The RAG prompt
(`langchain_demo/rag_demo.py`'s `_ANSWER_PROMPT`) explicitly instructs the
model to answer **only** from retrieved context — this input proves that
instruction is actually being honored instead of the model falling back to
its own (unrelated) general knowledge about world capitals.

---

## 8. Streaming

```bash
curl -N -X POST localhost:18282/langchain/streaming \
  -H 'Content-Type: application/json' -d '{"topic": "how rainbows form"}'
```

Sample output (truncated):
```
data: The

data:  majestic

data:  rainbow

data:  -

data:  a
...
```

**Why this input demonstrates the concept:** the `-N` flag disables curl's
output buffering, so you visibly see `data: <chunk>` lines arrive one at a
time rather than all at once — the point isn't the topic, it's watching
the response materialize incrementally instead of waiting for the full
generation to finish.

**Gotcha:** the same request with `?model=gemma4` streams real
content too, but interleaves many `data: ` lines with an *empty* chunk
between real tokens (verified: piping to a file and filtering out blank
lines shows the actual words/emoji are all there). This is
`ChatOllama.astream()`'s tokenization for that model, not a bug in
`streaming_demo.py` — don't "fix" it by filtering empty chunks unless
asked.

## 9. MCP Client (LangChain)

Needs `scripts/start_mcp_server.sh` running first (port `18383`).

```bash
# Tools: fetched from the MCP server, not imported locally.
curl -s -X POST localhost:18282/langchain/mcp/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "what is 12 times 7?"}'

# Prompts: fetch the server's explain_concept prompt.
curl -s -X POST localhost:18282/langchain/mcp/prompt \
  -H 'Content-Type: application/json' -d '{"topic": "RAG"}'

# Resources: dynamic (default) vs. static.
curl -s localhost:18282/langchain/mcp/resource
curl -s "localhost:18282/langchain/mcp/resource?uri=data://ai-tutorial/rag-corpus"
```

**Why this input demonstrates the concept:** `multiplier` in the
tool-calling response's `tool_calls` is the exact same function
`/langchain/tool-calling` (§3) binds directly — the only difference
between the two endpoints is that this one fetched it from
`mcp_server/tools.py` over HTTP first. Comparing the two side by side is
the point, not the arithmetic.

```bash
# Tools, the decorator-registered one: mcp_server/tools.py's
# server_uptime_seconds is defined with @mcp.tool() instead of
# mcp.add_tool(fn) — this confirms both registration styles produce an
# equally callable tool from the client's point of view.
curl -s -X POST localhost:18282/langchain/mcp/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "how long has the MCP server been running?"}'
```

**Why this input demonstrates the concept:** `server_uptime_seconds` in
the response's `tool_calls` has no backing function in `tools/*.py` at
all — it only exists because `mcp_server/tools.py`'s `register_tools`
declared it inline with `@mcp.tool()`. Getting a real elapsed-seconds
answer back proves the decorator path builds a fully working MCP tool
(name, docstring-derived description, schema) with no `tools/*.py`
entry required — see `docs/mcp-server.md`'s "Tools" section for why this
one, specifically, is a decorator tool rather than a shared function.

```bash
# Agent: same MCP-sourced tools, but a full ReAct loop instead of the
# single hand-executed round above. session_id carries memory across
# calls, same as /langchain/agents.
curl -s -X POST "localhost:18282/langchain/mcp/agent?session_id=testing-doc-mcp-agent" \
  -H 'Content-Type: application/json' -d '{"message": "what is 3+4?"}'
curl -s -X POST "localhost:18282/langchain/mcp/agent?session_id=testing-doc-mcp-agent" \
  -H 'Content-Type: application/json' -d '{"message": "what happens if I add 5 to the result?"}'
```

**Why this input demonstrates the concept:** turn 2's `steps` shows the
agent calling `adder(7, 5)` exactly once — proof `session_id` carried
turn 1's result (7) into this call, and proof `AGENT_SYSTEM_PROMPT`
(shared from `react_agent.py`, see §6d) stops it from re-calling `adder`
after already getting the answer. Omitting `session_id` on turn 2
instead sends a fresh, historyless thread with no idea what "the
result" means. Compare this endpoint's `steps` to `/langchain/agents`
(§6): same `create_react_agent` machinery and the same
`session_id`/`memory_backend` shape, the only difference is these tools
were fetched from `mcp_server/tools.py` over MCP instead of
imported from `tools/*.py` directly.

```bash
# Confirm the clean-503 (not 500) path: stop the MCP server first.
scripts/stop_mcp_server.sh
curl -s -w '\n%{http_code}\n' -X POST localhost:18282/langchain/mcp/tool-calling \
  -H 'Content-Type: application/json' -d '{"message": "what is 2+2?"}'
scripts/start_mcp_server.sh
```

See [docs/langchain/09-mcp-client.md](langchain/09-mcp-client.md) and
[docs/mcp-server.md](mcp-server.md) for the full design.

---

# Part 2: LangGraph Concepts

Everything below exercises `langgraph_demo/`, mounted under
`/langgraph/**` — see [docs/langgraph/00-overview.md](langgraph/00-overview.md)
for how this package relates to Part 1's LangChain concepts. Same
convention: `model` is an optional query parameter everywhere an LLM is
involved, defaulting to `llama3.2`.

## 10. StateGraph Basics

```bash
curl -s -X POST localhost:18282/langgraph/stategraph \
  -H 'Content-Type: application/json' -d '{"topic": "black holes"}'
```

**Why this input demonstrates the concept:** the response contains both
a `fact` and a `joke` derived *from that fact* — proof the second node
actually read the first node's output via shared state, not just ran
independently. Compare with `docs/langchain/02-lcel-chains.md`'s pipe
chain: same "step 1 feeds step 2" idea, expressed as graph nodes+edges
instead of a `|` pipe.

## 11. Conditional Edges / Branching

```bash
curl -s -X POST localhost:18282/langgraph/branching \
  -H 'Content-Type: application/json' -d '{"question": "What is 9 times 8?"}'

curl -s -X POST localhost:18282/langgraph/branching \
  -H 'Content-Type: application/json' -d '{"question": "What is the tallest mountain?"}'
```

**Why this input demonstrates the concept:** one clearly mathematical
question and one clearly general-knowledge question, run through the
*same* graph. Each gets routed to a different node (`category` in the
response tells you which) and produces a structurally different answer
(a tool-call result string for math, prose for general) — proof
`add_conditional_edges` actually changed which node ran, not just which
answer came back.

## 12. Cycles / Loops

```bash
curl -s -X POST localhost:18282/langgraph/cycles \
  -H 'Content-Type: application/json' \
  -d '{"topic": "the history of the Roman Empire", "max_words": 1, "max_attempts": 3}'
```

**Why this input demonstrates the concept:** `max_words: 1` is a tight
constraint, but `llama3.2` is often good enough to hit it in a single
attempt (e.g. `"Decline."`) — proof the feedback-driven prompt design in
`docs/langgraph/03-cycles.md` works well, but not proof the *loop*
fired. To see the loop-back edge and the `max_attempts` safety cap
actually engage, use a constraint that's impossible to satisfy:

```bash
curl -s -X POST localhost:18282/langgraph/cycles \
  -H 'Content-Type: application/json' \
  -d '{"topic": "the history of the Roman Empire", "max_words": 0, "max_attempts": 1}'
```

`max_words: 0` can never be met by any non-empty response, so this
reliably returns `met_target: false` with `attempts_used` equal to
`max_attempts` — the graph ran out of retries and terminated via
`should_continue`'s second condition instead of looping forever.

## 13. Streaming Graph Execution

```bash
curl -N -X POST localhost:18282/langgraph/streaming \
  -H 'Content-Type: application/json' -d '{"topic": "penguins"}'
```

**Why this input demonstrates the concept:** you'll see exactly **two**
`data:` lines — one `{"node": "generate_fact", ...}`, one
`{"node": "generate_joke", ...}` — each containing a *complete* piece of
text, not word-by-word fragments. Run
`curl -N -X POST localhost:18282/langchain/streaming -d '{"topic": "penguins"}'`
right after and count the difference: dozens of tiny token chunks with no
node information at all. Same underlying idea (streaming instead of
waiting for the full response), two different granularities.

## 14. Human-in-the-Loop / Interrupts

```bash
curl -s -X POST localhost:18282/langgraph/interrupts/start \
  -H 'Content-Type: application/json' \
  -d '{"request": "Can you extend my deadline by two days?", "session_id": "approval-demo"}'

curl -s -X POST localhost:18282/langgraph/interrupts/resume \
  -H 'Content-Type: application/json' -d '{"session_id": "approval-demo", "approved": true}'
```

Then try the reject path with a fresh session, and try calling `/resume`
with a `session_id` that never called `/start`:

```bash
curl -s -i -X POST localhost:18282/langgraph/interrupts/resume \
  -H 'Content-Type: application/json' -d '{"session_id": "never-started", "approved": true}'
```

**Why this input demonstrates the concept:** `/start`'s response status
is `"waiting_for_approval"` — the graph genuinely paused mid-execution
and returned control to you, it didn't just run to completion and label
itself paused. The unstarted-session call returns a `400` with a clear
message rather than crashing, proving there's real, checkable state
behind "is this thread actually paused" (`graph.get_state(config).next`),
not just an assumption that every resume call is valid.

## 15. Persistence / Checkpointers (Standalone)

```bash
curl -s -X POST localhost:18282/langgraph/persistence/demo-counter
curl -s -X POST localhost:18282/langgraph/persistence/demo-counter
curl -s -X POST localhost:18282/langgraph/persistence/demo-counter
```

**Why this input demonstrates the concept:** three calls to a graph with
**no LLM and no tools at all** — `count` still climbs 1 → 2 → 3 and
`history` accumulates. This isolates the persistence mechanic from
everything else: it's not "the agent is smart," it's "any compiled graph
with a checkpointer remembers state across `.invoke()` calls sharing a
`thread_id`." For the deeper proof, restart the app between calls with
`memory_backend=postgres`:

```bash
curl -s -X POST "localhost:18282/langgraph/persistence/restart-proof?memory_backend=postgres"
scripts/stop_app.sh && scripts/start_app.sh
curl -s -X POST "localhost:18282/langgraph/persistence/restart-proof?memory_backend=postgres"
```

The second call after restart shows `count: 2`, not `count: 1`.

## 16. Multi-Agent / Subgraphs

```bash
curl -s -X POST localhost:18282/langgraph/multi-agent \
  -H 'Content-Type: application/json' -d '{"request": "What is 100 divided by 4?"}'

curl -s -X POST localhost:18282/langgraph/multi-agent \
  -H 'Content-Type: application/json' -d '{"request": "Write a two-line poem about the moon."}'
```

**Why this input demonstrates the concept:** one request that needs the
math specialist, one that needs the writing specialist, through the same
supervisor endpoint. `delegated_to` in each response confirms which
specialist *subgraph* actually ran — proof the supervisor's routing
logic correctly selected between two independently-compiled graphs, not
just two branches of plain function calls (contrast with §10's
branching demo, where the specialists are plain functions, not their own
graphs).

## 17. RAG (query rewriter + retriever + generator sub-graphs)

```bash
# Turn 1 — no history yet, query rewriter is a pass-through.
curl -s -X POST localhost:18282/langgraph/rag/testing-doc-session \
  -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'

# Turn 2 — "that" gets resolved to "retrieval-augmented generation" using
# turn 1's history.
curl -s -X POST localhost:18282/langgraph/rag/testing-doc-session \
  -H 'Content-Type: application/json' -d '{"question": "Which backend is best for that?"}'
```

**Why this input demonstrates the concept:** turn 1's response has
`was_rewritten: false` (nothing to rewrite yet); turn 2's has
`was_rewritten: true` and a `rewritten_query` that no longer contains
"that" — proof the query-rewriter sub-graph's history-based conditional
edge actually fires on the second turn, not just that the pipeline runs.

```bash
# Redis + Postgres backends, mixed (needs scripts/start_infra.sh):
curl -s -X POST "localhost:18282/langgraph/rag/testing-doc-session-2?history_backend=redis&vector_backend=postgres" \
  -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'

# rerank=true without COHERE_API_KEY set — expect 400, not 500:
curl -s -w '\n%{http_code}\n' -X POST "localhost:18282/langgraph/rag/testing-doc-session-3?rerank=true" \
  -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'
```

See [docs/langgraph/08-rag.md](langgraph/08-rag.md) for the full design,
all three sub-graphs' diagrams, and the independent `rewrite_eval`/
`rerank`/`generation_eval` flags.

## 18. MCP Client (LangGraph)

Needs `scripts/start_mcp_server.sh` running first (port `18383`).

```bash
curl -s -X POST localhost:18282/langgraph/mcp \
  -H 'Content-Type: application/json' -d '{"question": "what is 100 divided by 4?"}'
```

**Why this input demonstrates the concept:** the same MCP-sourced
`divider` tool §9's LangChain version would fetch, called from inside a
single-node `StateGraph` instead of a plain chain — proof an MCP tool is
just a LangChain `BaseTool` regardless of which framework's execution
model invokes it.

```bash
# Agent, memory-backed — session_id carries context across calls, same
# proof pattern as §6d and §9. Turn 3 is a harder question (needs two
# NEW tool calls, not one) that stresses the repeat-call guard more than
# turn 2 alone does.
S=testing-doc-lg-mcp-agent
curl -s -X POST "localhost:18282/langgraph/mcp/agent?model=gemma4&session_id=$S" \
  -H 'Content-Type: application/json' -d '{"question": "what is 3+4?"}'
curl -s -X POST "localhost:18282/langgraph/mcp/agent?model=gemma4&session_id=$S" \
  -H 'Content-Type: application/json' -d '{"question": "what happens when I add 5 to it?"}'
curl -s -X POST "localhost:18282/langgraph/mcp/agent?model=gemma4&session_id=$S" \
  -H 'Content-Type: application/json' -d '{"question": "what is 4+5+6"}'

# memory_backend=redis is NOT supported for this agent — expect a clean 400:
curl -s -w '\n%{http_code}\n' -X POST "localhost:18282/langgraph/mcp/agent?memory_backend=redis" \
  -H 'Content-Type: application/json' -d '{"question": "what is 9 times 8?"}'
```

**Why this input demonstrates the concept:** turn 3's `final_answer` is
15, computed from `adder(4,5)=9` then `adder(9,6)=15` — a genuine
LangGraph reason/act loop (`call_model` <-> `call_tools`, both hand-built
`StateGraph` nodes, see `docs/langgraph/09-mcp-client.md`), not
`langgraph.prebuilt.create_react_agent` (which `langchain_demo`'s MCP
agent uses instead). `steps` may show `adder(4,5)` repeated — that's
expected here and is exactly the case `_find_prior_tool_result` was
added for: verified live that repeated calls reuse the identical cached
MCP response rather than re-invoking the tool, so the repeats are cheap,
not a real second execution. The `redis` call demonstrates a real
constraint, not a bug to file: this agent runs via `.ainvoke()`, and
`checkpointers.py`'s `RedisSaver`/`PostgresSaver` are sync-only — see
`docs/langgraph/09-mcp-client.md`'s Gotchas for why.

See [docs/langgraph/09-mcp-client.md](langgraph/09-mcp-client.md) and
[docs/mcp-server.md](mcp-server.md) for the full design.
