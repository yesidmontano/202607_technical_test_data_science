# Resumen Ejecutivo — Sección S05: Sistema Recomendador de Servicios

> **Prueba Técnica · Grupo SURA · Dirección de Analítica**  
> Secciones cubiertas: 5.1 Diseño · 5.2 Prototipo · 5.3 Paso a producción

---

## 1. Encuadre

El área quiere recomendar a cada empresa los servicios de prevención con **mayor probabilidad de adopción** y de **reducir su riesgo**, incluyendo empresas **sin histórico** (cold-start).

| Elemento | Definición |
|---|---|
| **Unidad** | Empresa × servicio (ranking top-K) |
| **Señales** | `uso_servicios` (implícito) · `catalogo_servicios` · `empresas` (+ `costo_pred` S03) |
| **Portafolio** | 5 000 empresas · 40 servicios · 98 736 usos (2022–2024) |
| **Cold-start** | **500 (10%)** sin ningún uso |
| **Staging** | `data/staging/S05/` (`recomendador_*`, `prototipo_*`) |
| **Referencias** | `diseño_recomendador.md` · `prototipo_recomendador.md` · `paso_produccion.md` (AGENTS #14–16) |

---

## 2. Diseño (5.1)

Tres candidatos evaluados con proxies offline y score multi-criterio (adopción · cold · riesgo · explicabilidad):

| Diseño | Familia | Cold | Hit@5 proxy | Score decisión |
|---|---|---|---:|---:|
| A | Contenido + popularidad de segmento | Nativo | 0.46 | 0.59 |
| B | CF item–item implícito | No nativo | **0.78** | 0.33 |
| **C ★** | **Híbrido adopción × riesgo (warm/cold)** | **Nativo** | 0.62 | **0.82** |

**Hechos que condicionan:** densidad warm **25%** (CF viable); match `dirigido_a` cubre 100% empresas pero solo **~10%** de usos reales → contenido necesario para cold, insuficiente solo; objetivo de negocio **dual**.

**Elección:** **Diseño C** — score \(\alpha\cdot\mathrm{adopcion}+(1-\alpha)\cdot\mathrm{riesgo}\); rama warm = CF+contenido; rama cold = contenido+popularidad+prior de riesgo.

---

## 3. Prototipo y evaluación (5.2)

Validación **temporal**: train ≤2023 / test 2024; GT = nuevas adopciones 2024. Cold de adopción vía **cold simulado** (historial oculto); true cold solo guardrails (sin GT).

**α\* = 0.70** (máx ΔRisk@5 s.t. NDCG@5 ≥ 95% del máximo).

| Métrica | Warm | Cold sim | True cold |
|---|---:|---:|---:|
| NDCG@5 | **0.402** | 0.108 | — |
| Recall@5 | **0.490** | 0.131 | — |
| ΔRisk@5 vs popularidad | **+0.173** | +0.131 | +0.125 |
| Coverage / % K=5 | 97.5% / 100% | 95% / 100% | **95% / 100%** |

**Trade-off vs B:** C cede ~8 pp NDCG a cambio de **≈2×** el lift de prior preventivo (ΔRisk +0.17 vs +0.08). Alineado al enunciado dual.

**Entrega operativa:** `prototipo_recomendaciones` — 5 000 empresas × top-5 @ α=0.70.

**Límite clave offline:** ΔRisk es proxy (categoría×perfil), no efecto causal de siniestros; true cold no tiene GT de adopción.

---

## 4. Paso a producción e impacto (5.3)

| Capa | Propuesta |
|---|---|
| **Datos** | Fabric Lakehouse + pipelines → feature store (uso, catálogo, empresas, riesgo S03) |
| **ML** | Azure ML: train/register, versionado, drift; **batch endpoint** programado (DAG) |
| **Serving inicial** | Batch top-K → Lakehouse; online solo si el canal lo exige |
| **Impacto real** | Experimento **A/B** (control vs C): adopción incremental → Δ frecuencia/costo → COP; dashboard Power BI |
| **No confundir** | NDCG offline ≠ impacto de negocio |

---

## 5. Mensaje para Dirección

Llevar a producción el **híbrido C @ α=0.70**: cubre el 10% cold, mantiene adopción razonable en warm (Recall@5≈49%) y desplaza el top-5 hacia servicios de mayor prior preventivo. Escalar tras **A/B** que demuestre adopción y, en horizonte medio, menor siniestralidad — no solo métricas de ranking. Si el KPI fuera únicamente adopción, B sería la alternativa (con fallback contenido para cold).

---

## 6. Artefactos clave

| Ruta | Contenido |
|---|---|
| `data/staging/S05/recomendador_diseños_resumen.parquet` | Comparación A/B/C (5.1) |
| `data/staging/S05/prototipo_resumen.parquet` | α\*, NDCG/Recall/ΔRisk, guardrails |
| `data/staging/S05/prototipo_recomendaciones.parquet` | Top-5 por empresa |
| `data/staging/S05/prototipo_alpha_curve.parquet` | Frontera adopción–riesgo |
| `docs/staging_data.md` | Contratos #128–145 |
| `sections/S05-.../5_1_.../diseño_recomendador.md` | Diseño (ref. AGENTS #14) |
| `sections/S05-.../5_2_.../prototipo_recomendador.md` | Prototipo (ref. AGENTS #15) |
| `sections/S05-.../5_3_.../paso_produccion.md` | Producción (ref. AGENTS #16) |
