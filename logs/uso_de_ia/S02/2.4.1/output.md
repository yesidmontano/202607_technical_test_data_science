# Registro de Uso de IA — 2.4.1

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se requería definir la arquitectura del Asistente RAG documental (§2.4.1) antes de implementar: stack (Google ADK + ChromaDB + Streamlit + Gemini Embedding 2), tres flujos operativos (ingestión, chat con citas, nowcast DFM) y metodología de evaluación RAG Triad con métricas predefinidas de ADK a nivel traces y E2E.

## Qué se tomó
- Ubicación canónica de la app: `apps/Asistente_RAG`.
- Stack fijado por el requerimiento: Google ADK (agente/tools/eval), ChromaDB PersistentClient (vector store + persistencia), Streamlit (UI), Gemini Embedding 2 (`gemini-embedding-2`).
- Integración del DFM preferido de §2.3.2–2.3.3 (forward 2025-T1: 1.158 [1.062, 1.285] IC80%) como `FunctionTool`, reutilizando staging S02 / `nowcast_common` + lógica de `03_dfm.py`.
- RAG Triad mapeado a criterios ADK prebuilt:
  - Groundedness → `hallucinations_v1`
  - Answer Relevance → `rubric_based_final_response_quality_v1`
  - Context Relevance → `rubric_based_tool_use_quality_v1` + `tool_trajectory_avg_score`
- Diagramas mermaid de componentes, ingestión, Q&A y nowcast; checklist de revisión.

## Qué se descartó o requirió corrección manual
- **Vertex AI RAG corpus / `VertexAiRagRetrieval`:** descartado; contradice ChromaDB local como store.
- **Embedding solo nativo PDF multimodal (≤6 págs.):** solo como complemento; camino principal = extracción de texto + chunking (boletines DANE largos).
- **Reentrenar RF/BSTS en la app:** fuera de alcance; el tool operativo es solo DFM.
- **Métricas TruLens nativas:** no se usan como runtime; el Triad se implementa con funciones/criterios predefinidos de ADK.

## Hallazgos clave del proceso
1. Separación clara: Streamlit = UI; ADK = orquestación; Chroma = memoria; DFM = tool, no microservicio.
2. Metadatos de chunk (`doc_id`, `page`, `source_path`) son el contrato que habilita citas con link al PDF.
3. Evaluación en dos capas (traces por invocación + eval sets E2E) cubre el requerimiento de calidad y mitigación de alucinaciones sin inventar un framework externo.
4. `hallucinations_v1` es el ancla explícita de groundedness en ADK; context/answer relevance se cubren con rúbricas predefinidas + trayectoria de tools.

## Lecciones y advertencias relevantes
- Con corpus vacío o retrieval bajo umbral, el agente debe abstenerse; los eval cases “sin evidencia” son tan críticos como los de respuesta correcta.
- El IC80% del DFM no debe “narrarse” sin tool call; el prompt del agente debe forzar `run_nowcast_dfm` para cifras.
- `data/chroma/` y `data/uploads/` deben ir en `.gitignore` en la fase de implementación.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `sections/.../2_4_Asistente RAG/results/asistente_rag.md` | Arquitectura §2.4.1 (stack, estructura, 3 flujos, RAG Triad ADK) |
| `logs/uso_de_ia/S02/2.4.1/output.md` | Este log |
| `logs/uso_de_ia/S02/2.4.1/prompt.md` | Prompt de entrada (ya existente) |
