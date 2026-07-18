"""ADK Runner bridge for Streamlit (sync wrappers)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.root_agent import build_root_agent
from config.settings import APP_NAME, DEFAULT_USER_ID, require_api_key
from services.citations import format_citations
from services.rag_fallback import compose_fallback_answer

_session_service: InMemorySessionService | None = None
_runner: Runner | None = None
_runner_model: str | None = None


def reset_runner() -> None:
    global _session_service, _runner, _runner_model
    _session_service = None
    _runner = None
    _runner_model = None


def _ensure_runner() -> Runner:
    global _session_service, _runner, _runner_model
    from config.settings import LLM_MODEL

    require_api_key()
    if _runner is None or _runner_model != LLM_MODEL:
        _session_service = InMemorySessionService()
        agent = build_root_agent()
        _runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            session_service=_session_service,
        )
        _runner_model = LLM_MODEL
    return _runner


async def _ensure_session(user_id: str, session_id: str) -> str:
    _ensure_runner()
    assert _session_service is not None
    existing = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        session = await _session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={},
        )
        return session.id
    return existing.id


def _extract_text(event: Any) -> str:
    parts: list[str] = []
    content = getattr(event, "content", None)
    if content is None:
        return ""
    for part in getattr(content, "parts", None) or []:
        text = getattr(part, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def _parse_retrieve_hits(tool_responses: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for raw in tool_responses:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict) and "hits" in data:
            hits.extend(data.get("hits") or [])
    return hits


async def ask_async(
    question: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    session_id: str = "default",
) -> dict[str, Any]:
    try:
        runner = _ensure_runner()
        sid = await _ensure_session(user_id, session_id)
        message = types.Content(role="user", parts=[types.Part(text=question)])

        final_text = ""
        tool_calls: list[str] = []
        tool_responses: list[str] = []
        events_summary: list[dict[str, Any]] = []

        async for event in runner.run_async(
            user_id=user_id,
            session_id=sid,
            new_message=message,
        ):
            author = getattr(event, "author", None) or getattr(event, "source", "")
            text = _extract_text(event)
            is_final = bool(getattr(event, "is_final_response", lambda: False)())
            content = getattr(event, "content", None)
            if content is not None:
                for part in getattr(content, "parts", None) or []:
                    fc = getattr(part, "function_call", None)
                    if fc is not None:
                        tool_calls.append(getattr(fc, "name", "tool"))
                    fr = getattr(part, "function_response", None)
                    if fr is not None:
                        resp = getattr(fr, "response", None)
                        if isinstance(resp, dict):
                            if "result" in resp:
                                tool_responses.append(str(resp["result"]))
                            else:
                                tool_responses.append(
                                    json.dumps(resp, ensure_ascii=False)
                                )
                        elif resp is not None:
                            tool_responses.append(str(resp))
            if text:
                events_summary.append(
                    {"author": author, "text": text[:500], "final": is_final}
                )
                if is_final or author == "model":
                    final_text = text

        if not final_text and events_summary:
            final_text = events_summary[-1]["text"]

        hits = _parse_retrieve_hits(tool_responses)
        citations = format_citations(hits)

        nowcast = None
        for raw in tool_responses:
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if isinstance(data, dict) and data.get("modelo") == "DFM" and "y_hat" in data:
                nowcast = data

        return {
            "answer": final_text.strip(),
            "citations": citations,
            "tool_calls": tool_calls,
            "nowcast": nowcast,
            "session_id": sid,
            "n_events": len(events_summary),
            "fallback": False,
        }
    except Exception as exc:
        msg = str(exc)
        if any(
            x in msg
            for x in ("429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND", "quota", "failed")
        ):
            out = compose_fallback_answer(question)
            out["fallback_reason"] = msg[:240]
            return out
        raise


def ask(
    question: str, *, user_id: str = DEFAULT_USER_ID, session_id: str = "default"
) -> dict[str, Any]:
    return asyncio.run(ask_async(question, user_id=user_id, session_id=session_id))
