# Output – Registro de Uso de IA

**ID:** `1.2.5`
**Tarea:** Detección y Tratamiento de Valores Atípicos – S01 / 1.2 EDA
**Sección del repositorio:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/04-analisis_outliers/`

---

## 1. Modelo utilizado

- **Modelo:** Cursor Grok 4.5

---

## 2. Por qué se usó

Se utilizó IA asistida para implementar de punta a punta el análisis 1.2.5 (detección multi-método + tratamiento + visualizaciones `sura_brand` + staging + documentación), alineado a los scripts previos de univariado/bivariado/temporal y a la decisión de negocio de no borrar extremos en un portafolio ARL.

---

## 3. Qué se tomó

### Scripts generados
| Archivo | Nivel de modificación |
|---|---|
| `analisis_outliers.py` | Generado íntegramente por IA; corrección menor de sintaxis (paréntesis sobrante) antes de la ejecución exitosa |

### Documentación generada
- `docs/staging_data.md`: secciones 15–20 (resumen, flags, tratados, impacto).
- `sections/.../results/Insights_EDA.md`: bloque **1.2.5 – Detección y Tratamiento de Valores Atípicos**.

### Decisiones de diseño tomadas por la IA (alineadas al EDA previo)
- Reutilizar staging (`siniestros_staging`, `empresa_siniestralidad_completa`); no releer raw.
- Prefijo de figuras `04_*`.
- Detección con **IQR 1.5×**, **MAD (z-mod ≥ 3.5)** y **P1–P99**.
- Tratamiento: **winsorización P1–P99** sin eliminar filas; columnas `*_w` / `log_*_w`.
- Conservar valores originales para análisis de cola / resultado técnico.
- Documentar que IQR/MAD son agresivos en colas pesadas (~12–15%) y que P1–P99 es el criterio operativo (~1–2%).

---

## 4. Qué se descartó o requirió corrección

- **Eliminación de filas** como tratamiento: descartado (en ARL los extremos son eventos reales).
- **Isolation Forest / LOF**: descartados por complejidad innecesaria en EDA descriptivo; tres métodos clásicos bastan para la decisión.
- **Winsorización más agresiva (P5–P95)**: descartada; recortaría demasiada masa útil.
- Corrección manual: error de sintaxis (`)` final) corregido antes del run limpio.

---

## 5. Artefactos producidos

### Datasets de staging (nuevos)
| Archivo | Filas | Columnas |
|---|---|---|
| `data/staging/S01/outliers_deteccion_resumen.parquet` | 9 | 25 |
| `data/staging/S01/siniestros_con_flags_outliers.parquet` | 39 894 | 23 |
| `data/staging/S01/empresa_con_flags_outliers.parquet` | 5 000 | 26 |
| `data/staging/S01/siniestros_tratados.parquet` | 39 894 | 22 |
| `data/staging/S01/empresa_siniestralidad_tratada.parquet` | 5 000 | 37 |
| `data/staging/S01/outliers_tratamiento_impacto.parquet` | 9 | 17 |

### Visualizaciones (9 figuras PNG a 150 DPI)
| Código | Figura |
|---|---|
| A1 | Boxplots outliers a nivel siniestro |
| A2 | Boxplots outliers a nivel empresa |
| A3 | Tasa de outliers por método (IQR / MAD / P1–P99) |
| B1 | Antes/después winsor – costo total |
| B2 | Antes/después winsor – días incapacidad |
| B3 | Antes/después winsor – costo acumulado empresa |
| C1 | Scatter costo × días con outliers P1–P99 |
| C2 | Tasa IQR por clase de riesgo |
| C3 | Impacto (reducción máx / skew) |

---

## 6. Estadísticas clave obtenidas (descriptivas)

| Métrica | Valor |
|---|---|
| IQR outliers `costo_total` | 13.0% |
| IQR outliers `dias_incapacidad` | 12.4% |
| Fuera P1–P99 `costo_total` | 2.0% |
| Clipados al winsorizar `costo_total` | 1.87% |
| Máx `costo_total` pre → post | $307M → $28.4M (−90.8%) |
| Skew `costo_total` pre → post | 12.16 → 3.45 (−71.7%) |
| Skew `dias_incapacidad` pre → post | 10.42 → 3.52 (−66.2%) |
| Outliers IQR costo en clase 1 → 5 | 4.1% → 17.4% |
| Flag compuesto P1–P99 (costo\|días) | 2.35% de siniestros |

---

## 7. Lecciones y advertencias

- En colas pesadas, **IQR no es regla de borrado**: marca ~1 de cada 8 siniestros.
- La tasa de outliers IQR **crece con `clase_riesgo`** → muchos extremos son estructurales; valorar winsorización estratificada en S03.
- Usar `*_w` para features; **no** usar tratados para medir carga catastrófica del portafolio.
- `prima_anual` tiene nulos (~11.6%); la detección/winsorización opera solo sobre válidos.

---

*Registro · S01-1.2.5 · Prueba Técnica Grupo SURA.*
