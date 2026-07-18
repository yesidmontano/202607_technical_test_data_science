"""Application settings for Asistente RAG."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]

load_dotenv(APP_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")

ASISTENTE_RAG_ROOT = Path(os.getenv("ASISTENTE_RAG_ROOT", str(APP_DIR))).resolve()
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(ASISTENTE_RAG_ROOT / "data" / "chroma"))).resolve()
UPLOADS_PATH = ASISTENTE_RAG_ROOT / "data" / "uploads"
STAGING_S02 = REPO_ROOT / "data" / "staging" / "S02"
RESOURCES_DIR = (
    REPO_ROOT
    / "sections"
    / "S02-Modelacion_Economica_Sectorial"
    / "2_4_Asistente RAG"
    / "resources"
)

COLLECTION_NAME = "sector_construccion_rag"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-flash-latest")
TOP_K = int(os.getenv("TOP_K", "6"))
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "1.15"))  # cosine distance filter
CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", "2800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
APP_NAME = "asistente_rag"
DEFAULT_USER_ID = "analista_sectorial"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""

UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
CHROMA_PATH.mkdir(parents=True, exist_ok=True)


def require_api_key() -> str:
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "Missing GOOGLE_API_KEY / GEMINI_API_KEY. Copy .env.example to .env."
        )
    return GOOGLE_API_KEY
