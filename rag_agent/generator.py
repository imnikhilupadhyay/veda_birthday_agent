"""RAG Agent Generator"""

from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)

from rag_agent.config import LLM_MODEL, OPENAI_API_KEY
from rag_agent.chain import RAGChain
from rag_agent.prompts import RAG_PROMPT


tool_manager = RAGChain()


def convert_gradio_history(history: list):
    messages = []

    if not history:
        return messages

    for item in history:
        if item is None:
            continue

        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")

            if not content:
                continue

            if role == "user":
                messages.append(HumanMessage(content=str(content)))
            elif role == "assistant":
                messages.append(AIMessage(content=str(content)))

        elif isinstance(item, (list, tuple)) and len(item) == 2:
            user_msg, assistant_msg = item

            if user_msg:
                messages.append(HumanMessage(content=str(user_msg)))

            if assistant_msg:
                messages.append(AIMessage(content=str(assistant_msg)))

    return messages


def tool_schema_manager(tools) -> List[dict]:
    tool_definitions = []

    for tool in tools:
        if tool.name == "condense_question":
            parameters = {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The user's current question",
                    },
                    "conversation_history": {
                        "type": "array",
                        "description": "Conversation history",
                    },
                },
                "required": ["question"],
            }
        else:
            parameters = {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "The input question to the tool",
                    }
                },
                "required": ["input"],
            }

        tool_definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                },
            }
        )

    return tool_definitions


def generator_agent(question: str, history: list | None = None) -> str:
    if not question:
        return "Please ask me something about Veda's birthday."

    generator_llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    tools = tool_manager.get_tools()
    tool_definition = tool_schema_manager(tools)

    generator_llm_with_tools = generator_llm.bind_tools(tool_definition)

    conversation_messages = convert_gradio_history(history)

    messages = [SystemMessage(content=RAG_PROMPT)]
    messages.extend(conversation_messages)
    messages.append(HumanMessage(content=question))

    last_response_content = ""

    for _ in range(4):
        response = generator_llm_with_tools.invoke(messages)
        messages.append(response)

        if response.content:
            last_response_content = response.content

        if not response.tool_calls:
            final_response = response.content or last_response_content

            if final_response:
                return str(final_response)

            return "Sorry, I could not generate a response."

        tool_names = [tool_call["name"] for tool_call in response.tool_calls]
        print(f"Chaining Tools -> {' | '.join(tool_names)}", flush=True)

        for call in response.tool_calls:
            tool_name = call["name"]
            args = call.get("args", {})

            print(f"\n🔧 Calling tool: {tool_name}", flush=True)
            print(f"   Args: {args}", flush=True)

            selected_tool = None

            for tool in tools:
                if tool.name == tool_name:
                    selected_tool = tool
                    break

            if selected_tool is None:
                tool_output = f"Tool {tool_name} not found."

            elif tool_name == "condense_question":
                tool_output = selected_tool.invoke(
                    {
                        "question": args.get("question", question),
                        "conversation_history": conversation_messages,
                    }
                )

            else:
                tool_output = selected_tool.invoke(
                    args.get("input", question)
                )

            if tool_output is None:
                tool_output = "No output from tool."

            messages.append(
                ToolMessage(
                    name=tool_name,
                    content=str(tool_output),
                    tool_call_id=call["id"],
                )
            )

    return (
        last_response_content
        or "I could not complete the answer because maximum tool iterations were reached."
    )