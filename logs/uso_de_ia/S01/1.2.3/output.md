# Output – Registro de Uso de IA

**ID:** `1.2.3`
**Tarea:** Análisis Bivariado EDA – S01 / 1.2 EDA
**Sección del repositorio:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/02-analisis_bivariado/`

---

## 1. Modelo utilizado

- **Modelo:** Grok 4.5 (Thinking)
- **Modo:** Conversación interactiva con lectura de contexto del repo, ejecución de scripts y escritura de artefactos

---

## 2. Por qué se usó

Se utilizó IA asistida para acelerar la escritura del script de análisis bivariado (`analisis_bivariado.py`) que cubre cuatro dimensiones de asociación (clase de riesgo, sector, tamaño, geografía), 13 visualizaciones con `sura_brand`, 7 datasets de staging reutilizables, actualización de `docs/staging_data.md` y hallazgos en `Insights_EDA.md`, manteniendo las convenciones del univariado previo (rutas relativas, semilla fija, PEP 8, panel con ceros).

---

## 3. Qué se tomó

### Scripts generados
| Archivo | Nivel de modificación |
|---|---|
| `analisis_bivariado.py` | Generado íntegramente por IA, con una corrección de API de Matplotlib tras el primer fallo de ejecución |

### Correcciones aplicadas en ciclo de depuración
1. **`Axes.boxplot(labels=...)` deprecado/eliminado** en la versión de Matplotlib del `.venv`: reemplazado por `tick_labels=...` en los 5 boxplots del script.

### Documentación generada
- `docs/staging_data.md`: ampliadas secciones 4–9 (panel completo + 5 resúmenes descriptivos).
- `sections/.../results/Insights_EDA.md`: bloque **1.2.3 – Análisis Bivariado** con tablas, figuras y síntesis descriptiva.

### Decisiones de diseño tomadas por la IA (alineadas al univariado)
- Reutilizar staging de 1.2.2 (`empresas_staging`, `siniestralidad_empresa`) en lugar de releer raw.
- Construir panel de **5 000 empresas** con ceros imputados (`empresa_siniestralidad_completa`) para evitar sesgo de selección.
- Análisis **solo descriptivo**; las pruebas formales de hipótesis se reservan para S01-1.3.
- Prefijo de figuras `02_*` para diferenciarlas del univariado (`01_*`).

---

## 4. Qué se descartó o requirió corrección

- Primer intento de ejecución falló por `labels=` en `boxplot`; corregido a `tick_labels=` y re-ejecutado con éxito.
- No se generaron mapas coropléticos (solo 7 departamentos; barras + composición de mix de riesgo son suficientes).
- Se eliminaron Kruskal-Wallis, Spearman con p-valor, anotaciones de pruebas y `bivariado_tests_asociacion.parquet` (corresponden a 1.3).

---

## 5. Artefactos producidos

### Datasets de staging (nuevos)
| Archivo | Filas | Columnas |
|---|---|---|
| `data/staging/S01/empresa_siniestralidad_completa.parquet` | 5 000 | 28 |
| `data/staging/S01/bivariado_resumen_clase_riesgo.parquet` | 5 | 15 |
| `data/staging/S01/bivariado_resumen_sector.parquet` | 15 | 15 |
| `data/staging/S01/bivariado_resumen_segmento.parquet` | 4 | 15 |
| `data/staging/S01/bivariado_resumen_departamento.parquet` | 7 | 15 |
| `data/staging/S01/bivariado_resumen_ciudad.parquet` | 7 | 15 |

### Visualizaciones (13 figuras PNG a 150 DPI)
| Código | Figura |
|---|---|
| A1 | Boxplots frecuencia / costo / severidad por clase de riesgo |
| A2 | Barras de medianas – gradiente clase de riesgo |
| A3 | Share del costo del portafolio por clase |
| B1 | Frecuencia relativa mediana por sector |
| B2 | Costo acumulado mediano por sector |
| B3 | Heatmap sector × clase de riesgo |
| C1 | Scatter tamaño vs conteo y vs tasa (log) |
| C2 | Boxplots por segmento de tamaño |
| C3 | Scatter prima anual vs costo acumulado |
| D1 | Frecuencia y costo por departamento |
| D2 | Frecuencia y costo por ciudad |
| D3 | Composición apilada de clase de riesgo por departamento |
| E1 | Heatmap de correlación por rangos (descriptivo) |

---

## 6. Estadísticas clave obtenidas (descriptivas)

| Métrica | Valor |
|---|---|
| Ratio frecuencia mediana Clase5 / Clase1 | 6.9× |
| Share costo clases 4+5 | 73.3% |
| Top sector (freq. mediana) | Construcción 36.0 |
| Bottom sector (freq. mediana) | TIC 5.9 |
| Rango medianas frecuencia entre deptos | 2.9 pts |

---

## 7. Lecciones y advertencias

- En Matplotlib reciente, `boxplot(..., labels=)` fue reemplazado por `tick_labels=`; verificar al portar código de ejemplos antiguos.
- Ciudad y departamento son **redundantes** en este dataset sintético (mapeo 1:1); documentarlo evita features duplicadas en modelado.
- Preferir `empresa_siniestralidad_completa` sobre `siniestralidad_empresa` cuando el modelo deba incluir empresas sin siniestros.
- El bivariado 1.2.3 es descriptivo; las pruebas formales van en S01-1.3.

---

*Registro · S01-1.2.3 · Prueba Técnica Grupo SURA.*
