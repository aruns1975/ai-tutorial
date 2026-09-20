from fastapi import APIRouter, HTTPException
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel

from langchain_demo.mcp_client import (
    run_mcp_agent_demo,
    run_mcp_prompt_demo,
    run_mcp_resource_demo,
    run_mcp_tool_calling_demo,
)
from langchain_demo.react_agent import AgentMemoryBackend
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/mcp", tags=["langchain-mcp"])


class MessageRequest(BaseModel):
    message: str


class TopicRequest(BaseModel):
    topic: str


def _unreachable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=f"Couldn't reach the MCP server: {exc}. Start it with scripts/start_mcp_server.sh.",
    )


def _agent_error(exc: Exception) -> HTTPException:
    """
    GraphRecursionError means the agent itself got stuck re-calling tools
    without reaching a final answer (e.g. a follow-up question with no
    session_id, so it has no memory of what "the result" refers to) — a
    completely different failure from the MCP server being unreachable,
    so it gets its own message instead of being folded into _unreachable.
    """
    if isinstance(exc, GraphRecursionError):
        return HTTPException(
            status_code=500,
            detail=(
                f"{exc} The agent likely got stuck re-calling tools instead of answering — often "
                "because a follow-up question needs the same session_id as the earlier turn it "
                "refers to. This is not the MCP server being unreachable."
            ),
        )
    return _unreachable(exc)


@router.post("/tool-calling")
async def mcp_tool_calling(payload: MessageRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langchain_demo.mcp_client.run_mcp_tool_calling_demo`."""
    try:
        return await run_mcp_tool_calling_demo(payload.message, model)
    except Exception as exc:
        raise _unreachable(exc) from exc


@router.post("/agent")
async def mcp_agent(
    payload: MessageRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: AgentMemoryBackend = AgentMemoryBackend.memory,
    session_id: str | None = None,
) -> dict:
    """Calls `langchain_demo.mcp_client.run_mcp_agent_demo`."""
    try:
        return await run_mcp_agent_demo(payload.message, model, memory_backend, session_id)
    except Exception as exc:
        raise _agent_error(exc) from exc


@router.post("/prompt")
async def mcp_prompt(payload: TopicRequest) -> dict:
    """Calls `langchain_demo.mcp_client.run_mcp_prompt_demo`."""
    try:
        return await run_mcp_prompt_demo(payload.topic)
    except Exception as exc:
        raise _unreachable(exc) from exc


@router.get("/resource")
async def mcp_resource(uri: str = "data://ai-tutorial/models") -> dict:
    """Calls `langchain_demo.mcp_client.run_mcp_resource_demo`."""
    try:
        return await run_mcp_resource_demo(uri)
    except Exception as exc:
        raise _unreachable(exc) from exc
