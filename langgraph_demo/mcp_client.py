"""
Concept: MCP (Model Context Protocol) client, inside a graph.

A single-node StateGraph whose node calls tools fetched from this
project's own MCP server (mcp_server/, started via
scripts/start_mcp_server.sh — see docs/mcp-server.md) instead of a
locally-imported tools/*.py function. The graph shape is deliberately
as simple as stategraph_basics.py's — the point isn't the graph, it's
that a LangGraph node reaches for an MCP tool exactly like
langchain_demo/mcp_client.py's chain does, with no LangGraph-specific
MCP integration needed: once fetched, an MCP tool is just a LangChain
BaseTool. Compare to branching.py's solve_math node, which binds
tools/math_tools.py functions directly via bind_tools — this node binds
the same kind of tools, just fetched over MCP instead of imported.

run_mcp_agent_demo is the memory-backed counterpart: instead of the
single-node graph above, it hands the MCP-fetched tools to LangGraph's
prebuilt create_react_agent with a checkpointer attached, so a
follow-up question (e.g. "what happens if I add 5 to the result?") can
see the previous turn's result via `session_id`. It reuses this
package's own checkpointers.py (CheckpointBackend/build_checkpointer) —
langgraph_demo's shared persistence story, per that file's docstring —
rather than langchain_demo.react_agent's AgentMemoryBackend/per-backend
files, which is the deliberate cross-package split documented in the
project root CLAUDE.md. It DOES reuse langchain_demo.react_agent's
AGENT_SYSTEM_PROMPT directly, though: that's a small, genuinely generic
instruction (not persistence logic), and without it, create_react_agent's
default loop was found (see docs/langchain/06-react-agents.md) to
re-call a tool with identical arguments many times after already
getting the answer — a fix worth sharing, not re-deriving.
"""

import os
import uuid
from typing import TypedDict

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from langchain_demo.react_agent import AGENT_SYSTEM_PROMPT
from langgraph_demo.checkpointers import CheckpointBackend, build_checkpointer
from models.chat_models.ollama_models import SupportedModel, get_chat_model

_SERVER_NAME = "ai_tutorial"
_MCP_SERVER_URL = f"http://localhost:{os.getenv('MCP_SERVER_PORT', '18383')}/mcp"

# Caps reason/act rounds per run_mcp_agent_demo call, instead of
# LangGraph's default 25 — a backstop in case AGENT_SYSTEM_PROMPT ever
# doesn't hold for some input.
_AGENT_RECURSION_LIMIT = 15

_client = MultiServerMCPClient({_SERVER_NAME: {"transport": "streamable_http", "url": _MCP_SERVER_URL}})


class MCPToolState(TypedDict):
    question: str
    answer: str


def _build_graph(model: SupportedModel):
    llm = get_chat_model(model)

    async def call_mcp_tools(state: MCPToolState) -> dict:
        tools = await _client.get_tools(server_name=_SERVER_NAME)
        tools_by_name = {tool.name: tool for tool in tools}

        messages = [HumanMessage(content=state["question"])]
        ai_message = llm.bind_tools(tools).invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return {"answer": ai_message.content}

        for tool_call in ai_message.tool_calls:
            tool = tools_by_name[tool_call["name"]]
            try:
                result = await tool.ainvoke(tool_call["args"])
            except Exception as exc:
                result = f"Error calling tool '{tool_call['name']}': {exc}"
            messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

        final_message = llm.invoke(messages)
        return {"answer": final_message.content}

    graph = StateGraph(MCPToolState)
    graph.add_node("call_mcp_tools", call_mcp_tools)
    graph.add_edge(START, "call_mcp_tools")
    graph.add_edge("call_mcp_tools", END)
    return graph.compile()


def create_graph_cache():
    graphs: dict[SupportedModel, object] = {}

    def get_graph(model: SupportedModel):
        if model not in graphs:
            graphs[model] = _build_graph(model)
        return graphs[model]

    return get_graph


_get_graph = create_graph_cache()


async def run_mcp_client_demo(question: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Invoke the single-node graph whose node calls MCP-sourced tools.
    Invoked with .ainvoke() since call_mcp_tools is async (it awaits
    the MCP client) — unlike this package's other concepts, which are
    all sync graph.invoke() calls.

    Returns {"question": str, "answer": str}.
    """
    graph = _get_graph(model)
    result = await graph.ainvoke({"question": question, "answer": ""})
    return {"question": question, "answer": result["answer"]}


def create_mcp_agent_cache():
    """
    Build an MCP-agent cache. Returns an async get_agent(model, memory_backend)
    closure — same shape as this file's create_graph_cache() and
    langchain_demo/mcp_client.py's create_mcp_agent_cache(). Async because
    building an agent needs one MCP round-trip (_client.get_tools) the
    first time a given (model, backend) pair is requested.
    """
    agents: dict[tuple[SupportedModel, CheckpointBackend], object] = {}

    async def get_agent(model: SupportedModel, memory_backend: CheckpointBackend):
        key = (model, memory_backend)
        if key not in agents:
            tools = await _client.get_tools(server_name=_SERVER_NAME)
            checkpointer = build_checkpointer(memory_backend)
            agents[key] = create_react_agent(
                get_chat_model(model), tools=tools, checkpointer=checkpointer, prompt=AGENT_SYSTEM_PROMPT
            )
        return agents[key]

    return get_agent


_get_mcp_agent = create_mcp_agent_cache()


async def run_mcp_agent_demo(
    question: str,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
    session_id: str | None = None,
) -> dict:
    """
    Fetch tools from the MCP server and hand them to LangGraph's prebuilt
    create_react_agent with a checkpointer attached — the memory-backed
    counterpart to run_mcp_client_demo's single-node graph above, and the
    LangGraph-native sibling of langchain_demo/mcp_client.py's
    run_mcp_agent_demo.

    `session_id` is LangGraph's `thread_id`: omit it for a single-shot,
    stateless call (a fresh thread is used and discarded); pass the same
    value across calls to accumulate multi-turn memory via the chosen
    `memory_backend`'s checkpointer.

    Returns {"session_id": str, "backend": str, "question": str,
             "final_answer": str,
             "steps": [{"type": "tool_call"|"tool_result"|"ai_message", ...}]}.

    Only memory_backend=memory is supported: this function is invoked via
    .ainvoke() (MCP tool calls are async), but checkpointers.py's redis/
    postgres builders return langgraph.checkpoint.redis.RedisSaver /
    langgraph.checkpoint.postgres.PostgresSaver — sync-only checkpointers
    that don't implement the async checkpoint interface .ainvoke() needs
    (verified: calling .ainvoke() with one raises a bare NotImplementedError
    from BaseCheckpointSaver.aget_tuple). Async-capable equivalents exist
    (langgraph.checkpoint.redis.AsyncRedisSaver,
    langgraph.checkpoint.postgres.aio.AsyncPostgresSaver) but aren't wired
    up here — raising a clear ValueError upfront beats either that bare
    NotImplementedError or silently mislabeling it as an unreachable MCP
    server.
    """
    if memory_backend is not CheckpointBackend.memory:
        raise ValueError(
            f"run_mcp_agent_demo only supports memory_backend=memory (got {memory_backend.value!r}) — "
            "it's invoked via .ainvoke(), and checkpointers.py's redis/postgres builders are "
            "sync-only checkpointers that don't support async. See this function's docstring."
        )
    agent = await _get_mcp_agent(model, memory_backend)
    thread_id = session_id or str(uuid.uuid4())
    result = await agent.ainvoke(
        {"messages": [("human", question)]},
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
        "question": question,
        "final_answer": messages[-1].content,
        "steps": steps,
    }
