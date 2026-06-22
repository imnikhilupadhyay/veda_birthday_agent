"""RAG Agent Generator"""

from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from rag_agent.config import LLM_MODEL, OPENAI_API_KEY
from rag_agent.chain import RAGChain
from rag_agent.prompts import RAG_PROMPT


tool_manager = RAGChain()


def convert_history_to_messages(history: list | None):
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
                    }
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


def _get_tool_by_name(tools, tool_name: str):
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None


def _execute_tool(tool_name: str, args: dict, tools, question: str, conversation_messages: list):
    selected_tool = _get_tool_by_name(tools, tool_name)

    if selected_tool is None:
        return f"Tool {tool_name} not found."

    if tool_name == "condense_question":
        return selected_tool.invoke(
            {
                "question": args.get("question", question),
                "conversation_history": conversation_messages,
            }
        )

    return selected_tool.invoke(args.get("input", question))


def generator_agent(question: str, history: list | None = None) -> str:
    """Non-streaming fallback agent."""

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

    conversation_messages = convert_history_to_messages(history)

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
            return str(response.content or last_response_content or "Sorry, I could not generate a response.")

        tool_names = [tool_call["name"] for tool_call in response.tool_calls]
        print(f"Chaining Tools -> {' | '.join(tool_names)}", flush=True)

        for call in response.tool_calls:
            tool_name = call["name"]
            args = call.get("args", {})

            print(f"Calling tool: {tool_name}", flush=True)
            print(f"Args: {args}", flush=True)

            tool_output = _execute_tool(
                tool_name=tool_name,
                args=args,
                tools=tools,
                question=question,
                conversation_messages=conversation_messages,
            )

            messages.append(
                ToolMessage(
                    name=tool_name,
                    content=str(tool_output),
                    tool_call_id=call["id"],
                )
            )

    return last_response_content or "I could not complete the answer because maximum tool iterations were reached."


def generator_agent_stream(question: str, history: list | None = None, user_profile: dict | None = None):
    """Streaming agent that yields UI events as dictionaries."""

    if not question:
        yield {
            "type": "token",
            "content": "Please ask me something about Veda's birthday.",
        }
        return

    generator_llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    tools = tool_manager.get_tools()
    tool_definition = tool_schema_manager(tools)

    generator_llm_with_tools = generator_llm.bind_tools(tool_definition)

    conversation_messages = convert_history_to_messages(history)

    messages = [SystemMessage(content=RAG_PROMPT)]

    if user_profile and user_profile.get("name"):
        messages.append(
            SystemMessage(
                content=f"The current user's name is {user_profile['name']}."
            )
        )

    messages.extend(conversation_messages)
    messages.append(HumanMessage(content=question))

    for _ in range(4):
        response = generator_llm_with_tools.invoke(messages)

        # If model wants tools, append full response with tool_calls
        if response.tool_calls:
            messages.append(response)

            tool_names = [tool_call["name"] for tool_call in response.tool_calls]
            print(f"Chaining Tools -> {' | '.join(tool_names)}", flush=True)

            for call in response.tool_calls:
                tool_name = call["name"]
                args = call.get("args", {})

                print(f"Calling tool: {tool_name}", flush=True)
                print(f"Args: {args}", flush=True)

                tool_output = _execute_tool(
                    tool_name=tool_name,
                    args=args,
                    tools=tools,
                    question=question,
                    conversation_messages=conversation_messages,
                )

                if tool_name == "condense_question":
                    yield {
                        "type": "thinking_update",
                        "content": f"Thinking... {tool_output}...",
                    }

                messages.append(
                    ToolMessage(
                        name=tool_name,
                        content=str(tool_output),
                        tool_call_id=call["id"],
                    )
                )

            continue

        # No tool calls: now stream final answer.
        # Important: do NOT append response before streaming,
        # otherwise you may stream based on an already-empty/final response.
        yield {"type": "answer_start", "content": ""}

        final_llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0,
            api_key=OPENAI_API_KEY,
            streaming=True,
        )

        for chunk in final_llm.stream(messages):
            token = chunk.content

            if token:
                yield {
                    "type": "token",
                    "content": token,
                }

        return

    yield {
        "type": "token",
        "content": "I could not complete the answer because maximum tool iterations were reached.",
    }
    """Streaming agent that yields UI events as dictionaries."""

    if not question:
        yield {
            "type": "token",
            "content": "Please ask me something about Veda's birthday.",
        }
        return

    generator_llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    tools = tool_manager.get_tools()
    tool_definition = tool_schema_manager(tools)

    generator_llm_with_tools = generator_llm.bind_tools(tool_definition)

    conversation_messages = convert_history_to_messages(history)

    messages = [SystemMessage(content=RAG_PROMPT)]
    messages.extend(conversation_messages)
    messages.append(HumanMessage(content=question))

    for _ in range(4):
        response = generator_llm_with_tools.invoke(messages)
        messages.append(response)

        if response.tool_calls:
            tool_names = [tool_call["name"] for tool_call in response.tool_calls]
            print(f"Chaining Tools -> {' | '.join(tool_names)}", flush=True)

            for call in response.tool_calls:
                tool_name = call["name"]
                args = call.get("args", {})

                print(f"Calling tool: {tool_name}", flush=True)
                print(f"Args: {args}", flush=True)

                tool_output = _execute_tool(
                    tool_name=tool_name,
                    args=args,
                    tools=tools,
                    question=question,
                    conversation_messages=conversation_messages,
                )

                if tool_name == "condense_question":
                    yield {
                        "type": "thinking_update",
                        "content": f"Thinking... {tool_output}...",
                    }

                messages.append(
                    ToolMessage(
                        name=tool_name,
                        content=str(tool_output),
                        tool_call_id=call["id"],
                    )
                )

            continue

        yield {"type": "answer_start", "content": ""}

        final_llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0,
            api_key=OPENAI_API_KEY,
            streaming=True,
        )

        for chunk in final_llm.stream(messages):
            token = chunk.content

            if token:
                yield {
                    "type": "token",
                    "content": token,
                }

        return

    yield {
        "type": "token",
        "content": "I could not complete the answer because maximum tool iterations were reached.",
    }

def extract_user_profile_from_query(user_message: str) -> dict:
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
Extract user profile information from the message.

Return JSON only.

Schema:
{
  "name": string | null
}

Rules:
- Extract the user's name only if the user explicitly tells their own name.
- Do not extract names of other people.
- Do not guess.
- Normalize name in title case.

Examples:
"Hi, my name is Rahul" -> {"name": "Rahul"}
"I am Rahul" -> {"name": "Rahul"}
"This is Rahul" -> {"name": "Rahul"}
"Myself Rahul" -> {"name": "Rahul"}
"what is my name?" -> {"name": null}
"Who is Veda's father?" -> {"name": null}
"""
        ),
        ("human", "{user_message}")
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({"user_message": user_message})
        return result or {"name": None}
    except Exception:
        return {"name": None}
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
Extract user profile information from the message.

Return JSON only.

Schema:
{
  "name": string | null
}

Rules:
- Extract the user's name only if the user explicitly tells their name.
- Do not extract names of other people.
- Do not guess.
- Normalize the name in title case.

Examples:
"Hi, my name is Rahul" -> {"name": "Rahul"}
"I am Rahul" -> {"name": "Rahul"}
"This is Rahul" -> {"name": "Rahul"}
"Myself Rahul" -> {"name": "Rahul"}
"what is my name?" -> {"name": null}
"Who is Veda's father?" -> {"name": null}
"""
        ),
        ("human", "{user_message}")
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({"user_message": user_message})
        return result or {"name": None}
    except Exception:
        return {"name": None}
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
Extract user profile information from the message.

Return JSON only.

Schema:
{
  "name": string | null
}

Rules:
- Extract the user's name only if the user explicitly tells their name.
- Examples:
  "Hi, my name is Rahul" -> {"name": "Rahul"}
  "I am Rahul" -> {"name": "Rahul"}
  "This is Rahul" -> {"name": "Rahul"}
  "what is my name?" -> {"name": null}
  "Who is Veda's father?" -> {"name": null}
- Do not guess.
"""
        ),
        ("human", "{user_message}")
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({"user_message": user_message})
        return result or {"name": None}
    except Exception:
        return {"name": None}