"""
Concept: LCEL Chains (Runnables, pipe syntax).

The LangChain Expression Language (LCEL) lets you compose Runnables
with the `|` operator. This file demonstrates:
- A simple linear pipe chain: prompt | llm | output_parser.
- RunnableParallel, running two independent branches over the same
  input concurrently.
- RunnableLambda, a plain Python function lifted into the chain.
- RunnablePassthrough, carrying the original input through unchanged
  alongside derived values.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough

from models.chat_models.ollama_models import SupportedModel, get_chat_model


def run_pipe_chain_demo(text: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    A minimal `prompt | llm | StrOutputParser()` pipe chain.

    Returns {"result": str}.
    """
    llm = get_chat_model(model)
    prompt = ChatPromptTemplate.from_messages(
        [("human", "Rewrite the following text so a 10-year-old could understand it:\n\n{text}")]
    )
    chain = prompt | llm | StrOutputParser()
    return {"result": chain.invoke({"text": text})}


def run_parallel_chain_demo(topic: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Fan a single topic out into two independent LLM branches
    (summary + follow-up questions) using RunnableParallel, post-process
    the questions branch with a RunnableLambda, and carry the original
    topic through unchanged with RunnablePassthrough.

    Returns {"summary": str, "questions": list[str], "original_topic": str}.
    """
    llm = get_chat_model(model)
    summary_prompt = ChatPromptTemplate.from_messages(
        [("human", "Summarize the topic '{topic}' in one sentence.")]
    )
    questions_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "human",
                "List 3 follow-up questions about '{topic}', one per line, "
                "with no numbering or extra commentary.",
            )
        ]
    )

    to_prompt_input = RunnableLambda(lambda topic: {"topic": topic})
    split_lines = RunnableLambda(lambda text: [line.strip("- ").strip() for line in text.splitlines() if line.strip()])

    parallel_chain = RunnableParallel(
        summary=to_prompt_input | summary_prompt | llm | StrOutputParser(),
        questions=to_prompt_input | questions_prompt | llm | StrOutputParser() | split_lines,
        original_topic=RunnablePassthrough(),
    )

    # A plain string in -> each branch above adapts it as needed;
    # RunnablePassthrough hands the same string straight through unchanged.
    result = parallel_chain.invoke(topic)
    return {
        "summary": result["summary"],
        "questions": result["questions"],
        "original_topic": result["original_topic"],
    }
