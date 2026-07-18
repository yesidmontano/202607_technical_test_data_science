# Resumen Ejecutivo — Sección S02: Modelación Económica y Sectorial

> **Prueba Técnica · Grupo SURA · Dirección de Analítica**  
> Secciones cubiertas: 2.1 Caracterización · 2.2 Modelamiento de relaciones · 2.3 Nowcast · 2.4 Asistente RAG

---

## 1. Encuadre de la sección

El sector construcción es de alta accidentalidad y alta sensibilidad al ciclo económico. La pregunta analítica de S02 es:

> *¿Cómo anticipar la siniestralidad AT del sector construcción a partir de su ciclo real, con rigor econométrico y soporte documental?*

| Elemento | Definición |
|---|---|
| **Unidad de análisis** | Sector construcción (agregado trimestral / mensual) |
| **Variable objetivo operativa** | Frecuencia AT por 100 trabajadores (`freq_at`) |
| **Fuentes externas** | DANE: ELIC, CEED, IPOC, EC (+ panel sintético `macro_sectorial.csv`) |
| **Staging** | `data/staging/S02/` (contratos documentados en `docs/staging_data.md`) |
| **Producto analítico** | Nowcast trimestral + asistente RAG integrado al flujo |
| **Restricción clave** | Muestra corta (T≤18–33 trimestres según fuente); ragged-edge de publicación |

---

## 2. Caracterización sectorial (2.1)

Se identificaron y exploraron cuatro fuentes DANE del ciclo constructor. El hallazgo estructural es una **segmentación dual**: edificación e infraestructura no co-mueven.

### 2.1 Fuentes y rezagos

| Fuente | Frecuencia | Rezago ~ | Rol |
|---|---|---|---|
| **ELIC** | Mensual / ref. anual | ~45 d | Señal líder (intención); latencia 6–18 meses hacia CEED |
| **CEED** | Trimestral | ~45 d | Coincidente edificación; ancla del ciclo físico |
| **IPOC** | Trimestral | ~48–50 d | Coincidente infraestructura; **bloque separado** |
| **EC** | Mensual | ~38 d | Bridge de alta frecuencia; llegada más temprana |

### 2.2 Hallazgos estructurales

| Dimensión | Hallazgo clave |
|---|---|
| **Dualidad del ciclo** | Spearman CEED–IPOC = **−0.72** (2020–2026-I) → no mezclar en un solo factor |
| **Co-movimiento edificación** | CEED–EC ρ ≈ **+0.79** → EC es bridge natural hacia CEED |
| **Lead estructural** | ELIC anticipa CEED con **6–18 meses**; ELIC 2026 (+33% anual) aún no se refleja en CEED/EC |
| **Estacionalidad EC** | Amplitud **26.8 pp** (valle ene / pico oct) → el mes **sí** importa para nowcast |
| **Jerarquía de llegada** | EC (~día 38) → ELIC (~45) → CEED/IPOC (~45–50) |

### 2.3 Contrato hacia 2.2 y 2.3

- **2.2:** modelar edificación (CEED/EC) e infraestructura (IPOC) en bloques separados; ELIC como predictor desfasado (lags 2–6 trimestres).
- **2.3:** privilegiar EC + AT parcial cuando CEED del trimestre T aún no está publicado.
- Staging listo: `panel_fuentes_trimestral`, `ec_mensual_clean`, `elic_anual_ref`, `ipoc_trimestral_clean`.

---

## 3. Modelamiento de relaciones (2.2)

Se modeló la dinámica ciclo ↔ frecuencia AT con estacionariedad, cointegración, IRF/FEVD y robustez (ADF+KPSS+PP, CCF, Johansen corregido).

### 3.1 Especificación definitiva

| Decisión | Evidencia |
|---|---|
| **VAR(1) en primeras diferencias** (bloque edificación) | Series I(1); EG+Johansen r=0 en n=18; Portmanteau limpio en T=18 |
| **No VECM** | EG p≈0.99; Johansen Reinsel–Ahn r̂=0 (el r̂=2 de T=12 era sesgo de muestra) |
| **No VAR en niveles** | Riesgo de regresión espuria con I(1) |
| **No ADL/OLS como modelo canónico** | Mejor AIC, pero no responde a dinámica multi-ecuacional ni IRF |
| **IPOC en bloque separado** | Fase distinta vs AT; no mezclar con CEED/EC |
| **Ventana preferente T=18** (AT+CEED) | Portmanteau p=0.74; CUSUM estable; T=12+EC solo para bridge |

### 3.2 Dinámica documentada

| Hallazgo | Magnitud | Lectura |
|---|---|---|
| IRF CEED → AT (h=1) | **+0.037** (~+3.7% en log) | Shock de edificación eleva AT al trimestre siguiente; se disipa en h=6–8 |
| FEVD AT (h=4–8) | Propia ~79–81%; CEED ~10–11%; EC ~9–10% | Ciclo aporta ~20% de la varianza; inercia propia domina |
| CCF CEED→AT pico | **k=6**, ρ≈**+0.58** | Canal de mediano plazo alineado con rezago 6–18 meses de §2.1; el VAR(1) no lo embebe |

### 3.3 Diagnósticos finales (ventana preferente T=18)

| Diagnóstico | Resultado |
|---|---|
| Portmanteau | **Pasa** (p≈0.74) |
| ARCH-LM | Pasa |
| Jarque-Bera | Pasa |
| CUSUM | Sin quiebre estructural (p≈0.85) |

**Límite reconocido:** con T≤18 no es estimable un VAR(p≥4–6) que capture el lead CCF k=6; ese canal se traslada al nowcast como evidencia de rezago / bridges.

---

## 4. Nowcast de frecuencia AT (2.3)

Se produjo un nowcast trimestral con information set **ragged-edge** (≈día 40 del trimestre), comparando tres familias en validación temporal estricta.

### 4.1 Comparativo de modelos (test 2024)

| Modelo | MAE | RMSE | MAPE (%) | Rol |
|---|---:|---:|---:|---|
| **DFM (seleccionado)** | **0.077** | **0.098** | **6.6** | Estimador puntual operativo |
| Random Forest | 0.118 | 0.153 | 10.3 | Descartado (val frágil) |
| BSTS | 0.136 | 0.209 | 12.6 | Cota de estrés / reservas |

**Modelo operativo:** DFM 1 factor (Kalman) + puente OLS anclado en AT parcial del mes 1.  
**No usar RF en producción.** BSTS solo como escenario adverso.

### 4.2 Nowcast forward 2025-T1

| Escenario | Frecuencia AT / 100 trab. | Uso |
|---|---:|---|
| **Central (DFM)** | **1.158** | Base para proyección de cartera |
| IC 80% DFM | **[1.062, 1.285]** | Banda ±10.7% (bootstrap residual) |
| BSTS (estrés) | 1.379 [0.965, 1.793] | Reservas / campañas conservadoras |

Lectura: ~**+6.3%** vs promedio histórico reciente (≈1.09) → presión siniestral moderada, coherente con CEED expansivo y empleo lag-1 alto.

### 4.3 Umbrales de alerta ARL

| Umbral | Frecuencia DFM | Acción |
|---|---|---|
| 🟢 Normal | < 1.05 | Monitoreo rutinario |
| 🟡 Alerta | 1.05 – 1.20 | Refuerzo preventivo CR4–CR5 |
| 🔴 Crítico | > 1.20 | Brigadas de campo; revisión tarifación |

> **Estado 2025-T1:** 🟡 **Alerta moderada** (DFM = 1.158)

El nowcast permite activar prevención **6–8 semanas** antes del reporte oficial; **no reemplaza** el AT oficial (MAPE ≈6.6%) ni discrimina empresa individual (eso es S03).

---

## 5. Asistente RAG (2.4)

Se construyó un asistente de recuperación y generación aumentada integrado al flujo de modelación — no como pieza aislada.

### 5.1 Arquitectura

| Capa | Tecnología |
|---|---|
| UI | Streamlit (Chat / Carga / Nowcast) |
| Agente | Google ADK (`Agent`, `Runner`, tools) |
| Embeddings | Gemini Embedding 2 (`gemini-embedding-2`, dim 768) |
| Vector store | ChromaDB `PersistentClient` |
| Nowcast | Tool `run_nowcast_dfm` → artefacto DFM de §2.3 |
| Evaluación | RAG Triad (groundedness / answer / context relevance) |

Ubicación: `apps/Asistente_RAG/`.

### 5.2 Estado de construcción

| Componente | Resultado |
|---|---|
| Corpus seed | CEED + ELIC → **85 chunks** / 2 docs |
| `retrieve_docs` | ✅ (p. ej. top hit CEED p.42) |
| `run_nowcast_dfm("2025-T1")` | ✅ ŷ=**1.158** IC80% **[1.062, 1.285]** |
| Smoke traces | ✅ retrieve + nowcast con citas |
| Fallback extractivo | ✅ ante cuota LLM free-tier (`generate_content` limit 0) |
| Eval Triad E2E completa | Configurada; corrida `adk eval` pendiente de cuota generate |

### 5.3 Mitigación de alucinaciones

- Respuestas condicionadas a chunks recuperados + citas con enlace al PDF.
- Abstención cuando no hay evidencia en el corpus.
- Si falla el LLM: modo extractivo (`rag_fallback`) sin inventar cifras.
- API key solo en `.env` (gitignored); `data/chroma/` y `data/uploads/` fuera de git.

---

## 6. Síntesis: Lo que S02 Condiciona a S03–S06

### Decisiones operativas obligatorias

| Decisión | Evidencia |
|---|---|
| **Bloques separados edificación vs infraestructura** | CEED–IPOC ρ=−0.72; IRF IPOC distinta de CEED |
| **VAR(1) en diferencias; no VECM** | I(1); EG+Johansen r=0; diagnósticos OK en T=18 |
| **Canal mediano plazo vía CCF k=6 / bridges** | No estimable en VAR(p≥6) con T corto |
| **Nowcast operativo = DFM + AT parcial** | MAPE test 6.6%; RF descartado; BSTS = estrés |
| **Alerta 2025-T1 = moderada (1.158)** | IC 80% [1.062, 1.285]; umbral 1.05–1.20 |
| **RAG como soporte documental del flujo** | Tools retrieve + DFM; citas obligatorias |

### Implicaciones por sección siguiente

| Sección | Qué hereda de S02 |
|---|---|
| **S03** (reto de negocio / portafolio) | Nowcast DFM como input macro de construcción; no sustituye modelos empresa-nivel |
| **S04–S05** | Contexto cíclico para interpretar efectos de prevención / adopción en construcción |
| **S06** (modelo a producto) | Arquitectura DFM ragged-edge + app RAG (`apps/Asistente_RAG`) como base de producto |

### Fuentes de datos y artefactos clave

| Artefacto | Rol |
|---|---|
| `data/staging/S02/panel_fuentes_trimestral*` | Panel ciclo DANE alineado |
| `data/staging/S02/nowcast_*` / `nowcast_forward_2025T1*` | Predicciones, métricas e IC del nowcast |
| `.../2_1_Caracterizacion/results/caracterizacion.md` | Ref. autoritativa 4 |
| `.../2_2_Modelamiento de relaciones/results/relaciones.md` | Ref. autoritativa 5 |
| `.../2_3_Nowcast/results/nowcast.md` | Ref. autoritativa 6 |
| `.../2_4_Asistente RAG/results/asistente_rag.md` | Ref. autoritativa 7 |
| `apps/Asistente_RAG/` | Producto RAG + tool nowcast |

---

*Análisis realizado con `sura_brand` · Sección S02 – Resumen Ejecutivo · Prueba Técnica Grupo SURA.*
