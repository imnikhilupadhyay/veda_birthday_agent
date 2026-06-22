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

QUERY_EXPANSIONS = {
    "venue": "Where is the birthday celebration taking place?",
    "location": "Where is the birthday celebration taking place?",
    "place": "Where is the birthday celebration taking place?",
    "where": "Where is the birthday celebration taking place?",
    "time": "What time does the birthday party start?",
    "timing": "What time does the birthday party start?",
    "date": "When is Veda's birthday?",
    "address": "What is the address of the birthday celebration?",
    "theme": "What is the theme of the birthday party?",
    "cake": "What kind of cake will be served at the birthday party?",
}

INTENT_TO_QUESTION = {
    "location": "Where is the birthday celebration taking place?",
    "time": "What time does the birthday party start?",
    "date": "When is Veda's birthday?",
    "address": "What is the address of the birthday celebration?",
    "theme": "What is the theme of the birthday party?",
    "cake": "What kind of cake will be served at the birthday party?",
}

def classify_query_intent(user_message: str) -> dict:
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You classify a user's birthday-agent query.

Return ONLY valid JSON.

JSON format:
{{
  "is_gibberish": false,
  "intent": "general"
}}

Allowed intents:
- location
- time
- date
- address
- theme
- cake
- general

Rules:
- location means venue/place/where the party is happening.
- time means start time/timing.
- date means birthday date or celebration date.
- address means full address.
- theme means party theme.
- cake means cake-related question.
- general means a normal understandable query that does not fit above.
- is_gibberish should be true only for random/meaningless text.

Examples:
"venue" -> {{"is_gibberish": false, "intent": "location"}}
"where is the party at" -> {{"is_gibberish": false, "intent": "location"}}
"where are we meeting" -> {{"is_gibberish": false, "intent": "location"}}
"where should i come" -> {{"is_gibberish": false, "intent": "location"}}
"party location" -> {{"is_gibberish": false, "intent": "location"}}
"time" -> {{"is_gibberish": false, "intent": "time"}}
"when should we come" -> {{"is_gibberish": false, "intent": "time"}}
"cake" -> {{"is_gibberish": false, "intent": "cake"}}
"abcd" -> {{"is_gibberish": true, "intent": "general"}}
"1234" -> {{"is_gibberish": true, "intent": "general"}}
"""
        ),
        ("human", "Message: {user_message}\nJSON:")
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({"user_message": user_message})
        return {
            "is_gibberish": bool(result.get("is_gibberish", False)),
            "intent": result.get("intent", "general"),
        }
    except Exception as e:
        print("INTENT CLASSIFICATION ERROR:", e, flush=True)
        return {"is_gibberish": False, "intent": "general"}

def normalize_user_query(question: str) -> str:
    result = classify_query_intent(question)

    if result.get("is_gibberish"):
        return question

    intent = result.get("intent", "general")

    if intent in INTENT_TO_QUESTION:
        expanded = INTENT_TO_QUESTION[intent]
        print(f"Intent normalized: '{question}' -> '{expanded}'", flush=True)
        return expanded

    return question
def is_gibberish_query(user_message: str) -> bool:
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You classify whether a user message is gibberish or not.

Return ONLY valid JSON.

JSON format:
{{
  "is_gibberish": true
}}

Rules:
- Gibberish means random characters, meaningless text, accidental typing, only numbers, or text with no understandable intent.
- Birthday-related short queries are NOT gibberish.
- Examples of NOT gibberish:
  - "venue"
  - "time"
  - "date"
  - "cake"
  - "where"
  - "when"
  - "what is her birthday?"
  - "my name is Rahul"
- Examples of gibberish:
  - "abcd"
  - "1234"
  - "asdfgh"
  - "qwerty"
  - "zzzz"
  - "ajskdjas"
"""
        ),
        ("human", "Message: {user_message}\nJSON:")
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({"user_message": user_message})
        return bool(result.get("is_gibberish", False))
    except Exception as e:
        print("GIBBERISH CLASSIFICATION ERROR:", e, flush=True)
        return False

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
    
    expanded_question = normalize_user_query(question)

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
    messages.append(HumanMessage(content=expanded_question))

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


def generator_agent_stream(
    question: str,
    history: list | None = None,
    user_profile: dict | None = None,
):
    """Streaming agent that yields UI events as dictionaries."""

    if not question:
        yield {
            "type": "token",
            "content": "Please ask me something about Veda's birthday.",
        }
        return

    expanded_question = normalize_user_query(question)

    if expanded_question != question:
        yield {
            "type": "thinking_update",
            "content": f"Thinking... {expanded_question}...",
        }

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
    messages.append(HumanMessage(content=expanded_question))

    for _ in range(4):
        response = generator_llm_with_tools.invoke(messages)

        if response.tool_calls:
            messages.append(response)

            tool_names = [tool_call["name"] for tool_call in response.tool_calls]
            print(f"Chaining Tools -> {' | '.join(tool_names)}", flush=True)

            for call in response.tool_calls:
                tool_name = call["name"]
                args = call.get("args", {})

                print(f"Calling tool: {tool_name}", flush=True)
                print(f"Args: {args}", flush=True)

                # Important:
                # If model passes original/weak input, override it with expanded_question
                if tool_name == "similar_questions":
                    args["input"] = expanded_question

                if tool_name == "condense_question":
                    args["question"] = expanded_question

                tool_output = _execute_tool(
                    tool_name=tool_name,
                    args=args,
                    tools=tools,
                    question=expanded_question,
                    conversation_messages=conversation_messages,
                )

                if tool_name == "condense_question":
                    yield {
                        "type": "thinking_update",
                        "content": f"Thinking... {tool_output}...",
                    }
                elif tool_name == "similar_questions":
                    yield {
                        "type": "thinking_update",
                        "content": "Searching Veda's birthday memories... 🎂"
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
You extract the current user's name from a message.

Return ONLY valid JSON.

JSON format:
{{
  "name": null
}}

Rules:
- Extract the name only when the speaker explicitly introduces themselves.
- If the speaker says "my name is X", extract X.
- If the speaker says "I am X", extract X only when it is clearly an introduction.
- If the speaker says "this is X", extract X only when it is clearly an introduction.
- A message may contain both introduction and another question.
- Do not extract names of other people.
- Do not guess.
- If no current-user name is provided, return {{"name": null}}.

Examples:
Message: Hi, my name is Rahul. When is her birthday?
JSON: {{"name": "Rahul"}}

Message: Hello, I am Priya. Can you help me?
JSON: {{"name": "Priya"}}

Message: This is Amit.
JSON: {{"name": "Amit"}}

Message: what is my name?
JSON: {{"name": null}}

Message: Who is Veda's father?
JSON: {{"name": null}}
"""
        ),
        ("human", "Message: {user_message}\nJSON:")
    ])

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke({"user_message": user_message})
        name = result.get("name")

        if isinstance(name, str) and name.strip():
            return {"name": name.strip().title()}

        return {"name": None}

    except Exception as e:
        print("PROFILE EXTRACTION ERROR:", e, flush=True)
        return {"name": None}
    