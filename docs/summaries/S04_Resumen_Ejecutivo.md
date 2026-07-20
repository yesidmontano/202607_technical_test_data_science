# Resumen Ejecutivo — Sección S04: Impacto e Inferencia Causal

> **Prueba Técnica · Grupo SURA · Dirección de Analítica**  
> Secciones cubiertas: 4.1 Estrategia de identificación · 4.2 Estimación del efecto · 4.3 Valor económico

---

## 1. Encuadre

La ARL invirtió en un programa de prevención adoptado por **~1 800 empresas** en momentos distintos (2019–2022). La adopción **no fue aleatoria**. Se quiere saber si el programa **redujo la siniestralidad** y cuánto vale ese efecto en COP.

| Elemento | Definición |
|---|---|
| **Unidad** | Empresa–año (panel 2018–2024) |
| **Tratamiento** | Adopción del programa (`fecha_inicio` → cohorte g) |
| **Outcome** | `frecuencia_x100` (principal); `costo_por_trab` (secundario) |
| **Controles** | Nunca tratadas (ancla) · not-yet-treated (robustez) |
| **Staging** | `data/staging/S04/` (`causal_*`, `valor_economico_*`) |
| **Referencias** | `estrategia_identificacion_causal.md` · `estimacion_efecto.md` · `efecto_economico.md` (AGENTS #11–13) |

---

## 2. Estrategia de identificación (4.1)

**Diseño:** DiD escalonado **Callaway–Sant’Anna** (no TWFE simple).

| Pieza | Elección |
|---|---|
| Estimando | ATT del programa sobre frecuencia |
| Supuestos | Tendencias paralelas · no anticipación · SUTVA · overlap |
| Amenazas clave | Ashenfelter · COVID 2020 · heterogeneidad · confusores U |

OLS/matching solo no bastan: la selección concentra el programa en empresas de mayor riesgo; DiD usa variación dentro de empresa + contrafactual de controles.

---

## 3. Efecto estimado (4.2)

Estimador CS doubly robust (`csdid`); EE bootstrap (influence functions, biters=500).

| Métrica | Valor |
|---|---|
| **ATT simple** | **−0.428** |
| SE / IC95 | 0.131 · [−0.686, −0.171] |
| vs baseline pre (tratadas) | **≈ −11.7%** |
| Pre-trends (e&lt;0) | **OK** (0/3 significativos) |

**Robustez (frecuencia):** excluir 2020 (−0.45) y not-yet-treated (−0.44) confirman signo y magnitud.  
**Canal:** frecuencia sí; ATT de `costo_por_trab` **no significativo** → no monetizar por ese ATT directo.

Event-study: efecto desde e=0; pico e=2–3; se atenúa en e≥4. Cohorte **2021** la más clara; **2022** la más débil.

---

## 4. Valor económico (4.3)

Puente actuarial (no ROI neto — no hay costo del programa en COP):

\[
\mathrm{Valor}_{it}=\Bigl(-\frac{\mathrm{ATT}}{100}\Bigr)\times n\_trabajadores_{it}\times \mathbb{E}[\mathrm{costo}\mid\mathrm{siniestro}]
\]

| Métrica | @ costo medio | @ mediana |
|---|---|---|
| Siniestros evitados (acum. post) | **~1 891** | — |
| Valor bruto acumulado | **5.70 B** COP | 2.52 B |
| **Run-rate anual pleno** | **1.26 B**/año | 0.56 B/año |
| Banda ATT @ media (anual) | **[0.50, 2.02] B**/año | — |

Media ≫ mediana por cola de siniestros caros: reportar **ambos**.

---

## 5. ¿Qué tan causal es la conclusión?

| Capa | Nivel | Lectura |
|---|---|---|
| Frecuencia | **Moderado–alto** | CS + pre-trends + robustez COVID/NYT |
| Pesos (COP) | **Moderado** | Traducción vía E[costo]; no ATT directo en COP |

**Se rompe si:** fallan tendencias paralelas (S1), hay anticipación (S2), spillovers (S3), cambia la mix de gravedad (S4), se extrapola a cohorte 2022 / horizontes lejanos (S5), o el costo del programa supera los claims evitados (S6 — valor bruto ≠ ROI).

---

## 6. Mensaje para Dirección

El programa **sí redujo la frecuencia** de siniestralidad de las tratadas (~12% vs su nivel pre). En régimen pleno eso equivale a **~1.3 B COP/año** de claims evitados (banda **0.5–2.0 B**), como valor **bruto**. No presentarlo como ROI hasta incorporar el costo del programa; priorizar expansión donde la evidencia de frecuencia es más fuerte (cohortes 2019–2021) y monitorear 2022 / horizontes e≥4.

---

## 7. Artefactos clave

| Ruta | Contenido |
|---|---|
| `data/staging/S04/causal_resumen.parquet` | ATT, IC95, pre-trends, robustez |
| `data/staging/S04/causal_att_dynamic.parquet` | Event-study |
| `data/staging/S04/valor_economico_resumen.parquet` | KPIs de monetización |
| `data/staging/S04/valor_economico_supuestos.parquet` | Condiciones de falla S1–S6 |
| `docs/staging_data.md` | Contratos #112–127 |
| `sections/S04-.../4_2_.../estimacion_efecto.md` | Estimación (ref. AGENTS #12) |
| `sections/S04-.../4_3_.../efecto_economico.md` | Valor económico (ref. AGENTS #13) |
