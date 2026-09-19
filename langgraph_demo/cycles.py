"""
Concept: Cycles / loops.

A graph edge can point back to a node that already ran — LangGraph
doesn't require a DAG. Demonstrated with a retry loop: ask the model for
a one-sentence description, and if it comes back longer than
`max_words`, loop back and ask again (up to `max_attempts`), instead of
accepting the first answer unconditionally.

Contrast with branching.py: that graph's conditional edge always reaches
END after one specialist node runs. This one's conditional edge can send
execution back to a node already visited — the actual "cycle" a cyclic
graph is named for.
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from models.chat_models.ollama_models import SupportedModel, get_chat_model


class RefineState(TypedDict):
    topic: str
    max_words: int
    max_attempts: int
    attempt: int
    text: str
    word_count: int


def _build_graph(model: SupportedModel):
    llm = get_chat_model(model)

    def generate(state: RefineState) -> dict:
        feedback = ""
        if state["attempt"] > 0:
            feedback = (
                f" Your previous attempt (\"{state['text']}\") was {state['word_count']} "
                f"words — too long. Try again, shorter."
            )
        response = llm.invoke(
            f"Describe {state['topic']} in {state['max_words']} words or fewer. "
            "Respond with ONLY the description, no preamble." + feedback
        )
        text = response.content.strip()
        return {"text": text, "word_count": len(text.split()), "attempt": state["attempt"] + 1}

    def should_continue(state: RefineState) -> Literal["generate", "__end__"]:
        if state["word_count"] <= state["max_words"] or state["attempt"] >= state["max_attempts"]:
            return END
        return "generate"

    graph = StateGraph(RefineState)
    graph.add_node("generate", generate)
    graph.add_edge(START, "generate")
    graph.add_conditional_edges("generate", should_continue)
    return graph.compile()


def create_graph_cache():
    graphs: dict[SupportedModel, object] = {}

    def get_graph(model: SupportedModel):
        if model not in graphs:
            graphs[model] = _build_graph(model)
        return graphs[model]

    return get_graph


_get_graph = create_graph_cache()


def run_cycles_demo(
    topic: str,
    max_words: int = 8,
    max_attempts: int = 5,
    model: SupportedModel = SupportedModel.llama3_2,
) -> dict:
    """
    Invoke the generate -> should_continue -> (loop back | end) graph.

    Returns {"topic": str, "text": str, "word_count": int,
             "attempts_used": int, "met_target": bool}.
    """
    graph = _get_graph(model)
    result = graph.invoke(
        {"topic": topic, "max_words": max_words, "max_attempts": max_attempts, "attempt": 0, "text": "", "word_count": 0}
    )
    return {
        "topic": topic,
        "text": result["text"],
        "word_count": result["word_count"],
        "attempts_used": result["attempt"],
        "met_target": result["word_count"] <= max_words,
    }
