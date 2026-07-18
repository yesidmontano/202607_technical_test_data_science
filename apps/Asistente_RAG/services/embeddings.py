"""Gemini Embedding 2 client."""

from __future__ import annotations

import time
from typing import Sequence

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from config.settings import EMBEDDING_DIM, EMBEDDING_MODEL, require_api_key

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=require_api_key())
    return _client


def _embed_once(client: genai.Client, text: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    vals = list(result.embeddings[0].values)
    if len(vals) > EMBEDDING_DIM:
        vals = vals[:EMBEDDING_DIM]
    return vals


def embed_texts(texts: Sequence[str], *, task: str = "retrieval_document") -> list[list[float]]:
    """Embed texts with Gemini Embedding 2 (one request per text).

    task is encoded as a short instruction prefix (Embeddings 2 style).
    Retries on 429 with exponential backoff.
    """
    if not texts:
        return []
    client = get_client()
    prefix = {
        "retrieval_document": "Task: retrieval document embedding. Text: ",
        "retrieval_query": "Task: retrieval query embedding. Text: ",
    }.get(task, "")

    out: list[list[float]] = []
    for t in texts:
        content = f"{prefix}{t}"
        delay = 2.0
        last_err: Exception | None = None
        for _attempt in range(8):
            try:
                out.append(_embed_once(client, content))
                last_err = None
                break
            except ClientError as exc:
                last_err = exc
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    time.sleep(delay)
                    delay = min(delay * 1.8, 90.0)
                    continue
                raise
        if last_err is not None:
            raise last_err
        time.sleep(0.25)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text], task="retrieval_query")[0]
