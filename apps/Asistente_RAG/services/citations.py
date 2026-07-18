"""Citation helpers for chat UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def format_citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by (doc_id, page) preserving retrieval order."""
    seen: set[tuple[str, int]] = set()
    cites: list[dict[str, Any]] = []
    for i, h in enumerate(hits, start=1):
        key = (str(h.get("doc_id", "")), int(h.get("page", 0) or 0))
        if key in seen:
            continue
        seen.add(key)
        path = h.get("source_path") or ""
        cites.append(
            {
                "ref": i,
                "doc_id": h.get("doc_id"),
                "filename": h.get("filename"),
                "page": h.get("page"),
                "score": round(float(h.get("score", 0.0)), 3),
                "source_path": path,
                "exists": Path(path).is_file() if path else False,
                "snippet": (h.get("text") or "")[:280],
            }
        )
    return cites


def citations_markdown(cites: list[dict[str, Any]]) -> str:
    if not cites:
        return "_Sin fuentes recuperadas._"
    lines = ["**Fuentes**"]
    for c in cites:
        lines.append(
            f"[{c['ref']}] `{c['filename']}` · p. {c['page']} · score={c['score']}"
        )
    return "\n".join(lines)
