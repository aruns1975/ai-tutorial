"""
Concept: MCP (Model Context Protocol) client.

Connects to this project's own MCP server (mcp_server/, started via
scripts/start_mcp_server.sh — see docs/mcp-server.md) instead of
importing tools/*.py functions directly, and demonstrates all three MCP
primitives: tools, prompts, and resources.

The tools exposed by the MCP server (mcp_server/tools.py) are the exact
same tools/*.py functions tool_calling.py and react_agent.py import and
bind directly — the difference here is HOW they're reached: over the
MCP protocol as if they lived on a separate server/process (which, when
run via scripts/start_mcp_server.sh, they do), not via a local Python
import. Once fetched, an MCP tool is just a LangChain BaseTool like any
other, so run_mcp_tool_calling_demo below mirrors tool_calling.py's
run_tool_calling_demo almost line for line — the only real difference
is `await client.get_tools(...)` in place of a local `_TOOLS` list.

run_mcp_agent_demo is the same idea one level up: instead of the
single-round bind_tools loop above, it hands the MCP-fetched tools to
LangGraph's prebuilt create_react_agent — the MCP-sourced counterpart to
react_agent.py's run_agent_demo. It reuses that file's AgentMemoryBackend
and its redis/postgres checkpointer builders directly (same package,
already-debugged setup code — no reason to write a second copy), so a
follow-up question like "what happens if I add 5 to the result?" can
actually see the previous turn's result via `session_id`, instead of
asking the model to guess at an undefined "the result" — which, with a
smaller model like gemma4, was observed to occasionally spiral into
several unnecessary tool-call rounds before settling on an answer,
rather than failing cleanly.
"""

import os
import uuid

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from langchain_demo import react_agent_postgres, react_agent_redis
from langchain_demo.react_agent import AGENT_SYSTEM_PROMPT, AgentMemoryBackend
from models.chat_models.ollama_models import SupportedModel, get_chat_model

_SERVER_NAME = "ai_tutorial"
_MCP_SERVER_URL = f"http://localhost:{os.getenv('MCP_SERVER_PORT', '18383')}/mcp"

# Caps how many reason/act rounds a single run_mcp_agent_demo call can
# take before LangGraph raises GraphRecursionError, instead of the
# default 25 — if the model gets stuck re-guessing at a tool instead of
# asking for clarification, this fails fast with a clear error rather
# than quietly grinding through many rounds.
_AGENT_RECURSION_LIMIT = 15

# One client, built once — like every other *_llm/store singleton in this
# project. Building it doesn't connect to anything; a session is opened
# per call to get_tools()/get_prompt()/get_resources(), so this is safe
# to hold even if the MCP server isn't running yet.
_client = MultiServerMCPClient({_SERVER_NAME: {"transport": "streamable_http", "url": _MCP_SERVER_URL}})

_AGENT_CHECKPOINTER_BUILDERS = {
    AgentMemoryBackend.memory: InMemorySaver,
    AgentMemoryBackend.redis: react_agent_redis.build_checkpointer,
    AgentMemoryBackend.postgres: react_agent_postgres.build_checkpointer,
}


def create_mcp_agent_cache():
    """
    Build an MCP-agent cache. Returns an async get_agent(model, memory_backend)
    closure — same shape as react_agent.py's create_agent_cache(), for the
    same reason: the graph's tools/checkpointer are baked in at compile
    time, so one compiled agent is built per (model, backend) pair, not
    per call. Async because building it needs one MCP round-trip
    (_client.get_tools) the first time a given pair is requested.
    """
    agents: dict[tuple[SupportedModel, AgentMemoryBackend], object] = {}

    async def get_agent(model: SupportedModel, memory_backend: AgentMemoryBackend):
        key = (model, memory_backend)
        if key not in agents:
            tools = await _client.get_tools(server_name=_SERVER_NAME)
            checkpointer = _AGENT_CHECKPOINTER_BUILDERS[memory_backend]()
            agents[key] = create_react_agent(
                get_chat_model(model), tools=tools, checkpointer=checkpointer, prompt=AGENT_SYSTEM_PROMPT
            )
        return agents[key]

    return get_agent


_get_mcp_agent = create_mcp_agent_cache()


async def run_mcp_tool_calling_demo(user_message: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Fetch tools from the MCP server, bind them to the chat model,
    execute whichever tool(s) it calls, and re-invoke for a final
    answer — the MCP-sourced counterpart to
    tool_calling.py's run_tool_calling_demo.

    Returns {"tool_calls": [{"name": str, "args": dict, "result": Any}],
             "final_answer": str}.
    """
    tools = await _client.get_tools(server_name=_SERVER_NAME)
    tools_by_name = {tool.name: tool for tool in tools}

    llm = get_chat_model(model)
    messages = [HumanMessage(content=user_message)]
    ai_message = llm.bind_tools(tools).invoke(messages)
    messages.append(ai_message)

    tool_calls_trace = []
    for tool_call in ai_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        try:
            result = await tool.ainvoke(tool_call["args"])
        except Exception as exc:
            result = f"Error calling tool '{tool_call['name']}': {exc}"
        tool_calls_trace.append({"name": tool_call["name"], "args": tool_call["args"], "result": result})
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    if not tool_calls_trace:
        return {"tool_calls": [], "final_answer": ai_message.content}

    final_message = llm.invoke(messages)
    return {"tool_calls": tool_calls_trace, "final_answer": final_message.content}


async def run_mcp_agent_demo(
    user_message: str,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: AgentMemoryBackend = AgentMemoryBackend.memory,
    session_id: str | None = None,
) -> dict:
    """
    Fetch tools from the MCP server and hand them to LangGraph's prebuilt
    create_react_agent, instead of tool-calling by hand like
    run_mcp_tool_calling_demo above — the agent decides how many
    tool-call rounds it needs, rather than the single round that function
    hand-executes.

    `session_id` is LangGraph's `thread_id`, same as react_agent.py's
    run_agent_demo: omit it for a single-shot, stateless call (a fresh
    thread is used and discarded); pass the same value across calls to
    accumulate multi-turn memory via the chosen `memory_backend`.

    Returns {"session_id": str, "backend": str, "final_answer": str,
             "steps": [{"type": "tool_call"|"tool_result"|"ai_message", ...}]}.
    """
    agent = await _get_mcp_agent(model, memory_backend)
    thread_id = session_id or str(uuid.uuid4())
    result = await agent.ainvoke(
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

    return {
        "session_id": thread_id,
        "backend": memory_backend.value,
        "final_answer": messages[-1].content,
        "steps": steps,
    }


async def run_mcp_prompt_demo(topic: str) -> dict:
    """
    Fetch the server's "explain_concept" prompt template, filled in
    with `topic` (see mcp_server/prompts.py).

    Returns {"topic": str, "messages": [{"role": str, "content": str}]}.
    """
    messages = await _client.get_prompt(_SERVER_NAME, "explain_concept", arguments={"topic": topic})
    return {"topic": topic, "messages": [{"role": m.type, "content": m.content} for m in messages]}


async def run_mcp_resource_demo(uri: str = "data://ai-tutorial/models") -> dict:
    """
    Read a resource from the MCP server by URI (see
    mcp_server/resources.py for the two exposed: "data://ai-tutorial/models"
    and "data://ai-tutorial/rag-corpus").

    Returns {"uri": str, "content": str}.
    """
    resources = await _client.get_resources(_SERVER_NAME, uris=[uri])
    return {"uri": uri, "content": resources[0].data if resources else None}
