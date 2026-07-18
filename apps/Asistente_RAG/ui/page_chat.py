"""Streamlit page: RAG chat with citations."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from agents.runner_service import ask


def _render_citations(citations: list[dict], *, key_prefix: str) -> None:
    if not citations:
        st.info("Sin citas recuperadas en este turno.")
        return
    st.markdown("##### Fuentes")
    for i, c in enumerate(citations):
        with st.expander(
            f"[{c['ref']}] {c['filename']} · p. {c['page']} · score={c['score']}"
        ):
            st.write(c.get("snippet") or "")
            path = c.get("source_path") or ""
            if path and Path(path).is_file():
                st.download_button(
                    label=f"Descargar {c['filename']}",
                    data=Path(path).read_bytes(),
                    file_name=str(c["filename"]),
                    mime="application/pdf",
                    key=f"dl_{key_prefix}_{i}_{c.get('doc_id')}_{c.get('page')}",
                )
            else:
                st.caption(f"Ruta: `{path}`")


def render() -> None:
    st.subheader("Chat documental (RAG)")
    st.caption(
        "El agente ADK recupera fragmentos con `retrieve_docs` y, si aplica, "
        "ejecuta `run_nowcast_dfm`. Las respuestas deben citar fuentes."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "rag_session_id" not in st.session_state:
        st.session_state.rag_session_id = "streamlit-session"
    if "msg_seq" not in st.session_state:
        st.session_state.msg_seq = 0

    for msg_idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                _render_citations(
                    msg["citations"],
                    key_prefix=f"hist_{msg_idx}_{msg.get('seq', msg_idx)}",
                )
            if msg.get("nowcast"):
                nc = msg["nowcast"]
                st.success(
                    f"Nowcast DFM {nc.get('periodo')}: **{nc.get('y_hat')}** "
                    f"[{nc.get('ic80_lo')}, {nc.get('ic80_hi')}] "
                    f"({nc.get('unidad')})"
                )

    prompt = st.chat_input("Pregunta sobre el corpus o el nowcast AT…")
    if not prompt:
        return

    st.session_state.msg_seq += 1
    user_seq = st.session_state.msg_seq
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "seq": user_seq}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente ADK…"):
            try:
                result = ask(prompt, session_id=st.session_state.rag_session_id)
            except Exception as exc:
                st.error(f"Error al consultar el agente: {exc}")
                return
        if result.get("fallback"):
            st.warning(
                "Respuesta en modo extractivo (LLM con cuota/modelo no disponible). "
                "Retrieval y nowcast sí se ejecutaron."
            )
        answer = result.get("answer") or "_Sin respuesta del modelo._"
        st.markdown(answer)
        citations = result.get("citations") or []
        st.session_state.msg_seq += 1
        asst_seq = st.session_state.msg_seq
        # Don't render citations here — they will show on next rerun from history
        # to avoid duplicate keys with the history loop. Store and rerun.
        if result.get("nowcast"):
            nc = result["nowcast"]
            st.success(
                f"Nowcast DFM {nc.get('periodo')}: **{nc.get('y_hat')}** "
                f"[{nc.get('ic80_lo')}, {nc.get('ic80_hi')}]"
            )
        if result.get("tool_calls"):
            st.caption("Tools: " + ", ".join(result["tool_calls"]))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "citations": citations,
            "nowcast": result.get("nowcast"),
            "seq": asst_seq,
            "fallback": result.get("fallback", False),
        }
    )
    st.rerun()
