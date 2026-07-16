# Registro de Uso de IA — 1.5.1

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba simular el clasificador baseline (Top 10% del año previo → año T), calcular AUC-ROC / Recall / Precisión / F1 en el último año, persistir staging, generar plots y documentar hallazgos + log.

## Qué se tomó
- Reutilización de `temporal_empresa_anio` (target `alta_siniestralidad` ya definido en 1.2); trazabilidad con `temporal_persistencia_yoy` y `hip_p10_retencion_top10`.
- Script `cuantificacion_baseline.py` con métricas en NumPy (sin añadir `scikit-learn` a `requirements.txt`).
- Evaluación principal 2023→2024; contexto histórico en los 6 pares YoY.
- Staging `baseline_{predicciones,metricas,confusion}`, 5 plots `01_baseline_*.png`, `results/Baseline.md`, docs #49–51.

## Qué se descartó o requirió corrección manual
- **Instalar scikit-learn:** descartado — no está en dependencias del proyecto; ROC/AUC/F1 se implementaron con NumPy (`np.trapezoid`).
- **Crear un panel nuevo desde raw:** innecesario; `temporal_empresa_anio` ya tiene el label anual Top 10%.
- **Duplicar `panel_empresa_lag_yoy`:** se creó un corte de evaluación (`baseline_predicciones`) con `y_pred`/`y_score` explícitos, no un segundo panel multi-año.
- Bug menor: `np.trapz` removido en NumPy 2.x → corregido a `np.trapezoid`.

## Hallazgos clave del proceso
1. **Baseline 2023→2024:** AUC-ROC = **0.740**; Recall = Precisión = F1 = **0.532** (TP=266, FP=234, FN=234, TN=4 266).
2. Con prevalencia simétrica (500 predichas / 500 reales), F1 coincide con la tasa de retención del Top 10%.
3. Históricamente F1 oscila **0.47–0.53**; 2024 es el par más alto de la serie.
4. Umbral propuesto para S03: superar de forma estable **F1 > 0.53** y **AUC > 0.74** en validación temporal.

## Lecciones y advertencias relevantes
- El AUC con score binario 0/1 es válido pero tiene pocos puntos en la ROC; modelos futuros con scores continuos serán más comparables en calibración, no solo en ranking duro.
- Accuracy (~0.91) es engañosa con 10% de prevalencia; no usarla como métrica principal.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-cuantificacion_baseline/cuantificacion_baseline.py` | Script ejecutable |
| `.../results/imgs/01_baseline_confusion.png` | Matriz de confusión 2023→2024 |
| `.../results/imgs/01_baseline_roc.png` | Curva ROC |
| `.../results/imgs/01_baseline_metricas.png` | Barras AUC/Recall/Prec/F1 |
| `.../results/imgs/01_baseline_metricas_historicas.png` | Serie YoY |
| `.../results/imgs/01_baseline_resumen.png` | Panel ejecutivo |
| `.../results/baseline_*.csv` | Espejo de staging |
| `.../results/Baseline.md` | Hallazgos para revisión |
| `data/staging/S01/baseline_predicciones.parquet` | Predicciones empresa (2024) |
| `data/staging/S01/baseline_metricas.parquet` | Métricas por par YoY |
| `data/staging/S01/baseline_confusion.parquet` | Celdas TP/FP/FN/TN |
| `docs/staging_data.md` | Datasets 49–51 |
