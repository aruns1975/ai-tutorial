# Tool Calling / Function Calling

## Concept

Modern chat models can decide to call an external function instead of
answering directly. The model is given a list of available tools — their
names, arguments, and docstrings — and when it wants to use one, it returns
a structured tool call (name + arguments) instead of plain text. The calling
code executes that function and feeds the result back to the model for a
final natural-language answer.

## Code walkthrough

See `langchain_demo/tool_calling.py`. It reuses functions straight from the
`tools/` package (see `tools/math_tools.py`, `tools/string_tools.py`,
`tools/search_tools.py`) — those modules' rich docstrings (the
"Call this tool for..." + few-shot-examples convention) are exactly what a
tool-calling model reads to decide which function fits a request.

```python
llm = get_chat_model(model)
ai_message = llm.bind_tools(_TOOLS).invoke(messages)
```

`run_tool_calling_demo(user_message, model=SupportedModel.llama3_2)` sends
the message to the tool-bound model. If the response includes
`tool_calls`, each is executed via `langchain_demo/tool_utils.py`'s
`create_tool_caller` closure (looks the function up by name, invokes it
with the model-supplied args), the results are appended as `ToolMessage`s,
and the *same* selected model is invoked once more for a final answer
grounded in those results. `create_tool_caller` catches exceptions from
the tool itself and returns the error as a string instead of letting it
propagate — see the Gotchas section below.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"` —
both handle single-tool-call requests reliably.

## Local infra prerequisites

None (the `web_search` tool additionally needs `GOOGLE_API_KEY`/
`GOOGLE_CSE_ID` in `.env` if you want that specific tool to succeed — see
`tools/search_tools.py`).

## How to call it

```bash
curl -s -X POST localhost:18282/langchain/tool-calling \
  -H 'Content-Type: application/json' \
  -d '{"message": "reverse the word hello"}'

curl -s -X POST localhost:18282/langchain/tool-calling \
  -H 'Content-Type: application/json' \
  -d '{"message": "what is 12 times 7?"}'
```

## Gotchas

- The bound tools here are plain Python functions (not `@tool`-decorated
  `StructuredTool` instances), so `create_tool_caller` invokes them
  directly as `tool_fn(**args)` rather than via a `.invoke()` method.
- If the model responds with no `tool_calls` at all (e.g. a question that
  doesn't need a tool), the demo returns its direct text answer with an
  empty `tool_calls` list — check for that case rather than assuming a tool
  was always used.
- **A failing tool doesn't crash the request.** If `web_search` is called
  without `GOOGLE_API_KEY`/`GOOGLE_CSE_ID` configured, it raises — the
  error is caught and fed back to the model as the tool's result (a
  string), so the model can recover and answer from its own knowledge
  instead of the endpoint 500ing. See `docs/TESTING.md` §3d for a live
  example.
- Small local models bound to many tools are trigger-happy — plenty of
  ordinary conversational prompts still produce a spurious, irrelevant
  tool call instead of a clean text-only response. This is a model
  limitation, not a bug in the wiring.
