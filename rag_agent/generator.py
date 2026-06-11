"""RAG Agent Generator"""

from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from rag_agent.config import LLM_MODEL, OPENAI_API_KEY
from rag_agent.chain import RAGChain
from rag_agent.prompts import RAG_PROMPT


tool_manager = RAGChain()


def convert_gradio_history(history: list):
    messages = []

    if not history:
        return messages

    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        elif isinstance(item, (list, tuple)) and len(item) == 2:
            user_msg, assistant_msg = item

            if user_msg:
                messages.append(HumanMessage(content=user_msg))
            if assistant_msg:
                messages.append(AIMessage(content=assistant_msg))

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
                        "description": "The user's current question"
                    },
                    "conversation_history": {
                        "type": "array",
                        "description": "Conversation history as messages"
                    }
                },
                "required": ["question", "conversation_history"]
            }
        else:
            parameters = {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "The input question to the tool"
                    }
                },
                "required": ["input"]
            }

        tool_definitions.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters
            }
        })

    return tool_definitions


def generator_agent(question: str, history: list | None = None) -> str:
    generator_llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY
    )

    tools = tool_manager.get_tools()
    tool_definition = tool_schema_manager(tools)

    generator_llm_with_tools = generator_llm.bind_tools(tool_definition)

    conversation_messages = convert_gradio_history(history)

    messages = [SystemMessage(content=RAG_PROMPT)]
    messages.extend(conversation_messages)
    messages.append(HumanMessage(content=question))

    for _ in range(3):
        response = generator_llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        tool_names = [tool_call["name"] for tool_call in response.tool_calls]
        print(f"Chaining Tools -> {' | '.join(tool_names)}")

        for call in response.tool_calls:
            tool_name = call["name"]
            args = call["args"]

            print(f"\n🔧 Calling tool: {tool_name}")
            print(f"   Args: {args}")

            selected_tool = None

            for tool in tools:
                if tool.name == tool_name:
                    selected_tool = tool
                    break

            if selected_tool is None:
                tool_output = f"Tool {tool_name} not found."

            elif tool_name == "condense_question":
                tool_output = selected_tool.invoke({
                    "question": args.get("question", question),
                    "conversation_history": conversation_messages
                })

            else:
                tool_output = selected_tool.invoke(args.get("input", ""))

            messages.append(
                ToolMessage(
                    name=tool_name,
                    content=str(tool_output),
                    tool_call_id=call["id"]
                )
            )

    return "I could not complete the answer because maximum tool iterations were reached."