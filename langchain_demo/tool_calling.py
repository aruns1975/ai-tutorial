"""
Concept: Tool calling / function calling.

Binds a subset of the existing tools/ functions to the chat model via
`llm.bind_tools([...])`. The model decides which tool(s) to call and
with what arguments; this code executes the chosen tool(s) locally
and feeds the results back to the model for a final natural-language
answer.

Reuses tools/*.py as-is — those modules' rich docstrings (the
"Call this tool for..." + few-shot examples convention) are exactly
what a tool-calling model reads to decide which function fits a
request.
"""

from langchain_core.messages import HumanMessage, ToolMessage

from langchain_demo.tool_utils import create_tool_caller
from models.chat_models.ollama_models import SupportedModel, get_chat_model
from tools.math_tools import adder, divider, multiplier, subtractor
from tools.string_tools import is_palindrome, reverse_text, word_count
from tools.search_tools import web_search

_TOOLS = [adder, subtractor, multiplier, divider, reverse_text, word_count, is_palindrome, web_search]
_call_tool = create_tool_caller(_TOOLS)


def run_tool_calling_demo(user_message: str, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """
    Send user_message to the tool-bound model. If it responds with
    tool_calls, execute each one via _call_tool with the model-supplied
    arguments, feed the results back as ToolMessages, and re-invoke the
    model for a final natural-language answer.

    Returns {"tool_calls": [{"name": str, "args": dict, "result": Any}],
             "final_answer": str}.
    """
    llm = get_chat_model(model)
    messages = [HumanMessage(content=user_message)]
    ai_message = llm.bind_tools(_TOOLS).invoke(messages)
    messages.append(ai_message)

    tool_calls_trace = []
    for tool_call in ai_message.tool_calls:
        result = _call_tool(tool_call["name"], tool_call["args"])
        tool_calls_trace.append({"name": tool_call["name"], "args": tool_call["args"], "result": result})
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    if not tool_calls_trace:
        return {"tool_calls": [], "final_answer": ai_message.content}

    final_message = llm.invoke(messages)
    return {"tool_calls": tool_calls_trace, "final_answer": final_message.content}
