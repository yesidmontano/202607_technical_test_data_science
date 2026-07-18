"""ADK tool: semantic retrieval over Chroma corpus."""

from __future__ import annotations

import json
from typing import Any

from services.chroma_store import query_chunks
from services.embeddings import embed_query


def retrieve_docs(query: str, top_k: int = 6) -> str:
    """Retrieve relevant document fragments from the sectoral PDF corpus.

    Use this tool whenever the user asks about DANE bulletins, construction
    indicators (CEED, ELIC, IPOC, EC), or any fact that must be grounded in
    the uploaded documents. Returns JSON with fragments and citation metadata.

    Args:
        query: Natural-language search query in Spanish.
        top_k: Maximum number of fragments to return (default 6).

    Returns:
        JSON string with keys: n_hits, hits[{text, filename, page, source_path,
        doc_id, score, distance}].
    """
    q = (query or "").strip()
    if not q:
        return json.dumps({"n_hits": 0, "hits": [], "error": "empty query"}, ensure_ascii=False)

    embedding = embed_query(q)
    hits = query_chunks(embedding, top_k=top_k)
    payload: dict[str, Any] = {
        "n_hits": len(hits),
        "hits": [
            {
                "text": h.get("text", "")[:1200],
                "filename": h.get("filename"),
                "page": h.get("page"),
                "source_path": h.get("source_path"),
                "doc_id": h.get("doc_id"),
                "score": round(float(h.get("score", 0.0)), 4),
                "distance": round(float(h.get("distance", 0.0)), 4),
            }
            for h in hits
        ],
    }
    if not hits:
        payload["note"] = (
            "No relevant fragments found. Tell the user you lack corpus support "
            "and do not invent facts."
        )
    return json.dumps(payload, ensure_ascii=False)
