"""
Concept: Persistence / checkpointers (standalone).

Contrast with langchain_demo/react_agent.py: that demo shows a
*prebuilt* agent gaining memory when you hand `create_react_agent` a
checkpointer. This one shows the same mechanic on a completely plain,
hand-written StateGraph with no LLM and no tools at all — a checkpointer
is a property of the *graph*, not something special about agents.
Any StateGraph gets persistent, resumable state across separate
`.invoke()` calls just by compiling it with `checkpointer=...` and
reusing the same `thread_id`.

The graph here is a trivial counter: each call increments a count and
appends to a history list. Call it twice with the same session_id and a
memory_backend of "redis" or "postgres", and the second call's count
picks up where the first left off — even across an app restart.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from langgraph_demo.checkpointers import CheckpointBackend, build_checkpointer


class CounterState(TypedDict):
    count: int
    history: list[str]


def _increment(state: CounterState) -> dict:
    # .get() with defaults: on a brand-new thread there's no checkpointed
    # state yet, so these keys won't exist in the incoming state at all.
    count = state.get("count", 0) + 1
    history = state.get("history", []) + [f"incremented to {count}"]
    return {"count": count, "history": history}


def _build_graph(memory_backend: CheckpointBackend):
    graph = StateGraph(CounterState)
    graph.add_node("increment", _increment)
    graph.add_edge(START, "increment")
    graph.add_edge("increment", END)
    return graph.compile(checkpointer=build_checkpointer(memory_backend))


def create_graph_cache():
    graphs: dict[CheckpointBackend, object] = {}

    def get_graph(memory_backend: CheckpointBackend):
        if memory_backend not in graphs:
            graphs[memory_backend] = _build_graph(memory_backend)
        return graphs[memory_backend]

    return get_graph


_get_graph = create_graph_cache()


def run_persistence_demo(session_id: str, memory_backend: CheckpointBackend = CheckpointBackend.memory) -> dict:
    """
    Invoke the counter graph for a session. Deliberately invokes with an
    EMPTY dict — not {"count": 0, ...} — so the checkpointer's persisted
    state (if any) is what the node reads; passing an explicit count
    would overwrite the checkpoint back to zero every time instead of
    accumulating.

    Returns {"session_id": str, "backend": str, "count": int, "history": list[str]}.
    """
    graph = _get_graph(memory_backend)
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke({}, config)
    return {
        "session_id": session_id,
        "backend": memory_backend.value,
        "count": result["count"],
        "history": result["history"],
    }
