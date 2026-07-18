### **S02: Modelación económica y sectorial del sector construcción**

### 2.4.2 Construcción del Asistente RAG

> **Resultado:** Aplicación operativa en `apps/Asistente_RAG` según arquitectura §2.4.1. Corpus de prueba (CEED + ELIC) indexado con **Gemini Embedding 2** en ChromaDB (85 chunks / 2 docs). Tools `retrieve_docs` y `run_nowcast_dfm` verificados. UI Streamlit con Chat / Carga / Nowcast. Eval RAG Triad configurada; smoke de traces en modo extractivo ante cuota LLM.

---

## 1. Cómo arrancar

```bash
# API key solo en apps/Asistente_RAG/.env (nunca en git)
.venv/bin/python apps/Asistente_RAG/scripts/seed_corpus.py   # si el índice está vacío
.venv/bin/streamlit run apps/Asistente_RAG/app.py
.venv/bin/python apps/Asistente_RAG/eval/run_eval.py         # smoke traces
```

---

## 2. Qué se construyó

| Componente | Ubicación | Estado |
|---|---|---|
| Settings + `.env` | `config/settings.py`, `.env` (gitignored) | ✅ |
| Embeddings Gemini Embedding 2 | `services/embeddings.py` | ✅ (dim 768, 1 request/texto, retry 429) |
| Chroma PersistentClient | `services/chroma_store.py` | ✅ colección `sector_construccion_rag` |
| Ingestión PDF | `services/ingestion.py` | ✅ extract → chunk → embed → upsert |
| Citas | `services/citations.py` | ✅ + download en UI |
| Tool retrieve | `tools/retrieve_docs.py` | ✅ |
| Tool nowcast DFM | `tools/nowcast_dfm.py` | ✅ lee staging S02 |
| Agente ADK | `agents/root_agent.py` + `runner_service.py` | ✅ + fallback extractivo |
| UI Streamlit | `app.py`, `ui/page_*.py` | ✅ 3 páginas |
| Eval RAG Triad | `eval/eval_config_rag_triad.json`, `eval_sets/`, `run_eval.py` | ✅ config + smoke |
| Seed corpus | `scripts/seed_corpus.py` | ✅ resources CEED/ELIC |

### Árbol desplegado

```text
apps/Asistente_RAG/
├── app.py
├── .env / .env.example
├── README.md
├── agents/   (prompts, root_agent, runner_service)
├── tools/    (retrieve_docs, nowcast_dfm)
├── services/ (embeddings, chroma_store, ingestion, citations, rag_fallback)
├── ui/       (page_upload, page_chat, page_nowcast)
├── eval/     (eval_config_rag_triad.json, eval_sets/, run_eval.py)
├── scripts/seed_corpus.py
└── data/{chroma,uploads}/   # gitignored
```

---

## 3. Pruebas realizadas

### 3.1 Ingestión (resources §2.4)

| Documento | Chunks | doc_id |
|---|---|---|
| `bol-CEED-Itrim2026.pdf` | 51 | `9092212fd3d5c236` |
| `bol-ELIC-may2026pr.pdf` | 34 | `eb944a9c15015986` |
| **Total** | **85** | 2 docs |

### 3.2 Tools

| Tool | Resultado |
|---|---|
| `retrieve_docs("CEED área causada…")` | 6 hits; top = CEED p.42 |
| `run_nowcast_dfm("2025-T1")` | ŷ=**1.1577** IC80% **[1.0615, 1.2852]** (DFM staging) |

### 3.3 Smoke traces (`eval/run_eval.py`)

| Caso | Tools | Citas | OK |
|---|---|---|---|
| `retrieve_ceed` | `retrieve_docs` | 5 | ✅ |
| `nowcast_dfm` | `run_nowcast_dfm` + `retrieve_docs` | 5 | ✅ |

Artefacto: `apps/Asistente_RAG/eval/last_smoke_results.json`.

### 3.4 Limitación de cuota LLM (Google AI Studio)

Durante las pruebas:

1. `gemini-2.5-flash` → **404** (“no longer available to new users”).
2. `gemini-2.0-flash` (y free-tier generate) → **429** con `limit: 0` en `generate_content_free_tier_*`.
3. **Embeddings** (`gemini-embedding-2`) sí funcionaron (indexación completa).

**Mitigación implementada:** si el `Runner` ADK falla por cuota/modelo, `runner_service` cae a `services/rag_fallback.py` (respuesta extractiva con retrieval + nowcast, sin inventar cifras). La UI avisa el modo extractivo. Cuando haya cuota de generación, el agente ADK sintetiza con citas de forma generativa.

**Default LLM:** `gemini-2.0-flash` (configurable vía `LLM_MODEL` en `.env`).

---

## 4. Evaluación RAG Triad (ADK)

Config en `eval/eval_config_rag_triad.json`:

| Pilar | Métrica ADK |
|---|---|
| Groundedness | `hallucinations_v1` |
| Answer Relevance | `rubric_based_final_response_quality_v1` |
| Context Relevance | `rubric_based_tool_use_quality_v1` + `tool_trajectory_avg_score` |

Eval set E2E esqueleto: `eval/eval_sets/rag_triad_smoke.json` (retrieve / nowcast / abstención).  
Judge model alineado a `gemini-2.0-flash`. Corrida completa `adk eval` pendiente de cuota generate.

---

## 5. Seguridad

- API key **solo** en `apps/Asistente_RAG/.env` (añadido a `.gitignore` junto con `data/chroma/` y `data/uploads/`).
- `.env.example` sin secretos.
- **Recomendación:** rotar la clave expuesta en el chat de construcción; no reutilizarla en repos públicos.

---

## 6. Checklist de aceptación §2.4.2

- [x] App en `apps/Asistente_RAG` con capas UI / agents / tools / services / eval
- [x] Chroma PersistentClient como vector store + persistencia
- [x] Embeddings `gemini-embedding-2` en ingestión y query
- [x] Chat con citas y descarga/link al PDF
- [x] Nowcast DFM desde staging S02 como tool
- [x] RAG Triad configurado (traces smoke + eval config E2E)
- [x] Corpus resources indexado (CEED + ELIC)
- [ ] Síntesis generativa ADK E2E con cuota LLM activa (bloqueado por free-tier generate=0)

---

## Next step

Reintentar chat generativo cuando el proyecto AI Studio tenga cuota `generate_content` (billing o nuevo proyecto). Opcional: ampliar corpus y correr `adk eval` formal con el config RAG Triad.
