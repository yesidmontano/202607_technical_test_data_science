# Registro de Uso de IA — 1.3.3

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba diseñar e implementar las pruebas de hipótesis formales para las 5 preguntas de feature set (P3, P5, P7, P9, P10) identificadas en el registro 1.3.1. La tarea requería: (1) formular H₀/H₁, (2) elegir la prueba adecuada verificando supuestos, (3) corregir por comparaciones múltiples, (4) reportar tamaños de efecto vs relevancia práctica, (5) reutilizar staging existente y documentar hallazos en Insights + log.

## Qué se tomó
- Código Python completo del script `hip_features.py` — generado por el modelo y ejecutado sin correcciones de API (una sola corrida limpia).
- Diseño estadístico de las 5 pruebas (K-W+Dunn, LR GLM interacción, Mann-Whitney, Spearman, binomial).
- Texto de la sección 1.3.3 en `Insights_pruebas_hipotesis.md` y entradas nuevas en `docs/staging_data.md`.
- Figuras `02_P{3,5,7,9,10}_*.png` y tablas resumen en results/staging.

## Qué se descartó o requirió corrección manual
- **Interacción saturada clase×sector (dummies 5×15):** descartada porque 36/75 celdas están vacías por diseño ARL. Se usó `clase_riesgo` como ordinal continua + interacciones lineales por sector (14 df).
- **ANOVA / t-tests para P3 y P7:** descartados tras Shapiro/Levene/K-S (normalidad y homocedasticidad violadas).
- No se crearon datasets que ya existían: se reutilizaron `empresa_siniestralidad_completa`, `temporal_empresa_anio` y `temporal_persistencia_yoy`. El único panel nuevo reutilizable es `panel_empresa_lag_yoy` (pares empresa-año para lag/retención).

## Hallazgos clave del proceso
1. **P3 – Clases de riesgo:** RECHAZAR H₀. η²=0.53 (grande); 10/10 pares Dunn significativos; todos los saltos adyacentes tienen Cliff's δ≈0.40 → no colapsar clases.
2. **P5 – Interacción sector×clase:** RECHAZAR H₀ estadísticamente (p=0.007), pero pseudo-R² incremental=0.0012 → relevancia práctica baja; priorizar modelo aditivo.
3. **P7 – Microempresas:** RECHAZAR H₀. δ=0.25 (mediano), mediana 1.72× vs resto; útil como flag de estratificación, no como driver principal (η² tamaño global=0.022).
4. **P9 – Persistencia lag:** RECHAZAR H₀. Spearman ρ=0.44; Pearson r=0.70 (alineado al EDA). `log_lag_n_siniestros` obligatorio. 6/6 años significativos tras Holm.
5. **P10 – Retención Top 10%:** RECHAZAR H₀. Retención 50.1% vs 10% azar → lift 5.01×, Cohen h=0.93 (grande). Argumento central para S03/S04/S05.

## Lecciones y advertencias relevantes
- En P5 (como en P4 de arquitectura) hay tensión significancia vs magnitud: con n=5 000 un LR pequeño puede ser “significativo” sin justificar complejidad de modelado.
- Spearman (0.44) < Pearson (0.70) en P9: la masa de ceros atenúa la correlación por rangos; ambos respaldan el lag, pero el mensaje de negocio debe anclarse en Pearson/lift cuando se comunique al negocio.
- Holm se aplicó a dos niveles: (a) familia de 5 pruebas del feature set, (b) post-hoc/por-año dentro de P3, P7, P9 y P10.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `sections/.../code/02-hip_features/hip_features.py` | Script ejecutable, semilla fija |
| `sections/.../results/imgs/02_P3_clase_riesgo_frecuencia.png` | Boxplot + medianas adyacentes |
| `sections/.../results/imgs/02_P5_interaccion_sector_clase.png` | Heatmap + η² por sector |
| `sections/.../results/imgs/02_P7_microempresas_frecuencia.png` | Micro vs resto + segmentos |
| `sections/.../results/imgs/02_P9_persistencia_conteo.png` | Scatter YoY + ρ por año |
| `sections/.../results/imgs/02_P10_retencion_top10.png` | Retención vs azar + serie YoY |
| `sections/.../results/hip_features_resumen.csv` | Tabla resumen 5 tests |
| `sections/.../results/Insights_pruebas_hipotesis.md` | Sección 1.3.3 añadida |
| `data/staging/S01/panel_empresa_lag_yoy.parquet` | Panel lag reutilizable |
| `data/staging/S01/hip_features_resumen.parquet` | Resumen en staging |
| `data/staging/S01/hip_p3_dunn_clase_adyacente.parquet` | Post-hoc P3 |
| `data/staging/S01/hip_p9_persistencia_spearman.parquet` | Spearman por año |
| `data/staging/S01/hip_p10_retencion_top10.parquet` | Retención binomial por año |
| `docs/staging_data.md` | Documentación datasets 27–31 |
