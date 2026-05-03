"""All env-driven and tunable constants live here."""

import os

# --- LLM ---
NVIDIA_API_KEY: str = os.environ["NVIDIA_API_KEY"]
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
MODEL: str = "openai/gpt-oss-120b"
EMBED_MODEL: str = "nvidia/nv-embedqa-e5-v5"
EMBED_DIM: int = 1024

# --- External services ---
SEARXNG_URL: str = os.environ.get("SEARXNG_URL", "http://searxng:8080")
BROWSER_URL: str = os.environ.get("BROWSER_URL", "http://browser:8001")
DATABASE_URL: str = os.environ["DATABASE_URL"]

# --- Pipeline tuning ---
NUM_SOURCES: int = 6
MAX_CHARS_PER_SOURCE: int = 2500
FETCH_TIMEOUT: float = 10.0
HISTORY_TURNS: int = 3                 # prior turns piped into the LLM prompt for follow-ups
DEEP_MAX_STEPS: int = 6                # safety cap on agentic loop iterations

# --- RAG / PDFs ---
CHUNK_TARGET_CHARS: int = 1500
CHUNK_OVERLAP_CHARS: int = 100
RAG_TOP_K: int = 6
MAX_PDF_BYTES: int = 20 * 1024 * 1024  # 20 MB

# --- Auth ---
ANON_USER_ID: str = "00000000-0000-0000-0000-000000000000"

# --- Search focus → SearXNG params ---
FOCUS_PARAMS: dict[str, dict] = {
    "web":      {"categories": "general"},
    "academic": {"categories": "science"},
    "news":     {"categories": "news"},
    "reddit":   {"engines": "reddit"},
}

# --- CORS allowed origins ---
CORS_ORIGINS: list[str] = ["http://localhost:3001", "http://localhost:3000"]
