# Output – Registro de Uso de IA

**ID:** `1.2.6`
**Tarea:** Correlación y Colinealidad entre Predictores Candidatos – S01 / 1.2 EDA
**Sección del repositorio:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/05-analisis_correlaciones/`

---

## 1. Modelo utilizado

- **Modelo:** Grok 4.5

---

## 2. Por qué se usó

Se utilizó IA asistida para implementar de punta a punta el análisis 1.2.6 (matrices Spearman/Pearson, VIF multi-set, pares \|ρ\| altos, asociaciones panel con lag, visualizaciones `sura_brand`, staging y documentación), alineado a los scripts 01–04 y a la separación predictor vs outcome/target.

---

## 3. Qué se tomó

### Scripts generados
| Archivo | Nivel de modificación |
|---|---|
| `analisis_correlaciones.py` | Generado íntegramente por IA; ajuste de texto de recomendación tras ver VIF bajos en la primera ejecución |

### Documentación generada
- `docs/staging_data.md`: secciones 21–26 (matrices, pares, VIF, recomendación).
- `sections/.../results/Insights_EDA.md`: bloque **1.2.6 – Correlación y Colinealidad**.

### Decisiones de diseño tomadas por la IA (alineadas al EDA previo)
- Reutilizar staging tratado (`empresa_siniestralidad_tratada`) + panel (`temporal_empresa_anio`); no releer raw.
- Prefijo de figuras `05_*`.
- Predictores numéricos: `clase_riesgo`, `log_n_trabajadores(_w)`, `log_prima_anual_w`, `antiguedad_meses`, `log_lag_n_siniestros`.
- Outcomes excluidos del VIF de predictores: conteo, frecuencia, costo, `tiene_siniestro` / `alta_siniestralidad`.
- VIF vía OLS en NumPy (sin `statsmodels`/`sklearn`, no listados en `requirements.txt`).
- Heatmaps con matriz precomputada (evita doble `.corr()` de `sb.correlation_heatmap`).
- Umbrales: \|ρ\| ≥ 0.70; VIF advertencia ≥ 5; severo ≥ 10.

---

## 4. Qué se descartó o requirió corrección

- **Instalar statsmodels/sklearn solo para VIF:** descartado; VIF implementado con `numpy.linalg.lstsq`.
- **Tratar prima y tamaño como mutuamente excluyentes a priori:** corregido tras el run — VIF max ≈ 1.68; pueden coexistir; ρ Spearman ≈ 0.59 es solo redundancia moderada.
- **Pruebas de hipótesis / p-valores sobre correlaciones:** no incluidas (pertenecen a S01-1.3).
- **VIF sobre dummies de sector/geografía:** documentado como categóricos fuera del VIF numérico (recomendación cualitativa desde 1.2.3).

---

## 5. Artefactos producidos

### Datasets de staging (nuevos)
| Archivo | Filas | Columnas |
|---|---|---|
| `data/staging/S01/correlacion_predictores_spearman.parquet` | 64 | 5 |
| `data/staging/S01/correlacion_predictores_pearson.parquet` | 16 | 5 |
| `data/staging/S01/correlacion_pares_altos.parquet` | 3 | 8 |
| `data/staging/S01/correlacion_predictor_vs_target.parquet` | 28 | 7 |
| `data/staging/S01/colinealidad_vif.parquet` | 17 | 8 |
| `data/staging/S01/predictores_recomendacion.parquet` | 7 | 9 |

### Visualizaciones (9 figuras PNG a 150 DPI)
| Código | Figura |
|---|---|
| A1 | Heatmap Spearman predictores + outcomes |
| A2 | Heatmap Pearson predictores (log/winsor) |
| A3 | Heatmap predictor × target |
| B1 | VIF set panel con lag |
| B2 | Pares \|ρ\| ≥ 0.70 |
| B3 | Scatter prima vs tamaño |
| C1 | Comparación VIF / κ entre sets |
| C2 | Heatmap set reducido C (sin prima) |
| C3 | Asociaciones panel con lag |

---

## 6. Estadísticas clave obtenidas (descriptivas)

| Métrica | Valor |
|---|---|
| ρ Spearman `clase_riesgo` ~ `frecuencia_x100_w` | 0.73 |
| ρ Spearman `log_prima` ~ `log_n_trabajadores` | 0.59 |
| ρ Pearson `log_prima` ~ `log_n_trabajadores` | 0.30 |
| ρ Spearman `log_n_siniestros_w` ~ `log_costo_empresa_w` | 0.90 |
| VIF máx set A (transversal) | 1.22 |
| VIF máx set B (panel + lag) | 1.68 |
| VIF máx set C (sin prima) | 1.68 (κ≈4.0, mejor condición) |
| VIF máx set D (sin tamaño) | 1.25 |
| ρ Spearman lag → `n_siniestros` (panel) | 0.44 |
| ρ Spearman lag → `alta_siniestralidad` | 0.38 |
| Pares predictor–predictor con \|ρ\| ≥ 0.70 | 0 |

---

## 7. Lecciones y advertencias

- En este portafolio, **colinealidad clásica (VIF) no es el cuello de botella**; la señal fuerte está en predictor→outcome (`clase_riesgo`, prima, lag).
- Preferir **Spearman** sobre Pearson para asociaciones con colas pesadas / winsor.
- El lag debe construirse con **shift por empresa** (ya reflejado en el análisis panel); no usar el conteo del mismo año como feature del target de ese año.
- `sector` sigue siendo prioridad alta por el bivariado 1.2.3, aunque no entre en la matriz VIF numérica.
- Feature set sugerido S03: `clase_riesgo` + exposición (`log_n_trabajadores`) + `log_lag_n_siniestros` + `sector` (+ prima opcional).

---

*Registro generado como parte del entregable de uso de IA – Prueba Técnica Grupo SURA.*
