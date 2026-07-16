# Registro de Uso de IA — 1.4.4

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba cuantificar el efecto de la imputación 1.4.3 frente a listwise deletion sobre baselines de frecuencia (Binomial Negativa) y severidad/costos (Lognormal), en tres escenarios (a/b/c), con comparación de coeficientes y métricas predictivas, más staging, plots, Insights y log.

## Qué se tomó
- Script `impacto_imputacion.py`: NB + OLS-log, split 80/20, holdout sobre outcomes originalmente observados.
- Reutilización de `empresas_imputadas`, `siniestros_imputados`, `empresa_siniestralidad_completa`, `faltantes_imputacion_estrategia`.
- Staging `faltantes_impacto_{coefs,metricas,resumen}`, 5 plots `04_impacto_*.png`, Insights §1.4.4, docs #46–48.

## Qué se descartó o requirió corrección manual
- **Comparar AIC crudo entre (a) y (b):** engañoso (distinto n); se reporta AIC relativo a (b) y se prioriza holdout + sesgo de coefs.
- **Evaluar holdout incluyendo outcomes imputados:** descartado — sesgaría a favor de (b)/(c). Solo se evalúa sobre R=0 original.
- Bug de plot: etiquetas de `miss_costo` cuando el término solo existe en (c) — corregido con labels dinámicos.

## Hallazgos clave del proceso
1. **Frecuencia:** listwise pierde 15.7% del train; mediana \|sesgo relativo\| de coefs clase ≈ **5.3%**; EE ×**1.57**; holdout RMSE levemente peor que (b)/(c).
2. **Días / costo:** pérdida 4–6%; sesgo de coefs <1%; holdout RMSE_log prácticamente idéntico entre escenarios.
3. **Flags `miss_*`:** no significativos (p>0.22); (c) no mejora de forma material frente a (b).
4. **Recomendación:** usar datos imputados (b) en S03; evitar listwise; flags opcionales solo para auditoría.

## Lecciones y advertencias relevantes
- Bajo MAR, listwise sesga más cuando el faltante está en un **predictor** del modelo de frecuencia (`prima`) que cuando está en el **outcome** de severidad (el holdout sobre observados casi no cambia).
- Un flag de missing no significativo no “limpia” la sospecha MNAR de 1.4.2; solo indica que, en este baseline, no aporta señal lineal adicional.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/04_impacto/impacto_imputacion.py` | Script ejecutable |
| `.../results/imgs/04_impacto_n_aic.png` | N train y AIC relativo |
| `.../results/imgs/04_impacto_holdout_metricas.png` | RMSE holdout |
| `.../results/imgs/04_impacto_coefs_forest.png` | Forest de β |
| `.../results/imgs/04_impacto_sesgo_coefs.png` | Sesgo relativo a vs b |
| `.../results/imgs/04_impacto_resumen.png` | Tabla ejecutiva |
| `.../results/faltantes_impacto_*.csv` | Espejo de staging |
| `.../results/Insights_datos_faltantes.md` | Sección 1.4.4 (cierre bloque) |
| `data/staging/S01/faltantes_impacto_coefs.parquet` | Coefs + sesgo vs b |
| `data/staging/S01/faltantes_impacto_metricas.parquet` | AIC + holdout |
| `data/staging/S01/faltantes_impacto_resumen.parquet` | Veredicto por modelo |
| `docs/staging_data.md` | Datasets 46–48 |
