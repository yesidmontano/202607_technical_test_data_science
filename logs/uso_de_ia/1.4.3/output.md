# Registro de Uso de IA — 1.4.3

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba proponer y aplicar imputación diferenciada según mecanismos 1.4.2 (MCAR → `desconocido`; MAR prima → regresión por tamaño/antigüedad/sector; MAR severidad → condicionada por tipo/gravedad/+prestación), generar datasets imputados, plots, Insights y log.

## Qué se tomó
- Script `estrategia_imputacion.py` con OLS log estocástica (paso MICE univariado) y categoría `desconocido`.
- Reutilización de `faltantes_mecanismos_veredicto`; no se sobrescribieron `empresas_staging` / `siniestros_staging`.
- Datasets nuevos: `empresas_imputadas`, `siniestros_imputados`, `faltantes_imputacion_estrategia`, `_diagnostico`.
- Sección 1.4.3 de Insights + entradas 42–45 en `docs/staging_data.md`.

## Qué se descartó o requirió corrección manual
- **statsmodels MICEData con dummies de sector:** falló por nombres con espacios en patsy; se optó por OLS con `C(sector)` (equivalente al paso MICE cuando solo `prima` está incompleta en el bloque).
- **sklearn / miceforest:** no instalados en `.venv`; no se añadieron dependencias.
- Imputación determinista (solo ŷ): descartada a favor de ŷ+ε para no subestimar varianza.

## Hallazgos clave del proceso
1. Targets imputados al 100%: 0 NaN en ciudad/depto/prima y parte/días/costo_asist.
2. R² log: prima 0.89; días 0.975; costo_asist 0.41 (mayor incertidumbre residual → coherente con sospecha MNAR).
3. Costos imputados con media mayor (7.6 M vs 2.6 M observados): patrón MAR por gravedad preservado.
4. Flags `miss_*` conservados para 1.4.4 (sobre todo `miss_costo_asist`).

## Lecciones y advertencias relevantes
- “MICE” con una sola variable incompleta en el bloque de predictores = regresión condicionada iterada una vez; documentarlo evita sobre-claim.
- No reemplazar staging 1.2: los pipelines previos dependen de NaN explícitos / winsorización sobre originales.
- Para 1.4.4: comparar imputación vs listwise deletion; sensibilidad MNAR en costo asistencial.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/03-estrategia_imputacion/estrategia_imputacion.py` | Script ejecutable |
| `.../results/imgs/03_imputacion_estrategia_resumen.png` | Catálogo de estrategias |
| `.../results/imgs/03_imputacion_prima_antes_despues.png` | Prima obs vs imp |
| `.../results/imgs/03_imputacion_severidad_antes_despues.png` | Días/costo obs vs imp |
| `.../results/imgs/03_imputacion_mcar_categoricas.png` | Nivel `desconocido` |
| `.../results/imgs/03_imputacion_costo_por_gravedad.png` | Costo imp × gravedad |
| `.../results/faltantes_imputacion_*.csv` | Espejo de staging |
| `.../results/Insights_datos_faltantes.md` | Sección 1.4.3 |
| `data/staging/S01/empresas_imputadas.parquet` | Empresas sin NaN + flags |
| `data/staging/S01/siniestros_imputados.parquet` | Siniestros sin NaN + flags |
| `data/staging/S01/faltantes_imputacion_estrategia.parquet` | Catálogo |
| `data/staging/S01/faltantes_imputacion_diagnostico.parquet` | Stats antes/después |
| `docs/staging_data.md` | Datasets 42–45 |
