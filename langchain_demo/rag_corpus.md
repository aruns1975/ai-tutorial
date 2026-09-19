# How This Project's LangChain Concepts Fit Together

This repository is a small FastAPI application built to teach core LangChain
and LangGraph concepts, one endpoint at a time. Every concept lives in its
own file under the `langchain_demo` package, and every file is wrapped by a
matching FastAPI router under the `controllers` package.

## Prompts and output parsers

The `prompts` concept shows the most basic LangChain building block: turning
a user's input into a well-structured prompt with `ChatPromptTemplate`, then
parsing the model's raw text response. Two parsing styles are contrasted:
`StrOutputParser`, which just returns the text, and `PydanticOutputParser`,
which asks the model to emit JSON matching a schema and validates it.

## LCEL chains

LangChain Expression Language, or LCEL, lets you compose steps with the `|`
operator, similar to a Unix pipe. A chain like `prompt | llm | parser` reads
left to right: format the prompt, send it to the model, parse the result.
`RunnableParallel` runs multiple branches over the same input at once,
`RunnableLambda` lifts a plain Python function into the chain, and
`RunnablePassthrough` forwards the original input unchanged alongside
derived values.

## Tool calling

Modern chat models can decide to call external functions instead of
answering directly. A model is given a list of available tools, described by
their names, arguments, and docstrings. When the model wants to use one, it
returns a structured tool call instead of text; the calling code executes
that function and feeds the result back for a final answer.

## Structured output

`with_structured_output()` is a shortcut that binds a schema directly to a
model call, so the model's response is constrained to match that schema
without the caller needing to hand-write format instructions or a separate
parsing step.

## Memory and conversation history

Chat models are stateless by default: each call only sees what you send it.
To hold a multi-turn conversation, the message history has to be tracked
outside the model and re-sent on every turn. `RunnableWithMessageHistory`
automates this by looking up a session's history before each call and
appending new messages after.

## Agents

An agent is a loop: the model reasons about what to do, optionally calls a
tool, observes the result, and repeats until it has enough information to
answer. This is sometimes called the ReAct pattern (Reason + Act). LangGraph
provides a prebuilt `create_react_agent` that implements this loop without
requiring you to hand-write the control flow.

## Retrieval-augmented generation

Retrieval-augmented generation, or RAG, gives a model access to information
it was not trained on by searching a document collection for relevant
passages and inserting them into the prompt before asking a question. The
documents are split into small chunks, each chunk is converted into a
numerical vector (an embedding), and a vector store is used to find the
chunks most similar to a given question. This project demonstrates three
interchangeable vector store backends for that search step: an in-memory
store for quick experimentation, Redis for a fast in-memory-plus-persistence
option, and Postgres with the pgvector extension for a durable, indexed
option suited to larger collections.

## Streaming

Instead of waiting for a model to finish generating a full response, a chain
can stream its output chunk by chunk as it's produced. This project exposes
a streaming endpoint using Server-Sent Events, so a client can start
displaying a response before the model has finished writing it.
