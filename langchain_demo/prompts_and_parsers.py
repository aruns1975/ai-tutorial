"""
Concept: Prompts, LLM calls, and Output Parsers.

Demonstrates the three most foundational LangChain building blocks:
- PromptTemplate / ChatPromptTemplate to turn user input into a
  well-structured message for the model.
- Invoking a chat model directly.
- Two output-parser styles: a plain StrOutputParser (just the raw
  text) and a PydanticOutputParser (the model is instructed, via
  format_instructions embedded in the prompt, to emit JSON that gets
  parsed into a validated Pydantic object).

This is framework-agnostic — no FastAPI imports here. See
controllers/prompts_controller.py for the HTTP layer that calls these
functions.
"""

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from models.chat_models.ollama_models import SupportedModel, get_chat_model


class ConceptExplanation(BaseModel):
    summary: str = Field(description="A one or two sentence summary of the topic.")
    key_points: list[str] = Field(description="3 to 5 short bullet points about the topic.")


def run_str_output_demo(
    topic: str,
    style: str = "concise",
    structured_output: bool = True,
    model: SupportedModel = SupportedModel.llama3_2,
) -> dict:
    """
    Render a ChatPromptTemplate and invoke the LLM. When structured_output
    is True (the default), the chain ends with StrOutputParser(), so
    `response` is a plain string. When False, the parser is skipped
    entirely and `response` is the raw AIMessage the model returned —
    this contrast is exactly what StrOutputParser is for: without it you
    get the full message object (content plus metadata like token usage
    and stop reason), with it you get just the text.

    Returns {"prompt": <rendered prompt text>, "structured_output": bool,
             "model": str,
             "response": <str, if structured_output> | <AIMessage, otherwise>}.
    """
    llm = get_chat_model(model)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful teaching assistant. Answer in a {style} way."),
            ("human", "Explain: {topic}"),
        ]
    )
    base_chain = prompt | llm
    chain = base_chain | StrOutputParser() if structured_output else base_chain
    rendered = prompt.format(style=style, topic=topic)
    response = chain.invoke({"style": style, "topic": topic})
    return {"prompt": rendered, "structured_output": structured_output, "model": model, "response": response}


def run_pydantic_parser_demo(topic: str, model: SupportedModel = SupportedModel.llama3_2) -> ConceptExplanation:
    """
    Render a prompt that embeds PydanticOutputParser's format
    instructions, invoke the LLM, and parse the raw text into a
    validated ConceptExplanation object.
    """
    llm = get_chat_model(model)
    parser = PydanticOutputParser(pydantic_object=ConceptExplanation)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You explain topics for a JSON API. Respond with ONLY a single JSON "
                "object containing REAL VALUES for the fields \"summary\" and "
                "\"key_points\" — never return the schema/field definitions "
                "themselves. Example of a correctly filled response: "
                '{{"summary": "Example summary sentence.", '
                '"key_points": ["point one", "point two", "point three"]}}'
                "\n\n{format_instructions}",
            ),
            ("human", "Explain: {topic}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())
    # format="json" forces Ollama to emit syntactically valid JSON (it
    # doesn't enforce our schema, but it stops small models like
    # llama3.2 from occasionally emitting truncated/malformed JSON).
    chain = prompt | llm.bind(format="json") | parser
    return chain.invoke({"topic": topic})
