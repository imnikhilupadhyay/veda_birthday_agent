"""Build and persist the vector database."""
"""uv run python -m scripts.ingest"""


from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import os
import json
from dotenv import load_dotenv

from rag_agent.config import CHROMA_PATH, DOC_PATH, OPENAI_API_KEY, EMBEDDING_MODEL, LLM_MODEL

load_dotenv()

def load_docs(path):
    """Load documents from the specified path."""
    docs = []
    for filename in os.listdir(path):
        if filename.endswith(".json"):
            with open(os.path.join(path, filename), "r", encoding="utf-8") as f:
                docs = json.load(f)
    return docs

docs = load_docs(DOC_PATH)

processed_docs = []

for qa in docs:
    qa["page_content"] = f"Q: {qa['question']}\nA: {qa['answer']}".strip()

    metadata = {
        "birthday": "2026-06-28",
        "data_of_birth": "2024-06-28",
        "name": "Veda Upadhyay",
    }
    qa["metadata"] = metadata

    processed_docs.append(Document(
        page_content=qa["page_content"],
        metadata=qa["metadata"]
    ))

print(f"Loaded {len(processed_docs)} documents")

embedding_model = OpenAIEmbeddings(
    model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY
)

vector_store = Chroma.from_documents(
    documents=processed_docs,
    embedding=embedding_model,
    persist_directory=CHROMA_PATH,
)

print(f"Documents loaded in the vector DB at {CHROMA_PATH}")