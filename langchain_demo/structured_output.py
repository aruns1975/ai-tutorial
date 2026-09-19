"""
Concept: Structured output.

Contrast with prompts_and_parsers.run_pydantic_parser_demo: instead of
hand-writing format instructions into the prompt and parsing raw text
afterward, `with_structured_output()` handles both steps for you,
binding the schema directly into the model call so the model is
constrained to return data matching it.
"""

from pydantic import BaseModel, Field

from models.chat_models.ollama_models import SupportedModel, get_chat_model


class Recipe(BaseModel):
    name: str = Field(description="The name of the dish.")
    ingredients: list[str] = Field(description="List of ingredients with quantities.")
    steps: list[str] = Field(description="Ordered list of preparation steps.")
    estimated_minutes: int = Field(description="Estimated total time to prepare, in minutes.")


def run_structured_output_demo(dish: str, model: SupportedModel = SupportedModel.llama3_2) -> Recipe:
    """
    Invoke the with_structured_output()-bound model and return a
    validated Recipe object.
    """
    llm = get_chat_model(model)
    return llm.with_structured_output(Recipe).invoke(f"Give me a simple recipe for {dish}.")
