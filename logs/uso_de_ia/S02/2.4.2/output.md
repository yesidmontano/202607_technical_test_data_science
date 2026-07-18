# Registro de Uso de IA — 2.4.2

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba poner en producción `apps/Asistente_RAG` según la arquitectura §2.4.1: scaffold completo, ingestión PDF con Gemini Embedding 2, agente ADK con tools de retrieval y nowcast DFM, UI Streamlit, evaluación RAG Triad, seed del corpus en resources y pruebas con la API de Google AI Studio.

## Qué se tomó
- Estructura de carpetas de §2.4.1 (config/agents/tools/services/ui/eval/data).
- Embeddings `gemini-embedding-2` (dim 768), Chroma PersistentClient, colección `sector_construccion_rag`.
- Corpus de prueba: `bol-CEED-Itrim2026.pdf`, `bol-ELIC-may2026pr.pdf` → 85 chunks.
- Nowcast vía staging S02 (`nowcast_dfm_*` / forward 2025-T1 = 1.1577 [1.0615, 1.2852]).
- Eval Triad: `hallucinations_v1`, rúbricas ADK, `tool_trajectory_avg_score`.
- API key únicamente en `apps/Asistente_RAG/.env` (+ `.gitignore`).
- Fallback extractivo (`rag_fallback.py`) cuando generate_content falla por cuota.

## Qué se descartó o requirió corrección manual
- **Batch embed de varios textos en una sola llamada:** Gemini Embedding 2 devolvía 1 vector por batch → mismatch Chroma; se corrigió a 1 request por chunk.
- **LLM `gemini-2.5-flash`:** 404 para usuarios nuevos → default `gemini-2.0-flash`.
- **Síntesis generativa ADK en smoke:** bloqueada por cuota free-tier generate (`limit: 0`); se validó el flujo con fallback extractivo + tools.
- **Vertex AI RAG:** fuera de alcance (arquitectura fija Chroma local).

## Hallazgos clave del proceso
1. App arrancable: `streamlit run apps/Asistente_RAG/app.py`.
2. Indexación real con Embedding 2 OK (85 chunks / 2 docs).
3. Tools verificadas: retrieve (hits CEED/ELIC) y DFM nowcast alineado a §2.3.
4. Smoke traces OK en modo extractivo; config RAG Triad lista para `adk eval` con cuota.
5. Free-tier de la key no permite `generate_content` (limit 0); embeddings sí.

## Lecciones y advertencias relevantes
- Rotar la API key tras haberla pegado en el chat.
- Pace embeddings (sleep + retry 429) en free tier.
- No commitear `.env`, `data/chroma/`, `data/uploads/`.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `apps/Asistente_RAG/**` | Aplicación completa |
| `apps/Asistente_RAG/.env` | Secretos locales (gitignored) |
| `apps/Asistente_RAG/eval/last_smoke_results.json` | Resultado smoke |
| `sections/.../results/construccion_asistente_rag.md` | Resultados §2.4.2 |
| `logs/uso_de_ia/S02/2.4.2/{prompt,output}.md` | Log IA |
| `requirements.txt` | + google-adk, chromadb, streamlit, google-genai, pypdf, dotenv |
| `.gitignore` | .env, chroma, uploads |
