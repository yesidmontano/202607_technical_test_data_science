# Output – Registro de Uso de IA

**ID:** `1.2.4`
**Tarea:** Análisis Temporal y de Estacionalidad – S01 / 1.2 EDA
**Sección del repositorio:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/03-analisis_temporal/`

---

## 1. Modelo utilizado

- **Modelo:** Cursor Grok 4.5 (Thinking)
- **Modo:** Conversación interactiva con lectura de contexto del repo, ejecución de scripts y escritura de artefactos

---

## 2. Por qué se usó

Se utilizó IA asistida para acelerar la escritura del script de análisis temporal (`analisis_temporal.py`) que cubre estructura temporal (series mensuales/anuales, YoY, mix AT/EL) y estacionalidad (índice mensual, heatmap año×mes, boxplots), 9 visualizaciones con `sura_brand`, 5 datasets de staging reutilizables (incluido panel empresa×año para CV temporal), actualización de `docs/staging_data.md` y hallazgos en `Insights_EDA.md`, manteniendo las convenciones de univariado/bivariado previos.

---

## 3. Qué se tomó

### Scripts generados
| Archivo | Nivel de modificación |
|---|---|
| `analisis_temporal.py` | Generado íntegramente por IA; ejecutado con éxito en el primer intento |

### Documentación generada
- `docs/staging_data.md`: secciones 10–14 (agregados temporales + panel empresa×año + persistencia).
- `sections/.../results/Insights_EDA.md`: bloque **1.2.4 – Análisis Temporal y Estacionalidad**.

### Decisiones de diseño tomadas por la IA (alineadas al EDA previo)
- Reutilizar `siniestros_staging` / `empresas_staging` (no releer raw).
- Prefijo de figuras `03_*`.
- Panel empresa×año con producto cartesiano y ceros (análogo al panel completo del bivariado).
- Target operativo `alta_siniestralidad` = **Top 10%** por `n_siniestros` dentro de cada año (definición CRISP-DM ajustada por el usuario; reemplaza “> media”).
- Análisis descriptivo; sin descomposición statsmodels (no instalado) ni pruebas formales (reservadas a 1.3).

### Ajuste posterior (misma sesión / follow-up)
- Regenerado staging y figura `03_C3` para reflejar Top 10% + tasa de retención del label (~50%).
- Actualizados `docs/staging_data.md`, `Insights_EDA.md` (1.2.4) y `.agents/AGENTS.md`.

---

## 4. Qué se descartó o requirió corrección

- No se usó descomposición estacional STL/classic (dependencia `statsmodels` ausente); se optó por índices estacionales + heatmap + boxplots, suficientes para concluir amplitud débil.
- No se modelaron efectos de día de la semana (granularidad del negocio es empresa-año).
- No se generaron pruebas formales de estacionalidad (Kruskal por mes, etc.); quedan para S01-1.3 si se requieren.

---

## 5. Artefactos producidos

### Datasets de staging (nuevos)
| Archivo | Filas | Columnas |
|---|---|---|
| `data/staging/S01/temporal_mensual.parquet` | 84 | 15 |
| `data/staging/S01/temporal_anual.parquet` | 7 | 14 |
| `data/staging/S01/estacionalidad_mes.parquet` | 12 | 15 |
| `data/staging/S01/temporal_empresa_anio.parquet` | 35 000 | 13 |
| `data/staging/S01/temporal_persistencia_yoy.parquet` | 6 | 4 |

### Visualizaciones (9 figuras PNG a 150 DPI)
| Código | Figura |
|---|---|
| A1 | Serie mensual + media móvil 3m |
| A2 | Estructura anual (volumen / costo / severidad) |
| A3 | Composición apilada AT/EL por año |
| B1 | Índice estacional mensual de volumen |
| B2 | Heatmap año × mes |
| B3 | Boxplots de volumen por mes entre años |
| C1 | Variación YoY (volumen y costo) |
| C2 | Índices estacionales de costo y severidad |
| C3 | Persistencia empresa–año (corr t vs t+1) |

---

## 6. Estadísticas clave obtenidas (descriptivas)

| Métrica | Valor |
|---|---|
| Amplitud índice estacional volumen | 3.8 pp (ene 1.018 → jun 0.980) |
| YoY volumen extremo | +15.7% (2019), −14.1% (2020) |
| Mix AT medio | ~86% |
| Persistencia media `n_siniestros` t→t+1 | 0.70 |
| Persistencia media `frecuencia_x100` t→t+1 | 0.18 |
| Target `alta_siniestralidad` | Top 10% (~500 empresas/año; umbral n ≥ 3) |
| Retención media del label Top 10% t→t+1 | 50.1% |

---

## 7. Lecciones y advertencias

- Estacionalidad mensual es **débil** en este dataset sintético; no priorizar dummies de mes frente a lags empresa-año.
- El panel `temporal_empresa_anio` habilita CV temporal sin leakage si las features de siniestros se construyen solo con años < T.
- La persistencia alta del conteo absoluto refuerza un baseline lag simple antes de modelos más complejos en S03.
- Costo/severidad muestran más amplitud mensual que el volumen, pero con colas pesadas esa señal es ruidosa.

---

*Registro · S01-1.2.4 · Prueba Técnica Grupo SURA.*
