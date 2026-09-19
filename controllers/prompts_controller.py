from fastapi import APIRouter
from pydantic import BaseModel

from langchain_demo.prompts_and_parsers import ConceptExplanation, run_pydantic_parser_demo, run_str_output_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/prompts", tags=["langchain-prompts"])


class PromptRequest(BaseModel):
    topic: str
    style: str = "concise"


class TopicRequest(BaseModel):
    topic: str


@router.post("")
def prompts_str_output(
    payload: PromptRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    structured_output: bool = True,
) -> dict:
    """Calls `langchain_demo.prompts_and_parsers.run_str_output_demo`."""
    return run_str_output_demo(payload.topic, payload.style, structured_output, model)


@router.post("/structured")
def prompts_pydantic_parser(payload: TopicRequest, model: SupportedModel = SupportedModel.llama3_2) -> ConceptExplanation:
    """Calls `langchain_demo.prompts_and_parsers.run_pydantic_parser_demo`."""
    return run_pydantic_parser_demo(payload.topic, model)
