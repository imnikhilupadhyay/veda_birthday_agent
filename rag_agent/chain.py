"""RAG chain construction."""

from typing import List

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import Tool, StructuredTool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from rag_agent.config import (
    CHROMA_PATH,
    EMBEDDING_MODEL,
    LLM_MODEL,
    OPENAI_API_KEY,
)


class RAGChain:

    def __init__(self):
        print("Initializing RAGChain...", flush=True)

        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0,
            api_key=OPENAI_API_KEY,
        )

        self.embedding_model = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY,
        )

        print(f"Loading Chroma from: {CHROMA_PATH}", flush=True)

        self.vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=self.embedding_model,
        )

        print("RAGChain initialized.", flush=True)

    def similar_questions(self, question: str) -> str:
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )

        results = retriever.invoke(question)

        if not results:
            return "No similar questions found in the knowledge base."

        return self._format_docs(results)

    def _format_docs(self, docs) -> str:
        output = "Retrieved birthday information:\n\n"

        for i, doc in enumerate(docs):
            output += f"--- Document {i + 1} ---\n"
            output += f"{doc.page_content}\n\n"

        return output.strip()

    def condense_question(
        self,
        question: str,
        conversation_history: list | None = None,
    ) -> str:
        if conversation_history is None:
            conversation_history = []

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
Given the conversation history, rewrite the user's question into a standalone question only if needed.

Rules:
- If the question is already clear, return it unchanged.
- Resolve vague references like her, his, she, he, it, this, that, there, they, them using chat history.
- If no chat history is available and the question refers to "her" or "she", assume the user is referring to Veda.
- Return only the rewritten question.
""",
                ),
                MessagesPlaceholder(variable_name="conversation_history"),
                ("human", "{question}"),
            ]
        )

        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke(
            {
                "conversation_history": conversation_history,
                "question": question,
            }
        )

        print(f"Condensed question: {response}", flush=True)

        return response.strip()

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="similar_questions",
                func=self.similar_questions,
                description=(
                    "Use this tool to retrieve relevant birthday information "
                    "from the knowledge base. Input should be a standalone question."
                ),
            ),
            StructuredTool.from_function(
                name="condense_question",
                func=self.condense_question,
                description=(
                    "Use this tool when the user's question has vague references "
                    "and needs chat history to become standalone."
                ),
            ),
        ]