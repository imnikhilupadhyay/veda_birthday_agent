import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

CHROMA_PATH = "chroma_db"
DOC_PATH = "data/docs"

COOKIE_NAME = "veda_birthday_session_id"
MAX_HISTORY_MESSAGES = 4