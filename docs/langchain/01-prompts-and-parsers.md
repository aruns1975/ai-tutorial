# Prompts, LLM Calls, and Output Parsers

> 🧪 **Try it hands-on:** [`jupyter/01-prompts-and-parsers.ipynb`](jupyter/01-prompts-and-parsers.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

A `PromptTemplate` (or `ChatPromptTemplate` for chat models) turns user input
into a well-structured message before it's sent to a model. Once the model
responds, an output parser turns its raw text into something your code can
use — anything from "just give me the string" to "give me a validated
object."

This file contrasts two parser styles:
- `StrOutputParser` — no transformation, just the text.
- `PydanticOutputParser` — the prompt is given format instructions (a
  description of the target schema), and the parser validates the model's
  response against a Pydantic model.

## Code walkthrough

See `langchain_demo/prompts_and_parsers.py`.

`run_str_output_demo(topic, style, structured_output=True, model=SupportedModel.llama3_2)`
builds a `ChatPromptTemplate` with a system message templated on `style`
and a human message templated on `topic`. `get_chat_model(model)` resolves
which `ChatOllama` instance to use (see "Choosing a model" below). The
`structured_output` flag toggles whether `StrOutputParser()` is in the
chain at all:

```python
llm = get_chat_model(model)
base_chain = prompt | llm
chain = base_chain | StrOutputParser() if structured_output else base_chain
```

With `structured_output=True` (the default), `response` is a plain string.
With `False`, the parser is skipped and `response` is the raw `AIMessage`
the model returned — content plus metadata (token usage, stop reason,
model name, etc.). Comparing the two responses side by side *is* the demo:
it shows exactly what `StrOutputParser` strips away to give you just the
text.

`run_pydantic_parser_demo(topic, model=SupportedModel.llama3_2)` embeds
`parser.get_format_instructions()` into the system prompt so the model
knows the exact JSON shape expected, then parses the raw response into a
`ConceptExplanation` object.

## Choosing a model

Both endpoints accept an optional `model` **query parameter**
(`?model=...`): `"llama3.2"` (default) or `"gemma4"`. See
`docs/TESTING.md` §0 for a worked comparison.

## Local infra prerequisites

None — just Ollama running locally with `llama3.2` (and `gemma4` if you
want to try it) pulled.

## How to call it

```bash
curl -s -X POST localhost:18282/langchain/prompts \
  -H 'Content-Type: application/json' \
  -d '{"topic": "black holes", "style": "concise"}'

# same request, but skip StrOutputParser to see the raw AIMessage
# (structured_output is also a query param, not a body field)
curl -s -X POST "localhost:18282/langchain/prompts?structured_output=false" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "black holes", "style": "concise"}'

curl -s -X POST localhost:18282/langchain/prompts/structured \
  -H 'Content-Type: application/json' \
  -d '{"topic": "black holes"}'

# same request against gemma4 instead of the default llama3.2
curl -s -X POST "localhost:18282/langchain/prompts?model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "black holes", "style": "concise"}'
```

## Gotchas

- Small local models (like `llama3.2`) sometimes emit slightly malformed
  JSON when asked to follow `PydanticOutputParser`'s format instructions on
  their own (e.g. an unclosed array). This demo binds the model with
  `format="json"` (an Ollama-specific option forcing syntactically valid
  JSON output) to make the pydantic-parsing path reliable — it doesn't
  enforce your schema, just valid JSON syntax, so the parser still does the
  real validation work.
