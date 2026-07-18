"""ChromaDB persistent vector store."""

from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings

from config.settings import CHROMA_PATH, COLLECTION_NAME, MAX_DISTANCE, TOP_K

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(
    *,
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]],
) -> int:
    col = get_collection()
    col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    return len(ids)


def delete_by_doc_id(doc_id: str) -> None:
    col = get_collection()
    try:
        col.delete(where={"doc_id": doc_id})
    except Exception:
        pass


def query_chunks(
    query_embedding: list[float],
    *,
    top_k: int = TOP_K,
    max_distance: float = MAX_DISTANCE,
) -> list[dict[str, Any]]:
    col = get_collection()
    if col.count() == 0:
        return []
    res = col.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, max(col.count(), 1)),
        include=["documents", "metadatas", "distances"],
    )
    hits: list[dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i, chunk_id in enumerate(ids):
        dist = float(dists[i]) if dists is not None else 0.0
        if dist > max_distance:
            continue
        meta = dict(metas[i] or {})
        hits.append(
            {
                "id": chunk_id,
                "text": docs[i] or "",
                "distance": dist,
                "score": 1.0 / (1.0 + dist),
                **meta,
            }
        )
    return hits


def list_documents() -> list[dict[str, Any]]:
    col = get_collection()
    if col.count() == 0:
        return []
    data = col.get(include=["metadatas"])
    seen: dict[str, dict[str, Any]] = {}
    for meta in data.get("metadatas") or []:
        if not meta:
            continue
        doc_id = str(meta.get("doc_id", ""))
        if not doc_id or doc_id in seen:
            continue
        seen[doc_id] = {
            "doc_id": doc_id,
            "filename": meta.get("filename"),
            "source_path": meta.get("source_path"),
            "title": meta.get("title"),
            "ingested_at": meta.get("ingested_at"),
        }
    return list(seen.values())


def collection_stats() -> dict[str, Any]:
    col = get_collection()
    return {"collection": COLLECTION_NAME, "n_chunks": col.count(), "n_docs": len(list_documents())}
