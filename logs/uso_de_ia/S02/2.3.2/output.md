# Registro de Uso de IA — 2.3.2

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba producir el nowcast de frecuencia AT del trimestre en curso (2.3.2) con tres familias definidas en 2.3.1 (RF, BSTS, DFM), respetando rezagos de publicación (ragged-edge), splits train/val/test, incertidumbre, staging S02, plots y log.

## Qué se tomó
- Insumos: `panel_ciclo_at_trimestral`, `panel_fuentes_trimestral`, `ec_staging`, `at_construccion_trimestral`, `siniestros_imputados`, hallazgos 2.1.4 (rezagos pub.) y 2.2.2 (CCF k=6).
- Panel ragged-edge (`nowcast_common.py`): AT mes-1 + EC mes-1; CEED/IPOC/macro en lag-1; memoria CEED MA3/lag-4.
- Scripts separados: `01_random_forest.py`, `02_bsts.py`, `03_dfm.py`, `04_comparativo.py`.
- Métricas MAE/RMSE/MAPE/R²; IC80; nowcast forward 2025-T1.
- `scikit-learn` añadido a `requirements.txt` (RF).
- BSTS: UC local level + spike-and-slab (PIP); AT parcial forzado como regresor.
- DFM: 1 factor + puente OLS con bootstrap.

## Qué se descartó o requirió corrección manual
- **Paquete `bsts`/`pybsts` externo:** descartado; BSTS ligero con statsmodels + Gibbs propio.
- **BSTS con estacionalidad UC period=4 en n=11:** degradaba el ajuste; se simplificó a local level (estacionalidad vía `q_sin`/`q_cos` en features).
- **Primera versión BSTS (regresión solo sobre residual irregular):** MAE train ~0.26–0.29; se reescribió a UC+exog.
- **Forzar VAR(p=6) por CCF:** no viable (2.2.2); se usó lag-4/MA3 como proxy de memoria.
- **Nowcast del calendario 2026:** sin AT post-2024; forward = primer trimestre sin target (2025-T1).

## Hallazgos clave del proceso
1. Panel modelable n=17; splits 11/2/4; forward 2025-T1.
2. **DFM gana en test:** MAE 0.077, RMSE 0.098, MAPE 6.6% (R²=0.45).
3. RF: buen train (MAE 0.052) pero val frágil (n=2) y test MAE 0.132.
4. BSTS: test MAE 0.136; IC más anchos; PIP prioriza CEED/empleo; AT parcial incluido por diseño.
5. Nowcast 2025-T1 (DFM): **1.158** [1.062, 1.285] IC80%.

## Lecciones y advertencias relevantes
- Con T corto el val set no debe usarse para decisiones fuertes de hiperparámetros; el ranking se basa en test.
- El IC del forward asume un proxy de AT parcial; conviene recalibrar cuando exista el mes 1 real de 2025.
- DFM + puente con AT parcial es la especificación recomendada para reporting ARL; RF/BSTS como contraste.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/02-produccion/nowcast_common.py` | Panel ragged-edge + helpers |
| `.../code/02-produccion/01_random_forest.py` | RF |
| `.../code/02-produccion/02_bsts.py` | BSTS |
| `.../code/02-produccion/03_dfm.py` | DFM |
| `.../code/02-produccion/04_comparativo.py` | Comparativo |
| `.../results/nowcast.md` | §2.3.2 |
| `.../results/imgs/02_*.png` | 13 figuras |
| `data/staging/S02/nowcast_*.parquet` | #73–87 |
| `docs/staging_data.md` | Documentación staging |
| `requirements.txt` | + scikit-learn |
| `logs/uso_de_ia/S02/2.3.2/{prompt,output}.md` | Log |
