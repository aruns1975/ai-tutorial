"""
Concept: StateGraph basics.

The foundational LangGraph building block: a typed state schema, nodes
(plain functions that take the state and return a partial update), and
edges wiring nodes together into a graph you compile and invoke.

Demonstrates a minimal two-node linear graph: generate a fact about a
topic, then generate a joke about that fact. Contrast with
langchain_demo/lcel_chains.py's `prompt | llm | parser` — LCEL chains are
linear pipes; a StateGraph is nodes + edges over a shared, typed state
that any node can read/write, which is what makes branching (see
branching.py) and cycles (see cycles.py) possible.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from models.chat_models.ollama_models import SupportedModel, get_chat_model


class FactJokeState(TypedDict):
    topic: str
    fact: str
    joke: str


def _build_graph(model: SupportedModel):
    llm = get_chat_model(model)

    def generate_fact(state: FactJokeState) -> dict:
        response = llm.invoke(f"Give one interesting, concise fact about {state['topic']}.")
        return {"fact": response.content}

    def generate_joke(state: FactJokeState) -> dict:
        response = llm.invoke(f"Write one short joke based on this fact: {state['fact']}")
        return {"joke": response.content}

    graph = StateGraph(FactJokeState)
    graph.add_node("generate_fact", generate_fact)
    graph.add_node("generate_joke", generate_joke)
    graph.add_edge(START, "generate_fact")
    graph.add_edge("generate_fact", "generate_joke")
    graph.add_edge("generate_joke", END)
    return graph.compile()


def create_graph_cache():
    """Build once, cache per model — same closure-factory shape used
    throughout this project (see langchain_demo/react_agent.py's
    create_agent_cache() for the fuller closure-vs-dict writeup)."""
    graphs: dict[SupportedModel, object] = {}

    def get_graph(model: SupportedModel):
        if model not in graphs:
            graphs[model] = _build_graph(model)
        return graphs[model]

    return get_graph


get_fact_joke_graph = create_graph_cache()


def run_stategraph_demo(topic: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Invoke the two-node fact -> joke graph and return the final state.

    Returns {"topic": str, "fact": str, "joke": str}.
    """
    graph = get_fact_joke_graph(model)
    result = graph.invoke({"topic": topic, "fact": "", "joke": ""})
    return {"topic": topic, "fact": result["fact"], "joke": result["joke"]}
