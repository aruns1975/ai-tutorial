"""
Concept: Human-in-the-loop / interrupts.

`interrupt()` pauses a graph mid-node and surfaces a value to the caller;
the caller resumes execution later with `Command(resume=...)`. This is a
distinctly LangGraph feature with no equivalent in the plain LangChain
concepts elsewhere in this project — a chain either finishes or it
doesn't, but a graph can pause indefinitely awaiting a human decision.

Interrupts require a checkpointer (the paused state has to be persisted
somewhere between the pausing call and the resuming call) — this concept
reuses langgraph_demo/checkpointers.py, the same three backends as
persistence.py.

Demonstrated with a draft -> request_approval -> finalize graph: draft a
short reply, pause for a human approve/reject decision, then finalize
accordingly.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from langgraph_demo.checkpointers import CheckpointBackend, build_checkpointer
from models.chat_models.ollama_models import SupportedModel, get_chat_model


class ApprovalState(TypedDict):
    request: str
    draft: str
    approved: bool
    result: str


def _build_graph(model: SupportedModel, memory_backend: CheckpointBackend):
    llm = get_chat_model(model)

    def draft(state: ApprovalState) -> dict:
        response = llm.invoke(f"Draft a short (1-2 sentence) reply to: {state['request']}")
        return {"draft": response.content}

    def request_approval(state: ApprovalState) -> dict:
        decision = interrupt({"question": "Approve this draft?", "draft": state["draft"]})
        return {"approved": bool(decision)}

    def finalize(state: ApprovalState) -> dict:
        if state["approved"]:
            return {"result": f"[SENT] {state['draft']}"}
        return {"result": "[REJECTED] Draft was not sent."}

    graph = StateGraph(ApprovalState)
    graph.add_node("draft", draft)
    graph.add_node("request_approval", request_approval)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "request_approval")
    graph.add_edge("request_approval", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=build_checkpointer(memory_backend))


def create_graph_cache():
    graphs: dict[tuple[SupportedModel, CheckpointBackend], object] = {}

    def get_graph(model: SupportedModel, memory_backend: CheckpointBackend):
        key = (model, memory_backend)
        if key not in graphs:
            graphs[key] = _build_graph(model, memory_backend)
        return graphs[key]

    return get_graph


_get_graph = create_graph_cache()


def start_approval_demo(
    request: str,
    session_id: str,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
) -> dict:
    """
    Start the graph: draft a reply, then pause at request_approval and
    surface the draft for a human decision.

    Returns {"session_id": str, "status": "waiting_for_approval",
             "draft": str} — call resume_approval_demo with the same
    session_id to continue.
    """
    graph = _get_graph(model, memory_backend)
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke({"request": request, "draft": "", "approved": False, "result": ""}, config)
    interrupt_payload = result["__interrupt__"][0].value
    return {"session_id": session_id, "status": "waiting_for_approval", "draft": interrupt_payload["draft"]}


def resume_approval_demo(
    session_id: str,
    approved: bool,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
) -> dict:
    """
    Resume a paused graph with a human's approve/reject decision.

    Returns {"session_id": str, "status": "done", "result": str}.

    Raises ValueError if there's no pending interrupt for this
    (session_id, model, memory_backend) combination — most commonly
    because `model`/`memory_backend` didn't match what start_approval_demo
    was called with (each (model, memory_backend) pair has its own
    compiled graph and, for memory_backend=memory, its own separate
    in-process checkpoint store).
    """
    graph = _get_graph(model, memory_backend)
    config = {"configurable": {"thread_id": session_id}}
    if not graph.get_state(config).next:
        raise ValueError(
            f"No pending approval found for session_id={session_id!r} with "
            f"model={model.value!r}, memory_backend={memory_backend.value!r}. "
            "Call start_approval_demo with the same session_id, model, and "
            "memory_backend first."
        )
    result = graph.invoke(Command(resume=approved), config)
    return {"session_id": session_id, "status": "done", "result": result["result"]}
