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
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Google Gemini 設定
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")
GOOGLE_EMBED_MODEL = os.getenv("GOOGLE_EMBED_MODEL", "models/gemini-embedding-001")

# Ollama 設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://api.ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# 商業化認證與配額設定
DB_PATH = os.path.join(DATA_DIR, "users.db")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "commercial_rag_super_secret_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "20"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

# 管理員帳號名單 (.env 可用逗號分隔設定多個，支援 "username" 或 "username:password" 語法)
# 範例: ADMIN_USERS="admin:admin123,superadmin:MyPass888,manager"
ADMIN_USERS_CONFIG = {}
for entry in os.getenv("ADMIN_USERS", "admin").split(","):
    entry = entry.strip()
    if not entry:
        continue
    if ":" in entry:
        u_name, u_pass = entry.split(":", 1)
        ADMIN_USERS_CONFIG[u_name.strip().lower()] = u_pass.strip()
    else:
        ADMIN_USERS_CONFIG[entry.lower()] = DEFAULT_ADMIN_PASSWORD

ADMIN_USERS = list(ADMIN_USERS_CONFIG.keys())

