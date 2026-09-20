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

run_mcp_agent_demo is the memory-backed counterpart — a genuinely
LangGraph-native reason/act loop, hand-built as an explicit two-node
StateGraph (call_model <-> call_tools) with a checkpointer attached at
compile time, deliberately NOT langgraph.prebuilt.create_react_agent
(used by langchain_demo/mcp_client.py's own run_mcp_agent_demo). That
prebuilt hides the loop behind one call; a langgraph_demo concept should
show the loop itself, same reasoning docs/langgraph/07-multi-agent.md
already gives for hand-building a multi-graph system instead of relying
on a prebuilt agent. It reuses this package's own checkpointers.py
(CheckpointBackend/build_checkpointer) — langgraph_demo's shared
persistence story, per that file's docstring — rather than
langchain_demo.react_agent's AgentMemoryBackend/per-backend files, which
is the deliberate cross-package split documented in the project root
CLAUDE.md. It DOES reuse langchain_demo.react_agent's AGENT_SYSTEM_PROMPT
directly, though: that's a small, genuinely generic instruction (not
persistence logic).

Hand-building the loop also buys something a prebuilt can't easily give
you: call_tools checks the accumulated message history for a tool
already called with the exact same name/args and, if found, reuses that
result instead of re-invoking the tool. AGENT_SYSTEM_PROMPT alone
(see docs/langchain/06-react-agents.md) was found to reduce but not
eliminate a weaker model (gemma4) re-calling a tool with identical
arguments several times in a longer conversation — this is a hard,
deterministic backstop for exactly that case, not achievable by prompting
alone.
"""

import os
import uuid
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, START, MessagesState, StateGraph

from langchain_demo.react_agent import AGENT_SYSTEM_PROMPT
from langgraph_demo.checkpointers import CheckpointBackend, build_checkpointer
from models.chat_models.ollama_models import SupportedModel, get_chat_model

_SERVER_NAME = "ai_tutorial"
_MCP_SERVER_URL = f"http://localhost:{os.getenv('MCP_SERVER_PORT', '18383')}/mcp"

# Caps reason/act rounds per run_mcp_agent_demo call, instead of
# LangGraph's default 25. call_tools's repeat-call cache (see
# _find_prior_tool_result) makes a repeated request CHEAP — no real tool
# re-invocation — but each ask still consumes one graph step, so a model
# that keeps re-asking can still exhaust this budget; verified live with
# gemma4 on a 3-turn conversation needing 2 new tool calls in the final
# turn. 20 (vs. an even tighter number) gives that case enough headroom
# to converge most of the time while still failing well before
# LangGraph's own default of 25.
_AGENT_RECURSION_LIMIT = 20

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


def _find_prior_tool_result(messages: list, name: str, args: dict) -> str | None:
    """
    Look for a tool call already made earlier in `messages` with the
    same name and args, and return its already-computed result if
    found — the hard, deterministic half of the repeat-call guard (the
    other half is AGENT_SYSTEM_PROMPT asking the model not to bother
    re-calling in the first place).
    """
    for i, message in enumerate(messages):
        if getattr(message, "type", None) == "ai" and getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                if tool_call["name"] == name and tool_call["args"] == args:
                    for later in messages[i + 1 :]:
                        if getattr(later, "type", None) == "tool" and later.tool_call_id == tool_call["id"]:
                            return later.content
    return None


def _build_agent_graph(model: SupportedModel, memory_backend: CheckpointBackend):
    llm = get_chat_model(model)

    async def call_model(state: MessagesState) -> dict:
        tools = await _client.get_tools(server_name=_SERVER_NAME)
        response = llm.bind_tools(tools).invoke([SystemMessage(content=AGENT_SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    async def call_tools(state: MessagesState) -> dict:
        tools = await _client.get_tools(server_name=_SERVER_NAME)
        tools_by_name = {tool.name: tool for tool in tools}
        last_message = state["messages"][-1]

        tool_messages = []
        for tool_call in last_message.tool_calls:
            cached_result = _find_prior_tool_result(state["messages"][:-1], tool_call["name"], tool_call["args"])
            if cached_result is not None:
                result = cached_result
            else:
                tool = tools_by_name[tool_call["name"]]
                try:
                    result = await tool.ainvoke(tool_call["args"])
                except Exception as exc:
                    result = f"Error calling tool '{tool_call['name']}': {exc}"
            tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
        return {"messages": tool_messages}

    def route_after_model(state: MessagesState) -> Literal["call_tools", "__end__"]:
        return "call_tools" if state["messages"][-1].tool_calls else END

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    graph.add_node("call_tools", call_tools)
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", route_after_model)
    graph.add_edge("call_tools", "call_model")
    return graph.compile(checkpointer=build_checkpointer(memory_backend))


def create_mcp_agent_cache():
    """
    Build an MCP-agent cache. Returns a get_agent(model, memory_backend)
    closure — same shape as this file's create_graph_cache(). Sync: unlike
    an earlier version of this function built on create_react_agent,
    compiling this graph needs no MCP round-trip up front — tools are
    fetched live inside call_model/call_tools on every turn instead of
    being baked in at compile time, matching run_mcp_client_demo's
    single-node graph above (and meaning a mcp_server/tools.py change is
    picked up without an app restart).
    """
    graphs: dict[tuple[SupportedModel, CheckpointBackend], object] = {}

    def get_agent(model: SupportedModel, memory_backend: CheckpointBackend):
        key = (model, memory_backend)
        if key not in graphs:
            graphs[key] = _build_agent_graph(model, memory_backend)
        return graphs[key]

    return get_agent


_get_agent_graph = create_mcp_agent_cache()


async def run_mcp_agent_demo(
    question: str,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
    session_id: str | None = None,
) -> dict:
    """
    Invoke the hand-built call_model <-> call_tools loop (see
    _build_agent_graph above) — the LangGraph-native counterpart to
    langchain_demo/mcp_client.py's create_react_agent-based
    run_mcp_agent_demo.

    `session_id` is LangGraph's `thread_id`: omit it for a single-shot,
    stateless call (a fresh thread is used and discarded); pass the same
    value across calls to accumulate multi-turn memory via the chosen
    `memory_backend`'s checkpointer.

    Returns {"session_id": str, "backend": str, "question": str,
             "final_answer": str,
             "steps": [{"type": "tool_call"|"tool_result"|"ai_message", ...}]}.

    Only memory_backend=memory is supported: this graph is invoked via
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
    graph = _get_agent_graph(model, memory_backend)
    thread_id = session_id or str(uuid.uuid4())
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=question)]},
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
