"""
Concept: Multi-agent / subgraphs.

A compiled StateGraph can be used directly as a node in another graph —
a "subgraph". This is what a multi-agent system actually is in
LangGraph: each specialist agent is its own independently-built,
independently-testable graph; a supervisor graph routes to whichever
specialist fits the request and treats it as a single node.

Contrast with branching.py: that demo's specialist logic is a single
plain function per branch. Here, each specialist (`math_specialist`,
`writing_specialist`) is its own fully compiled StateGraph — you could
run/test either one in isolation before ever wiring it into the
supervisor.
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from langchain_demo.tool_utils import create_tool_caller
from models.chat_models.ollama_models import SupportedModel, get_chat_model
from tools.math_tools import adder, divider, multiplier, subtractor

_MATH_TOOLS = [adder, subtractor, multiplier, divider]
_call_tool = create_tool_caller(_MATH_TOOLS)


class SupervisorState(TypedDict):
    request: str
    category: str
    answer: str


def _build_math_specialist(model: SupportedModel):
    """A standalone graph that could be invoked on its own — nothing
    about it knows it will later be used as a subgraph node."""
    llm = get_chat_model(model)

    def solve(state: SupervisorState) -> dict:
        ai_message = llm.bind_tools(_MATH_TOOLS).invoke(state["request"])
        if not ai_message.tool_calls:
            return {"answer": ai_message.content}
        tool_call = ai_message.tool_calls[0]
        result = _call_tool(tool_call["name"], tool_call["args"])
        return {"answer": f"{tool_call['name']}({tool_call['args']}) = {result}"}

    graph = StateGraph(SupervisorState)
    graph.add_node("solve", solve)
    graph.add_edge(START, "solve")
    graph.add_edge("solve", END)
    return graph.compile()


def _build_writing_specialist(model: SupportedModel):
    """A second standalone graph, equally usable on its own."""
    llm = get_chat_model(model)

    def write(state: SupervisorState) -> dict:
        response = llm.invoke(f"Write a short, creative response to: {state['request']}")
        return {"answer": response.content}

    graph = StateGraph(SupervisorState)
    graph.add_node("write", write)
    graph.add_edge(START, "write")
    graph.add_edge("write", END)
    return graph.compile()


def _build_supervisor_graph(model: SupportedModel):
    llm = get_chat_model(model)
    math_specialist = _build_math_specialist(model)
    writing_specialist = _build_writing_specialist(model)

    def classify(state: SupervisorState) -> dict:
        response = llm.invoke(
            "Classify the following request as exactly one word, either "
            "'math' or 'writing' — respond with nothing else.\n\n"
            f"Request: {state['request']}"
        )
        category = "math" if "math" in response.content.lower() else "writing"
        return {"category": category}

    def route(state: SupervisorState) -> Literal["math_specialist", "writing_specialist"]:
        return "math_specialist" if state["category"] == "math" else "writing_specialist"

    graph = StateGraph(SupervisorState)
    graph.add_node("classify", classify)
    graph.add_node("math_specialist", math_specialist)  # a compiled graph, used as a node
    graph.add_node("writing_specialist", writing_specialist)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route)
    graph.add_edge("math_specialist", END)
    graph.add_edge("writing_specialist", END)
    return graph.compile()


def create_graph_cache():
    graphs: dict[SupportedModel, object] = {}

    def get_graph(model: SupportedModel):
        if model not in graphs:
            graphs[model] = _build_supervisor_graph(model)
        return graphs[model]

    return get_graph


_get_graph = create_graph_cache()


def run_multi_agent_demo(request: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Invoke the supervisor graph, which delegates to whichever specialist
    subgraph fits the request.

    Returns {"request": str, "delegated_to": "math_specialist"|"writing_specialist", "answer": str}.
    """
    graph = _get_graph(model)
    result = graph.invoke({"request": request, "category": "", "answer": ""})
    delegated_to = "math_specialist" if result["category"] == "math" else "writing_specialist"
    return {"request": request, "delegated_to": delegated_to, "answer": result["answer"]}
