import shutil
from rag_agent.config import CHROMA_PATH

shutil.rmtree(CHROMA_PATH, ignore_errors=True)

print("Chroma DB deleted")

"""uv run python -m scripts.delete"""