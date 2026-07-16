# Registro de Uso de IA — 1.4.1

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba cuantificar de forma reproducible los datos faltantes de `empresas.csv` y `siniestros.csv`, con tablas reutilizables en staging, plots en `results/imgs` e Insights para revisión. La tarea es el primer paso del bloque 1.4 (cuantificación); mecanismo e imputación quedan para procesos siguientes.

## Qué se tomó
- Script `cuantificacion_faltantes.py`: conteos por columna/dataset, patrones de co-ocurrencia, tasas estratificadas, 5 plots SURA, CSV en results y 4 parquets en staging.
- Reutilización de `empresas_staging` / `siniestros_staging` solo para contraste (nulos de columnas raw coinciden); la cuantificación se ancla en los CSV raw del requerimiento.
- Sección 1.4.1 de `Insights_datos_faltantes.md` y entradas 34–37 en `docs/staging_data.md`.

## Qué se descartó o requirió corrección manual
- **No se crearon copias del panel completo con flags de missing** (p. ej. `empresas_con_flags_faltantes`): los staging existentes ya preservan los NaN; se documentaron resúmenes agregados reutilizables.
- **No se clasificó MCAR/MAR/MNAR ni se imputó** en este paso: el Insights del bloque 1.4 lo deja explícito como pendiente 1.4.2–1.4.4; aquí solo se cuantificaron señales estratificadas.
- Sentinels tipo string vacío / `"NA"`: se verificaron y no aportan faltantes adicionales más allá de NaN.

## Hallazgos clave del proceso
1. **Completitud celdas alta, filas afectadas materiales:** empresas 97.95% celdas / 15.5% filas con ≥1 nulo; siniestros 98.38% / 13.9%.
2. **Columnas con nulos:** `prima_anual` 11.58%, geo (`ciudad`=`departamento`) 4.48%; en siniestros `costo_asistencial` 6.42%, `dias_incapacidad` 4.15%, `parte_cuerpo` 4.01%.
3. **Patrones:** geo siempre junta (nunca ciudad sin depto); en siniestros dominan faltantes univariados (intersección triple ≈ 7 filas).
4. **Señales estratificadas:** `dias_incapacidad` EL 11.7% vs AT 2.9%; `costo_asistencial` mortal 35.8% vs leve 3.6% → inputs fuertes para hipótesis MAR en 1.4.2.

## Lecciones y advertencias relevantes
- Listwise deletion descartaría ~14–15% de filas y, en siniestros, sesgaría la cola (EL / mortal); no es opción por defecto.
- Los 2 562 NaN de `costo_asistencial` explican los nulos de `costo_total_w` vistos en P12 (1.3.4); no son un artefacto del winsorizado.
- Las tasas estratificadas **no** son aún un veredicto de mecanismo: faltan tests formales (1.4.2).

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `sections/.../code/01-cuantificacion/cuantificacion_faltantes.py` | Script ejecutable, semilla fija |
| `sections/.../results/imgs/01_faltantes_por_columna.png` | % faltantes por columna |
| `sections/.../results/imgs/01_completitud_datasets.png` | KPIs de completitud |
| `sections/.../results/imgs/01_patrones_coocurrencia.png` | Patrones de co-ocurrencia |
| `sections/.../results/imgs/01_faltantes_estratificados.png` | Tasas por tipo/gravedad |
| `sections/.../results/imgs/01_matriz_faltantes_muestra.png` | Matriz visual (muestra) |
| `sections/.../results/faltantes_*.csv` | Tablas espejo de staging |
| `sections/.../results/Insights_datos_faltantes.md` | Hallazgos 1.4.1 |
| `data/staging/S01/faltantes_resumen_datasets.parquet` | KPIs por dataset |
| `data/staging/S01/faltantes_resumen_columnas.parquet` | Una fila por columna |
| `data/staging/S01/faltantes_patrones.parquet` | Co-ocurrencia |
| `data/staging/S01/faltantes_por_estrato.parquet` | Tasas condicionadas |
| `docs/staging_data.md` | Documentación datasets 34–37 |
