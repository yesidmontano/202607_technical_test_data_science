# Registro de Uso de IA — 3.1.1 / 3.1.2

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se necesitaba validar empíricamente los tres supuestos de la pregunta de negocio (independencia frecuencia–severidad, estabilidad del mix, prima vs. costo), persistir staging reutilizable en `data/staging/S03/`, generar figuras con `sura_brand`, documentar hallazgos en `pregunta.md` y actualizar `docs/staging_data.md`.

## Qué se tomó
- Reutilización de staging S01: `empresa_siniestralidad_completa`, `temporal_empresa_anio`, `siniestros_imputados` (trazabilidad).
- Convenciones del repo: rutas relativas con `Path.parents[5]`, semilla 42, espejo CSV en `results/`, plots en `results/imgs/`, paquete `sura_brand`.
- Criterios cuantitativos explícitos: |ρ| Spearman (0.20 / 0.40), JS YoY (0.10), loss ratio > 1.
- Script único `01-supuestos.py` que cubre S1–S3, 7 datasets staging, 8 figuras y veredicto consolidado.

## Qué se descartó o requirió corrección manual
- **Usar solo el conteo de empresas para estabilidad:** descartado — el panel es balanceado con atributos fijos, así que el share de empresas es idéntico año a año y no informa el supuesto. Se ancló la evidencia en shares de **siniestros** y **costo**.
- **Asumir independencia a priori por arquitectura freq+sev de S01:** rechazado empíricamente; S01 justifica NB y severidad AT/EL separadas, pero no independencia freq–sev.
- **Regenerar paneles desde raw:** innecesario; staging S01 ya tipificado e imputado.
- **Chi² sobre mix de empresas YoY:** irrelevante (distribución fija); se usó Jensen–Shannon sobre composición de riesgo.

## Hallazgos clave del proceso
1. **S1 RECHAZADO:** ρ(freq, severidad)=0.35; ρ(freq, costo medio)=0.42 → modelar severidad condicionada.
2. **S2 SOSTENIDO:** JS YoY media (siniestros+costo)=0.052 < 0.10; sector-costo es el más variable (JS≈0.10).
3. **S3 SOSTENIDO con bolsas:** ρ(prima, costo)=0.80; LR mediana=0.39; 16.9% empresas y 25/148 segmentos con LR>1 (sobre todo Micro + clases/sectores de alto riesgo).

## Lecciones y advertencias relevantes
- En paneles de afiliados con atributos estáticos, “estabilidad del portafolio” debe medirse por **composición de siniestros/costo**, no por headcount.
- Loss ratio con prima estática vs. costo multi-año es un proxy histórico; el modelo de S03 debe proyectar costo *forward* y no solo diagnosticar LR pasado.
- Verificar siempre umbrales de interpretación en el veredicto para que S03/S05 reutilicen los mismos criterios.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-supuestos/01-supuestos.py` | Script ejecutable de validación |
| `.../results/imgs/01_S1_freq_vs_severidad.png` | Scatter freq vs sev / costo medio |
| `.../results/imgs/01_S1_corr_por_clase.png` | ρ por clase de riesgo |
| `.../results/imgs/01_S2_mix_clase_costo.png` | Stacked mix costo × clase |
| `.../results/imgs/01_S2_mix_sector_costo.png` | Stacked mix costo × sector |
| `.../results/imgs/01_S2_mix_segmento_costo.png` | Stacked mix costo × tamaño |
| `.../results/imgs/01_S2_js_estabilidad.png` | Barras JS YoY |
| `.../results/imgs/01_S3_prima_vs_costo.png` | Scatter + heatmap LR |
| `.../results/imgs/01_S3_segmentos_loss_ratio.png` | Top segmentos por LR |
| `.../results/supuestos_*.csv` | Espejo de staging / lectura rápida |
| `.../results/pregunta.md` | Hallazgos 3.1.2 para revisión |
| `data/staging/S03/supuestos_freq_sev_empresa.parquet` | Empresas con freq/sev |
| `data/staging/S03/supuestos_freq_sev_correlacion.parquet` | Tabla de correlaciones |
| `data/staging/S03/supuestos_mix_anual.parquet` | Shares anuales |
| `data/staging/S03/supuestos_mix_estabilidad.parquet` | JS por dimensión/métrica |
| `data/staging/S03/supuestos_prima_vs_costo_empresa.parquet` | LR por empresa |
| `data/staging/S03/supuestos_prima_vs_costo_segmento.parquet` | LR por segmento |
| `data/staging/S03/supuestos_veredicto.parquet` | Veredictos S1–S3 |
| `docs/staging_data.md` | Datasets #88–94 |
| `logs/uso_de_ia/S03/3.1.1/output.md` | Este log |
