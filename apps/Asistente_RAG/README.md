# Asistente RAG documental — Sector construcción

Aplicación en `apps/Asistente_RAG` según arquitectura §2.4.1.

## Stack

- **Frontend:** Streamlit
- **Agente:** Google ADK (`Agent` + tools)
- **Vector store:** ChromaDB PersistentClient
- **Embeddings:** Gemini Embedding 2 (`gemini-embedding-2`)
- **Nowcast:** DFM §2.3 desde staging S02

## Setup

```bash
# Desde la raíz del repo
cp apps/Asistente_RAG/.env.example apps/Asistente_RAG/.env
# Editar .env con GOOGLE_API_KEY de Google AI Studio

.venv/bin/pip install -r requirements.txt

# Indexar corpus de prueba (resources §2.4)
.venv/bin/python apps/Asistente_RAG/scripts/seed_corpus.py

# UI
.venv/bin/streamlit run apps/Asistente_RAG/app.py

# Smoke eval (traces)
.venv/bin/python apps/Asistente_RAG/eval/run_eval.py
```

## Páginas

1. **Chat** — preguntas con citas y descarga de PDF fuente
2. **Carga de documentos** — upload + ingestión automática
3. **Nowcast DFM** — punto e IC80% del modelo operativo

## Evaluación RAG Triad

Config: `eval/eval_config_rag_triad.json`  
Eval set: `eval/eval_sets/rag_triad_smoke.json`
