"""
Concept: Agents (ReAct-style, tool-using loops).

Uses LangGraph's prebuilt create_react_agent to build a
reason-act-observe loop: the model decides which tool(s) to call,
observes results, and repeats until it has enough information to
answer, all without hand-writing the loop yourself (contrast with
tool_calling.py's single-round bind_tools demo).

Also demonstrates LangGraph's *native* persistence: a `checkpointer`
attached to the compiled graph gives the agent multi-turn memory keyed by
`thread_id` — LangGraph's own answer to the same problem
memory_conversation.py solves with RunnableWithMessageHistory (which is
deprecated upstream specifically in favor of this). Selected via
`memory_backend`, the same three options as the Memory concept:

- memory   -> langgraph.checkpoint.memory.InMemorySaver. Lost on restart.
- redis    -> langchain_demo/react_agent_redis.py.
- postgres -> langchain_demo/react_agent_postgres.py.
"""

import uuid
from enum import Enum

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from langchain_demo import react_agent_postgres, react_agent_redis
from models.chat_models.ollama_models import SupportedModel, get_chat_model
from tools.datetime_tools import current_date, days_between
from tools.math_tools import adder, divider, multiplier, subtractor
from tools.search_tools import web_search

_AGENT_TOOLS = [adder, subtractor, multiplier, divider, current_date, days_between, web_search]

# Without this, gemma4 was observed to re-call a tool with IDENTICAL
# arguments over a dozen times after already getting the answer, before
# finally emitting a plain-text final message — create_react_agent's
# default ReAct loop has no built-in "stop once you have the result"
# instruction, and a weaker model doesn't reliably infer it. llama3.2
# didn't need this, but it's harmless for it too. Public (not
# underscore-prefixed) because mcp_client.py's run_mcp_agent_demo reuses
# it verbatim for the same create_react_agent call shape — no reason to
# maintain a second copy of the same instruction.
AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools. Once a tool call has "
    "returned a result that answers the user's question, respond directly "
    "with the final answer in plain text. Never call the same tool with the "
    "same arguments more than once."
)

# Caps reason/act rounds per call, instead of LangGraph's default 25 — if
# AGENT_SYSTEM_PROMPT's instruction still doesn't stop a repeat-call
# loop, this fails fast with a clear GraphRecursionError instead of
# quietly grinding through many more rounds.
_AGENT_RECURSION_LIMIT = 15


class AgentMemoryBackend(str, Enum):
    memory = "memory"
    redis = "redis"
    postgres = "postgres"


_CHECKPOINTER_BUILDERS = {
    AgentMemoryBackend.memory: InMemorySaver,
    AgentMemoryBackend.redis: react_agent_redis.build_checkpointer,
    AgentMemoryBackend.postgres: react_agent_postgres.build_checkpointer,
}

# -----------------------------------------------------------------------
# Encapsulation: closure vs. a bare module-level dict
#
# WITHOUT a closure, the compiled-agent cache would just be a module-level
# dict that any function in this file reads and writes directly:
#
#     _agents: dict[tuple[SupportedModel, AgentMemoryBackend], object] = {}
#
#     def _get_agent(model, memory_backend):
#         key = (model, memory_backend)
#         if key not in _agents:
#             checkpointer = _CHECKPOINTER_BUILDERS[memory_backend]()
#             _agents[key] = create_react_agent(get_chat_model(model), tools=_AGENT_TOOLS, checkpointer=checkpointer)
#         return _agents[key]
#
# This is exactly what this file used to do (back when it only cached by
# model, before checkpointers existed here). It works, but `_agents` is a
# name any function in this module can reach in and mutate directly.
#
# WITH a closure (the active implementation below), the dict lives only
# inside create_agent_cache()'s local scope — the returned function is the
# only way to reach it. Same trade-off as memory_conversation.py's
# create_memory_history_store(): same behavior, a boundary that's
# enforced rather than just conventional.
# -----------------------------------------------------------------------

def create_agent_cache():
    """
    Build a compiled-agent cache. Returns a get_agent(model, memory_backend)
    closure — the only way to reach the private dict inside this function.
    One compiled graph (and one checkpointer) is built per (model, backend)
    pair, since the graph's tools/checkpointer are baked in at compile time.
    """
    agents: dict[tuple[SupportedModel, AgentMemoryBackend], object] = {}

    def get_agent(model: SupportedModel, memory_backend: AgentMemoryBackend):
        key = (model, memory_backend)
        if key not in agents:
            checkpointer = _CHECKPOINTER_BUILDERS[memory_backend]()
            agents[key] = create_react_agent(
                get_chat_model(model), tools=_AGENT_TOOLS, checkpointer=checkpointer, prompt=AGENT_SYSTEM_PROMPT
            )
        return agents[key]

    return get_agent


_get_agent = create_agent_cache()


def run_agent_demo(
    user_message: str,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: AgentMemoryBackend = AgentMemoryBackend.memory,
    session_id: str | None = None,
) -> dict:
    """
    Invoke the LangGraph ReAct agent with a single human message and walk
    the returned message list into a step trace.

    `session_id` is LangGraph's `thread_id` under the hood: omit it for a
    single-shot, stateless call (a fresh thread is used and discarded);
    pass the same value across calls to accumulate multi-turn memory via
    the chosen `memory_backend`'s checkpointer — in that case `steps`
    reflects the *entire* thread's history so far, not just this turn.

    Returns {"session_id": str, "backend": str, "final_answer": str,
             "steps": [{"type": "tool_call"|"tool_result"|"ai_message", ...}]}.
    """
    agent = _get_agent(model, memory_backend)
    thread_id = session_id or str(uuid.uuid4())
    result = agent.invoke(
        {"messages": [("human", user_message)]},
        config={"configurable": {"thread_id": thread_id}, "recursion_limit": _AGENT_RECURSION_LIMIT},
    )
    messages = result["messages"]

    steps = []
    for message in messages:
        message_type = getattr(message, "type", None)
        if message_type == "ai" and getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                steps.append({"type": "tool_call", "name": tool_call["name"], "args": tool_call["args"]})
        elif message_type == "tool":
            steps.append({"type": "tool_result", "name": message.name, "result": message.content})
        elif message_type == "ai" and message.content:
            steps.append({"type": "ai_message", "content": message.content})

    final_answer = messages[-1].content
    return {"session_id": thread_id, "backend": memory_backend.value, "final_answer": final_answer, "steps": steps}
