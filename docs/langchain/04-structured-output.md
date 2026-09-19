# Structured Output

## Concept

`with_structured_output()` is a shortcut that binds a schema directly to a
model call. Contrast this with `prompts_and_parsers.run_pydantic_parser_demo`
(concept 1), which hand-writes format instructions into the prompt and
parses the raw text afterward as two separate steps — `with_structured_output`
handles both in one call.

## Code walkthrough

See `langchain_demo/structured_output.py`.

```python
def run_structured_output_demo(dish: str, model: SupportedModel = SupportedModel.llama3_2) -> Recipe:
    llm = get_chat_model(model)
    return llm.with_structured_output(Recipe).invoke(f"Give me a simple recipe for {dish}.")
```

`Recipe` is a plain Pydantic model (`name`, `ingredients`, `steps`,
`estimated_minutes`) — the return value is already a validated `Recipe`
instance, no separate parsing step required.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -s -X POST localhost:18282/langchain/structured-output \
  -H 'Content-Type: application/json' \
  -d '{"dish": "banana bread"}'

curl -s -X POST "localhost:18282/langchain/structured-output?model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"dish": "banana bread"}'
```

## Gotchas

- `with_structured_output()` still relies on the underlying model actually
  following the schema — for small local models, expect occasional loosely
  accurate field values (e.g. a rough `estimated_minutes` guess) even when
  the shape itself always validates.
