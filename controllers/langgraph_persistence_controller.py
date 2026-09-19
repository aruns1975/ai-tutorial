from fastapi import APIRouter

from langgraph_demo.checkpointers import CheckpointBackend
from langgraph_demo.persistence import run_persistence_demo

router = APIRouter(prefix="/langgraph/persistence", tags=["langgraph-persistence"])


@router.post("/{session_id}")
def persistence(session_id: str, memory_backend: CheckpointBackend = CheckpointBackend.memory) -> dict:
    """Calls `langgraph_demo.persistence.run_persistence_demo`."""
    return run_persistence_demo(session_id, memory_backend)
