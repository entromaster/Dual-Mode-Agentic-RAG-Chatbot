"""
Application configuration — loads settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# ── Model Configuration ──────────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-2.5-flash"
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# ── Dates ─────────────────────────────────────────────────────────────────────
CURRENT_DATE: str = "2026-06-15"

# ── Paths ─────────────────────────────────────────────────────────────────────
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent          # …/backend
DATASET_DIR: Path = Path(os.getenv("DATASET_PATH", os.getenv("DATASET_DIR", str(BACKEND_DIR.parent / "Dataset"))))
CHROMA_PERSIST_DIR: str = str(BACKEND_DIR / "chroma_data")
SQLITE_DB_PATH: str = str(BACKEND_DIR / "orders.db")
STATIC_DIR: str = os.getenv("STATIC_DIR", str(BACKEND_DIR / "static"))

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_COLLECTION_NAME: str = "northwind_docs"
