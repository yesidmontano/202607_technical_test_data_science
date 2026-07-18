"""PDF ingestion: extract → chunk → embed → Chroma upsert."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from config.settings import CHUNK_CHARS, CHUNK_OVERLAP, UPLOADS_PATH
from services import chroma_store
from services.embeddings import embed_texts


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            pages.append((i, text))
    return pages


def chunk_pages(
    pages: list[tuple[int, str]],
    *,
    chunk_chars: int = CHUNK_CHARS,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for page_num, text in pages:
        if len(text) <= chunk_chars:
            chunks.append({"page": page_num, "text": text})
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_chars, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append({"page": page_num, "text": piece})
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks


def ingest_pdf_bytes(
    data: bytes,
    filename: str,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    doc_id = _content_hash(data)
    safe_name = Path(filename).name
    dest = UPLOADS_PATH / f"{doc_id}_{safe_name}"
    dest.write_bytes(data)

    pages = extract_pages(dest)
    if not pages:
        return {
            "ok": False,
            "error": "No se pudo extraer texto del PDF (posible escaneo sin OCR).",
            "doc_id": doc_id,
            "filename": safe_name,
        }

    pieces = chunk_pages(pages)
    chroma_store.delete_by_doc_id(doc_id)

    texts = [p["text"] for p in pieces]
    embeddings: list[list[float]] = []
    # Embed in smaller waves so partial progress survives rate limits
    wave = 8
    for i in range(0, len(texts), wave):
        embeddings.extend(embed_texts(texts[i : i + wave], task="retrieval_document"))
    if len(embeddings) != len(texts):
        raise RuntimeError(
            f"Embedding count mismatch: got {len(embeddings)} for {len(texts)} chunks"
        )
    now = datetime.now(timezone.utc).isoformat()
    rel_path = str(dest.relative_to(UPLOADS_PATH.parent.parent))  # apps/Asistente_RAG/...

    # Prefer path relative to app root for UI downloads
    source_path = str(dest)
    ids = [f"{doc_id}_{i}" for i in range(len(pieces))]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": safe_name,
            "source_path": source_path,
            "page": int(p["page"]),
            "chunk_id": i,
            "title": title or safe_name,
            "ingested_at": now,
        }
        for i, p in enumerate(pieces)
    ]
    chroma_store.upsert_chunks(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return {
        "ok": True,
        "doc_id": doc_id,
        "filename": safe_name,
        "n_pages": len(pages),
        "n_chunks": len(pieces),
        "source_path": source_path,
        "rel_hint": rel_path,
    }


def ingest_pdf_path(pdf_path: Path, *, title: str | None = None) -> dict[str, Any]:
    data = Path(pdf_path).read_bytes()
    return ingest_pdf_bytes(data, Path(pdf_path).name, title=title)
