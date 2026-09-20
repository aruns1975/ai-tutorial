from fastapi import APIRouter, HTTPException
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel

from langgraph_demo.checkpointers import CheckpointBackend
from langgraph_demo.mcp_client import run_mcp_agent_demo, run_mcp_client_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/mcp", tags=["langgraph-mcp"])


class QuestionRequest(BaseModel):
    question: str


def _unreachable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=f"Couldn't reach the MCP server: {exc}. Start it with scripts/start_mcp_server.sh.",
    )


@router.post("")
async def mcp_client(payload: QuestionRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langgraph_demo.mcp_client.run_mcp_client_demo`."""
    try:
        return await run_mcp_client_demo(payload.question, model)
    except Exception as exc:
        raise _unreachable(exc) from exc


@router.post("/agent")
async def mcp_agent(
    payload: QuestionRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
    session_id: str | None = None,
) -> dict:
    """Calls `langgraph_demo.mcp_client.run_mcp_agent_demo`."""
    try:
        return await run_mcp_agent_demo(payload.question, model, memory_backend, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GraphRecursionError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{exc} The agent likely got stuck re-calling tools instead of answering.",
        ) from exc
    except Exception as exc:
        raise _unreachable(exc) from exc
