"""Deterministic RAG fallback when the LLM quota is exhausted."""

from __future__ import annotations

import json
import re
from typing import Any

from services.citations import format_citations
from tools.nowcast_dfm import run_nowcast_dfm
from tools.retrieve_docs import retrieve_docs


_NOWCAST_RE = re.compile(
    r"nowcast|predicci[oó]n|proyecci[oó]n|frecuencia\s+at|accidentes?\s+de\s+trabajo",
    re.I,
)


def compose_fallback_answer(question: str) -> dict[str, Any]:
    """Retrieve (and optionally nowcast) without calling the chat LLM."""
    tool_calls: list[str] = []
    nowcast = None
    citations: list[dict[str, Any]] = []
    parts: list[str] = []

    if _NOWCAST_RE.search(question or ""):
        tool_calls.append("run_nowcast_dfm")
        nowcast = json.loads(run_nowcast_dfm("2025-T1"))
        if nowcast.get("ok"):
            parts.append(
                f"Según el modelo operativo DFM (§2.3), el nowcast para "
                f"**{nowcast['periodo']}** es **{nowcast['y_hat']}** "
                f"(IC80% [{nowcast['ic80_lo']}, {nowcast['ic80_hi']}]) "
                f"{nowcast['unidad']}."
            )
            parts.append(nowcast.get("notas", ""))

    tool_calls.append("retrieve_docs")
    raw = json.loads(retrieve_docs(question, top_k=5))
    hits = raw.get("hits") or []
    citations = format_citations(hits)

    if hits:
        parts.append(
            "Fragmentos recuperados del corpus (respuesta extractiva; "
            "el LLM generativo no estuvo disponible en este turno):\n"
        )
        for i, h in enumerate(hits[:4], start=1):
            snippet = (h.get("text") or "").replace("\n", " ")[:420]
            parts.append(
                f"**[{i}]** `{h.get('filename')}` p.{h.get('page')}: {snippet}…"
            )
    else:
        parts.append(
            "No encontré soporte en el corpus para esta pregunta. "
            "No invento hechos adicionales."
        )

    return {
        "answer": "\n\n".join(p for p in parts if p).strip(),
        "citations": citations,
        "tool_calls": tool_calls,
        "nowcast": nowcast if nowcast and nowcast.get("ok") else None,
        "session_id": "fallback",
        "n_events": 0,
        "fallback": True,
    }
