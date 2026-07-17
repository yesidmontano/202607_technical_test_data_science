# Registro de Uso de IA — 2.2.1

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se requería un pipeline econométrico completo (serie AT trimestral, ADF/KPSS, cointegración, VAR/VECM, IRF/FEVD, diagnósticos, bloque IPOC) alineando DANE staging, macro sintético y siniestros, con visualizaciones `sura_brand` y documentación reproducible.

## Qué se tomó
- Universo Construcción desde `empresas.csv` / `temporal_empresa_anio`; agregación trimestral AT desde `siniestros_imputados` (totales anuales validados vs TE).
- Reutilización de `panel_fuentes_trimestral` (2.1.3) + `macro_sectorial` filtrado a Construcción.
- Spec final: **VAR(1) en diferencias** (endógenas: log AT, log CEED flujo, log EC; exógenas: Δ PIB sectorial, Δ log empleo), tras EG sin cointegración en T=12.
- Bloque auxiliar IPOC: VAR(2) en diferencias (n=18).
- Staging #58–65, 7 plots `01_*.png`, hallazgos en `relaciones.md` §2.2.1.

## Qué se descartó o requirió corrección manual
- **VECM por Johansen r̂=2:** descartado — con T=12 Johansen distorsiona tamaño; EG p=0.995 no soporta cointegración. Primera corrida eligió VECM y la IRF falló (matriz no PD); se corrigió la regla a “EG primario si T&lt;40”.
- **Interpolar `temporal_empresa_anio` a trimestres:** descartado; se usaron fechas de siniestros.
- **p hasta 4 en edificación:** no factible (T_diff=11, k=3+exóg.) → p*=1.
- **Área causada CEED literal:** no está en el CSV; se usó `proceso_nueva_m2` como proxy de flujo.

## Hallazgos clave del proceso
1. Spec: **VAR(1) en diferencias** (no VECM; no OLS/ADL como modelo principal).
2. IRF CEED→AT h=1: **+0.037** (log); se disipa en ~6–8 trimestres.
3. FEVD AT h=4/8: CEED 10–11%, EC ~9–10%, propia ~79–81%.
4. IPOC vs CEED: Spearman **−0.80**; IRF IPOC→AT con signo distinto (pico −0.058 en h=2) → fases opuestas.
5. Portmanteau VAR edif. en el margen (p≈0.04); ARCH y JB OK.

## Lecciones y advertencias relevantes
- n=12 limita potencia e IRF; reportar incertidumbre y sensibilidades con ventana CEED-only (n=18) en pasos siguientes.
- Correlación contemporánea CEED↔AT negativa (−0.62) en 2022–24 no contradice IRF en diferencias (dinámica de corto plazo distinta del comovimiento en niveles).

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-modelamiento/modelamiento_relaciones.py` | Script ejecutable |
| `.../results/imgs/01_*.png` | 7 figuras |
| `.../results/relaciones.md` | Hallazgos §2.2.1 |
| `data/staging/S02/at_construccion_trimestral.parquet` | Serie AT |
| `data/staging/S02/panel_ciclo_at_trimestral.parquet` | Panel alineado |
| `data/staging/S02/estacionariedad_tests.parquet` | ADF/KPSS |
| `data/staging/S02/var_{lag_selection,irf,fevd,diagnosticos,modelo_resumen}.parquet` | Resultados VAR |
| `docs/staging_data.md` | Datasets #58–65 |
| `logs/uso_de_ia/S02/2.2.1/{prompt,output}.md` | Log IA |
