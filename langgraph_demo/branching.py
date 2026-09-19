"""
Concept: Conditional edges / branching.

`add_conditional_edges` routes execution to a different node based on the
current state, instead of a fixed next step. Demonstrated with a small
router: classify a question as "math" or "general", then send it to a
node specialized for that category. Reuses tools/math_tools.py via
`bind_tools`, the same tool-calling pattern as langchain_demo/tool_calling.py.
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from langchain_demo.tool_utils import create_tool_caller
from models.chat_models.ollama_models import SupportedModel, get_chat_model
from tools.math_tools import adder, divider, multiplier, subtractor

_MATH_TOOLS = [adder, subtractor, multiplier, divider]
_call_tool = create_tool_caller(_MATH_TOOLS)


class RouterState(TypedDict):
    question: str
    category: str
    answer: str


def _build_graph(model: SupportedModel):
    llm = get_chat_model(model)

    def classify(state: RouterState) -> dict:
        response = llm.invoke(
            "Classify the following question as exactly one word, either "
            "'math' or 'general' — respond with nothing else.\n\n"
            f"Question: {state['question']}"
        )
        category = "math" if "math" in response.content.lower() else "general"
        return {"category": category}

    def route(state: RouterState) -> Literal["solve_math", "answer_general"]:
        return "solve_math" if state["category"] == "math" else "answer_general"

    def solve_math(state: RouterState) -> dict:
        ai_message = llm.bind_tools(_MATH_TOOLS).invoke(state["question"])
        if not ai_message.tool_calls:
            return {"answer": ai_message.content}
        tool_call = ai_message.tool_calls[0]
        result = _call_tool(tool_call["name"], tool_call["args"])
        return {"answer": f"{tool_call['name']}({tool_call['args']}) = {result}"}

    def answer_general(state: RouterState) -> dict:
        response = llm.invoke(state["question"])
        return {"answer": response.content}

    graph = StateGraph(RouterState)
    graph.add_node("classify", classify)
    graph.add_node("solve_math", solve_math)
    graph.add_node("answer_general", answer_general)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route)
    graph.add_edge("solve_math", END)
    graph.add_edge("answer_general", END)
    return graph.compile()


def create_graph_cache():
    graphs: dict[SupportedModel, object] = {}

    def get_graph(model: SupportedModel):
        if model not in graphs:
            graphs[model] = _build_graph(model)
        return graphs[model]

    return get_graph


_get_graph = create_graph_cache()


def run_branching_demo(question: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Invoke the classify -> route -> (solve_math | answer_general) graph.

    Returns {"question": str, "category": "math"|"general", "answer": str}.
    """
    graph = _get_graph(model)
    result = graph.invoke({"question": question, "category": "", "answer": ""})
    return {"question": question, "category": result["category"], "answer": result["answer"]}
