"""Asistente RAG documental — Streamlit entrypoint.

Run from repo root:
    .venv/bin/streamlit run apps/Asistente_RAG/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st

from config.settings import require_api_key
from ui import page_chat, page_nowcast, page_upload

st.set_page_config(
    page_title="Asistente RAG · Construcción",
    page_icon="📄",
    layout="wide",
)

st.title("Asistente RAG documental — Sector construcción")
st.caption(
    "Google ADK · ChromaDB · Gemini Embedding 2 · Nowcast DFM (§2.3)"
)

try:
    require_api_key()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

page = st.sidebar.radio(
    "Navegación",
    ["Chat", "Carga de documentos", "Nowcast DFM"],
    index=0,
)

if page == "Carga de documentos":
    page_upload.render()
elif page == "Nowcast DFM":
    page_nowcast.render()
else:
    page_chat.render()
