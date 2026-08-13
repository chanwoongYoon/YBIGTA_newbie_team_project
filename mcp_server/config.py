import os

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


# --- DB (read-only credentials, separate from the collector's write credentials) ---
MCP_DB_HOST = os.getenv("MCP_DB_HOST", "127.0.0.1")
MCP_DB_PORT = _env_int("MCP_DB_PORT", 3306)
MCP_DB_USER = os.getenv("MCP_DB_USER", "mcp_user")
MCP_DB_PASSWORD = os.getenv("MCP_DB_PASSWORD", "")
MCP_DB_NAME = os.getenv("MCP_DB_NAME", "review_db")

DATABASE_URL = os.getenv(
    "MCP_DATABASE_URL",
    f"mysql+pymysql://{MCP_DB_USER}:{MCP_DB_PASSWORD}@{MCP_DB_HOST}:{MCP_DB_PORT}/{MCP_DB_NAME}?charset=utf8mb4",
)

# --- Auth ---
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

# --- Server ---
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = _env_int("MCP_SERVER_PORT", 8000)

# --- Query safety limits (see repositories/review_repository.py) ---
MAX_ROW_LIMIT = _env_int("MCP_MAX_ROW_LIMIT", 100)
DEFAULT_ROW_LIMIT = _env_int("MCP_DEFAULT_ROW_LIMIT", 20)
QUERY_TIMEOUT_MS = _env_int("MCP_QUERY_TIMEOUT_MS", 5000)

ALLOWED_SOURCES = ("goodreads", "kyobo", "yes24")
