# Registro de Uso de IA — 3.2.1

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se requería implementar el modelo actuarial frecuencia × severidad para estimar el costo esperado por empresa y por clase de riesgo, persistir staging reutilizable, generar figuras con `sura_brand`, documentar hallazgos y registrar el uso de IA.

## Qué se tomó
- Decisiones S01: NB (no Poisson, no ZI), severidad AT/EL separada, lognormal de costo, predictores `clase`/`sector`/`tamaño`/`lag`.
- Decisión 3.1.2 S1: severidad condicionada (no independencia).
- Panel `temporal_empresa_anio` + `siniestros_tratados` + atributos de `empresa_siniestralidad_completa`.
- Evaluación temporal train 2019–2023 / holdout 2024; proyección próximo año con features 2024.
- Corrección lognormal `E[Y]=exp(μ+σ²/2)` y marginalización de `gravedad` y `tipo` para pricing.

## Qué se descartó o requirió corrección manual
- **Severidad solo con clase×segmento (sin gravedad):** R²_log≈0.04 — insuficiente. Se añadió `C(gravedad)` y se marginalizó `P(g|clase,tipo)` para predicción empresa.
- **`smf.negativebinomial.predict` sin offset:** subestimaba E[N] (~0.03). Se estimó α por MLE y se predijo con GLM NB + offset.
- **Bug `attach_severity` en forward:** `sev_pred` duplicado al re-merge; se corrige dropeando la columna previa.
- **Zero-inflated / Poisson:** descartados por P1/P2 de S01.

## Hallazgos clave del proceso
1. Holdout frecuencia: MAE=0.81, Spearman=0.60; IRR clase 5 vs 1 = 5.0.
2. Severidad AT/EL: R²_log=0.54/0.57; MAE≈1.4–1.5 M COP.
3. Costo pure premium: Spearman=0.57; **portafolio pred/obs=0.985** (17.55 vs 17.82 B).
4. Proyección próximo año: **17.42 B COP**; clases 4–5 = 72% del costo; **169 empresas (3.4%)** con LR pred>1.

## Lecciones y advertencias relevantes
- En pricing, no usar gravedad como feature directa: marginalizar con mix histórico.
- El lag de frecuencia aporta señal (persistencia); no incluir el outcome del mismo año.
- Calibración agregada buena no implica buen ajuste en cola — revisar Top empresas y clase 5 en 3.3.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-modelo/01-modelo.py` | Script del modelo |
| `.../results/imgs/01_modelo_*.png` | 7 figuras |
| `.../results/modelo_*.csv` | Espejo de staging |
| `.../results/model_frecuencia_serveridad.md` | Hallazgos para revisión |
| `data/staging/S03/modelo_*.parquet` | Datasets #95–103 |
| `docs/staging_data.md` | Documentación staging |
| `logs/uso_de_ia/S03/3.2.1/output.md` | Este log |
