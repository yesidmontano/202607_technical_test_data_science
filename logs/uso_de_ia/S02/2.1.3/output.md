# Registro de Uso de IA — 2.1.3

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba un EDA preliminar corto de las cuatro fuentes DANE seleccionadas en 2.1.2 (ELIC, CEED, IPOC, EC): limpieza tipográfica, staging reutilizable, visualizaciones con `sura_brand`, hallazgos en `caracterizacion.md` y registro de uso de IA.

## Qué se tomó
- Patrón de scripts S01 (rutas relativas `ROOT = parents[5]`, `sb.apply_sura_style()`, `create_dashboard` / `create_report_figure`, footer + logo, `savefig(dpi=150)`).
- Script único `eda_fuentes.py` que: parsea miles con coma, estandariza columnas, persiste 6 parquet en `data/staging/S02/`, genera 7 plots `03_*.png` y un panel trimestral alineado.
- Documentación de datasets #52–57 en `docs/staging_data.md` y sección 2.1.3 completa en `caracterizacion.md`.

## Qué se descartó o requirió corrección manual
- **Serie mensual completa de ELIC:** el CSV disponible es un snapshot de referencia mayo (n=3); se documentó como limitación, no se inventaron series.
- **Mezclar IPOC y CEED en un solo factor:** descartado tras Spearman ρ≈−0.72 en 2024–2025; se proponen bloques separados (edificación vs obras civiles).
- **Ruta de log en el prompt original (`S01/2.1.3`):** corregida a `logs/uso_de_ia/S02/2.1.3/` según convención vigente del repo.

## Hallazgos clave del proceso
1. **ELIC 2026:** +33.2% anual en m² de mayo (1.92 M); recuperación tras piso 2024 (−30%).
2. **CEED:** pico de área censada ~47 M m² hacia 2023–2024 y contracción a 40.9 M en 2026-I; paralizada estable (~24–27%).
3. **IPOC:** repunte 2024–2025 (máx. 136.7) impulsado por Minas/plantas; diverge de CEED/EC.
4. **EC:** co-mueve con CEED (Spearman **+0.79**); estacionalidad fuerte (amplitud 26.8 pp); mejor rezago (~38 d).
5. **Núcleo indicador líder propuesto:** ELIC + EC → anticipar CEED; IPOC en paralelo para infraestructura.

## Lecciones y advertencias relevantes
- ELIC con n=3 no sirve para estimar rezagos 6–18 meses; para 2.2/2.3 conviene ampliar la serie histórica si el DANE lo permite.
- Los z-scores del panel son solo exploratorios; el indicador compuesto formal debe definir pesos y estacionariedad en el paso siguiente.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/03-EDA_fuentes/eda_fuentes.py` | Script ejecutable |
| `.../results/imgs/03_elic_area_y_variaciones.png` | ELIC área + variaciones % |
| `.../results/imgs/03_ceed_series_areas.png` | CEED series de estados |
| `.../results/imgs/03_ceed_composicion.png` | CEED shares y flujos |
| `.../results/imgs/03_ipoc_total_y_tipologias.png` | IPOC total y tipologías |
| `.../results/imgs/03_ec_serie_mensual.png` | EC serie + YoY |
| `.../results/imgs/03_ec_estacionalidad.png` | EC perfil estacional |
| `.../results/imgs/03_panel_ciclo_resumen.png` | Co-movimiento z-scores |
| `data/staging/S02/elic_staging.parquet` | ELIC limpio |
| `data/staging/S02/ceed_staging.parquet` | CEED limpio |
| `data/staging/S02/ipoc_staging.parquet` | IPOC limpio |
| `data/staging/S02/ec_staging.parquet` | EC limpio |
| `data/staging/S02/fuentes_eda_resumen.parquet` | Resumen 4 fuentes |
| `data/staging/S02/panel_fuentes_trimestral.parquet` | Panel alineado |
| `docs/staging_data.md` | Datasets #52–57 |
| `.../results/caracterizacion.md` | Hallazgos 2.1.3 |
