# Registro de Uso de IA — 4.2.1

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se requería implementar la estrategia causal 4.1 (DiD escalonado Callaway–Sant’Anna), estimar el ATT del programa sobre siniestralidad con EE adecuados al panel, correr al menos una robustez, persistir staging S04, generar figuras con `sura_brand`, documentar hallazgos y registrar el uso de IA.

## Qué se tomó
- Diseño 4.1: CS / cohortes 2019–2022, outcome `frecuencia_x100`, controles never-treated, amenazas COVID/Ashenfelter/TWFE.
- Panel `temporal_empresa_anio` + `programas_prevencion` + atributos de empresa.
- Paquete `csdid` (ATTgt doubly robust + `aggte` simple/group/dynamic) con bootstrap de influence functions (`biters=500`).
- Patrón de scripts S03 (ROOT `parents[5]`, staging parquet, plots `01_*`, markdown de hallazgos).
- Robusteces: excluir 2020, not-yet-treated, outcome `costo_por_trab`, más chequeo de pre-trends del event-study.

## Qué se descartó o requirió corrección manual
- **TWFE clásico:** descartado por sesgo con adopción escalonada (amenaza 4.1).
- **`catt` en PyPI:** no es Callaway–Sant’Anna (es Cast-to-TV); se usó `csdid`.
- **IDs string en `csdid`:** exige `firm_id` numérico — se derivó de `id_empresa`.
- **ATT de costo/trabajador:** no significativo; no se usa como resultado principal (sí como robustez de canal).

## Hallazgos clave del proceso
1. ATT simple frecuencia = **−0.428** (SE 0.131; IC95 [−0.686, −0.171]) → ~**−11.7%** vs baseline pre de tratadas.
2. Pre-trends OK (0/3 horizontes pre significativos).
3. Robustez COVID y not-yet-treated confirman el signo y orden de magnitud (−0.45 / −0.44).
4. Canal: frecuencia sí; costo por trabajador no identificado con precisión.

## Lecciones y advertencias relevantes
- Con adopción escalonada preferir CS/`aggte` sobre TWFE.
- Bootstrap SE del CS ya incorpora la estructura panel vía IF; no reportar SE homocedásticos OLS.
- Para 4.3 monetizar el ATT de frecuencia, no el de costo.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-estimacion/01-estimacion.py` | Script de estimación |
| `.../results/imgs/01_causal_*.png` | 5 figuras |
| `.../results/estimacion_efecto.md` | Hallazgos para revisión |
| `data/staging/S04/causal_*.parquet` | Datasets #112–119 |
| `docs/staging_data.md` | Documentación staging |
| `logs/uso_de_ia/S04/4.2.1/output.md` | Este log |
| `requirements.txt` | Añadidos `csdid`, `statsmodels` |
