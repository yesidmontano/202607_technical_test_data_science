# Resumen Ejecutivo — Sección S03: Reto de Negocio

> **Prueba Técnica · Grupo SURA · Dirección de Analítica**  
> Secciones cubiertas: 3.1 Pregunta de negocio · 3.2 Modelado frecuencia–severidad · 3.3 Proyección de portafolio · 3.4 Documentación y recomendación

---

## 1. Encuadre

La Dirección necesita anticipar el **resultado técnico** del portafolio y decidir dónde ajustar **suscripción** y **tarifa**.

> *¿Cuál es el costo esperado de siniestralidad del próximo año por empresa y por clase, y en qué segmentos la prima no cubre ese costo?*

| Elemento | Definición |
|---|---|
| **Unidad de análisis** | Empresa (`id_empresa`) y clase de riesgo |
| **Target de negocio** | Costo esperado `E[Costo] = E[N] × E[Sev\|X]` y loss / combined ratio |
| **Validación** | Train 2019–2023 · holdout 2024 · proyección features 2024 → 2025 |
| **Staging** | `data/staging/S03/` (`supuestos_*`, `modelo_*`, `proyeccion_*`) |
| **Referencias** | `pregunta.md` · `model_frecuencia_serveridad.md` · `proyeccion_portafolio.md` · `documentacion_reto_negocio.md` |

---

## 2. Pregunta y supuestos (3.1)

**Decisiones que soporta el modelo:** (1) ajuste de suscripción por empresa de alto costo esperado; (2) ajuste de tarifa por segmento insuficiente.

| Supuesto | Veredicto | Implicación |
|---|---|---|
| Independencia frecuencia–severidad | **RECHAZADO** (ρ≈0.35–0.42) | Severidad condicionada a clase × tamaño (+ gravedad) |
| Estabilidad del mix portafolio | **SOSTENIDO** (JS YoY≈0.05) | Usar mix reciente como proxy del próximo año |
| Prima refleja el riesgo | **SOSTENIDO** con bolsas (ρ prima–costo≈0.80; 25/148 segmentos LR>1) | Tarifa rankea bien; hay celdas a corregir |

---

## 3. Modelo frecuencia–severidad (3.2)

| Componente | Familia | Especificación |
|---|---|---|
| **Frecuencia** | Binomial Negativa + offset `log(n_trabajadores)` | `n ~ C(clase)+C(segmento)+C(sector)+log1p(lag)` · α≈0.114 |
| **Severidad** | Lognormal AT/EL separados | `log(costo) ~ C(clase)+C(segmento)+C(gravedad)`; pricing marginaliza tipo y gravedad |
| **Pure premium** | `E[N]×E[Sev\|X]` | Por empresa y agregado por clase |

**Holdout 2024:** frecuencia Spearman≈0.60 · costo Spearman≈0.57 · portafolio pred/obs≈**0.99**.  
**IRR clase 5 vs 1 = 5.0×.** Clases 4–5 ≈ **72%** del costo esperado proyectado.

---

## 4. Proyección de portafolio (3.3)

Universo con prima > 0 (n=4 421). Combined ratio = LR + expense ratio (supuesto **25%**; adverso 27%).

| Escenario | Siniestralidad | Primas | LR | CR | Resultado técnico |
|---|---|---|---|---|---|
| **Base** | 15.9 B | 28.8 B | 55% | **80%** | **+5.7 B** |
| **Adverso** (+36% YoY máx. histórico) | 21.6 B | 28.8 B | 75% | **102%** | **−0.6 B** |

**Incertidumbre (modelo + proceso):** IC90 siniestralidad ≈ [9.8, 22.6] B · P(CR>100%) ≈ **8%**.

---

## 5. Recomendación (3.4)

1. **Suscripción:** condicionar alta exposición / nuevas afiliaciones en el Top de `costo_pred` y en las **169 empresas** con LR pred>1 (foco Micro + clases 4–5).
2. **Tarifa:** alzar en los **25 segmentos** clase×sector×tamaño con LR histórico > 1 (prioridad Micro en sectores de alto costo).
3. **Monitoreo:** planificar con CR base ~80%; usar adverso CR>100% como **umbral de alerta** (no solo el punto central).
4. **Gobernanza:** pricing con E[Sev] marginalizado; no confundir con modelo claim-level que usa gravedad observada.

---

## 6. Límites y riesgos (lectura rápida)

| Riesgo | Lectura |
|---|---|
| ER supuesto (sin gastos en raw) | CR es indicativo → sensibilizar ±5 pp |
| Severidad promedia gravedad | Cola grave/mortal subestimada a nivel empresa |
| Sin cópula freq–sev | Estrés extremo puede superar el adverso puntual |
| Prima estática | No modela cambio de tarifa ni mix mid-year |
| Buen portafolio ≠ precisión individual | Cola pesada; priorizar ranking y calibración agregada |

---

## 7. Mensaje para Dirección

El portafolio llega al próximo año con **margen técnico en base (CR≈80%)**, pero un año de siniestralidad como el peor histórico **borra ese margen (CR≈102%)**. El valor está en **ajustar suscripción y tarifa en Micro / clases altas / segmentos con LR>1**, no en mover la tarifa promedio de todo el portafolio.

---

## 8. Artefactos clave

| Ruta | Contenido |
|---|---|
| `data/staging/S03/modelo_pred_empresa.parquet` | E[N], E[Sev], E[Costo], LR por empresa |
| `data/staging/S03/proyeccion_escenarios.parquet` | KPIs base / adverso |
| `data/staging/S03/proyeccion_empresa.parquet` | CR y resultado técnico por empresa × escenario |
| `docs/staging_data.md` | Contratos #88–111 |
| `sections/S03-.../3_4_.../documentacion_reto_negocio.md` | Documentación integral (ref. AGENTS #10) |
