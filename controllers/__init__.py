from fastapi import APIRouter

from controllers.agents_controller import router as agents_router
from controllers.chains_controller import router as chains_router
from controllers.langgraph_branching_controller import router as langgraph_branching_router
from controllers.langgraph_cycles_controller import router as langgraph_cycles_router
from controllers.langgraph_interrupts_controller import router as langgraph_interrupts_router
from controllers.langgraph_mcp_controller import router as langgraph_mcp_router
from controllers.langgraph_multiagent_controller import router as langgraph_multiagent_router
from controllers.langgraph_persistence_controller import router as langgraph_persistence_router
from controllers.langgraph_rag_controller import router as langgraph_rag_router
from controllers.langgraph_stategraph_controller import router as langgraph_stategraph_router
from controllers.langgraph_streaming_controller import router as langgraph_streaming_router
from controllers.mcp_client_controller import router as mcp_client_router
from controllers.memory_controller import router as memory_router
from controllers.prompts_controller import router as prompts_router
from controllers.rag_controller import router as rag_router
from controllers.streaming_controller import router as streaming_router
from controllers.structured_output_controller import router as structured_output_router
from controllers.tool_calling_controller import router as tool_calling_router

router = APIRouter()
for sub_router in (
    # LangChain concepts (/langchain/**)
    prompts_router,
    chains_router,
    tool_calling_router,
    structured_output_router,
    memory_router,
    agents_router,
    rag_router,
    streaming_router,
    mcp_client_router,
    # LangGraph concepts (/langgraph/**)
    langgraph_stategraph_router,
    langgraph_branching_router,
    langgraph_cycles_router,
    langgraph_streaming_router,
    langgraph_interrupts_router,
    langgraph_persistence_router,
    langgraph_multiagent_router,
    langgraph_rag_router,
    langgraph_mcp_router,
):
    router.include_router(sub_router)
