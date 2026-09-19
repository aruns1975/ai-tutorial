from fastapi import APIRouter
from pydantic import BaseModel

from langchain_demo.structured_output import Recipe, run_structured_output_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/structured-output", tags=["langchain-structured-output"])


class DishRequest(BaseModel):
    dish: str


@router.post("")
def structured_output(payload: DishRequest, model: SupportedModel = SupportedModel.llama3_2) -> Recipe:
    """Calls `langchain_demo.structured_output.run_structured_output_demo`."""
    return run_structured_output_demo(payload.dish, model)
