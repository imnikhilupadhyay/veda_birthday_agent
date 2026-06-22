import json
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from rag_agent.config import CHROMA_PATH, EMBEDDING_MODEL, OPENAI_API_KEY


embedding_model = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    api_key=OPENAI_API_KEY,
)

vectorstore = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embedding_model,
)

data = vectorstore.get()

recovered = []

for doc in data["documents"]:
    question = ""
    answer = ""

    for line in doc.splitlines():
        if line.startswith("Q:"):
            question = line.replace("Q:", "", 1).strip()
        elif line.startswith("A:"):
            answer = line.replace("A:", "", 1).strip()

    recovered.append({
        "question": question,
        "answer": answer
    })

Path("data/docs").mkdir(parents=True, exist_ok=True)

with open("data/docs/veda_qa_recovered.json", "w", encoding="utf-8") as f:
    json.dump(recovered, f, indent=2, ensure_ascii=False)

print(f"Recovered {len(recovered)} Q&A records")
print("Saved to data/docs/veda_qa_recovered.json")