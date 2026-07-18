"""Streamlit page: PDF upload + automatic embedding."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from services import chroma_store
from services.ingestion import ingest_pdf_bytes, ingest_pdf_path
from config.settings import RESOURCES_DIR


def render() -> None:
    st.subheader("Carga de documentos PDF")
    st.caption(
        "Los PDFs se indexan automáticamente con **Gemini Embedding 2** "
        "(`gemini-embedding-2`) en ChromaDB persistente."
    )

    stats = chroma_store.collection_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Chunks indexados", stats["n_chunks"])
    c2.metric("Documentos", stats["n_docs"])
    c3.metric("Colección", stats["collection"])

    st.markdown("#### Subir PDF")
    uploaded = st.file_uploader("Selecciona uno o más PDF", type=["pdf"], accept_multiple_files=True)
    if uploaded and st.button("Ingestar documentos", type="primary"):
        for f in uploaded:
            with st.spinner(f"Indexando {f.name}…"):
                result = ingest_pdf_bytes(f.getvalue(), f.name)
            if result.get("ok"):
                st.success(
                    f"✅ `{result['filename']}` → {result['n_chunks']} chunks "
                    f"(doc_id=`{result['doc_id']}`)"
                )
            else:
                st.error(f"❌ {result.get('filename')}: {result.get('error')}")
        st.rerun()

    st.markdown("#### Corpus de prueba (resources §2.4)")
    if RESOURCES_DIR.is_dir():
        pdfs = sorted(RESOURCES_DIR.glob("*.pdf"))
        st.write(f"Encontrados: {len(pdfs)} PDF en `{RESOURCES_DIR.name}/`")
        if pdfs and st.button("Ingestar corpus de resources"):
            for pdf in pdfs:
                with st.spinner(f"Indexando {pdf.name}…"):
                    result = ingest_pdf_path(pdf)
                if result.get("ok"):
                    st.success(f"✅ {pdf.name}: {result['n_chunks']} chunks")
                else:
                    st.error(f"❌ {pdf.name}: {result.get('error')}")
            st.rerun()
    else:
        st.warning("No se encontró la carpeta de resources.")

    docs = chroma_store.list_documents()
    if docs:
        st.markdown("#### Documentos en el índice")
        st.dataframe(docs, use_container_width=True)
