import os
from dotenv import load_dotenv

# 載入 .env 設定
load_dotenv(override=True)

# 專案路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_PDF_PATH = os.path.join(DATA_DIR, "Produktinformationsblatt.pdf")
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, ".chroma_db")

# 提供者預設設定
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "google").lower()

# Google Gemini 設定
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")
GOOGLE_EMBED_MODEL = os.getenv("GOOGLE_EMBED_MODEL", "models/gemini-embedding-001")

# Ollama 設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
