# Registro de Uso de IA — 2.2.2

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba profundizar 2.2.1 con robustez de estacionariedad (PP), CCF de rezagos/adelantos, cointegración en n=18 con corrección Reinsel–Ahn, sensibilidad del VAR, diagnósticos extendidos y una decisión definitiva de especificación — todo sobre staging existente.

## Qué se tomó
- Insumos: `panel_ciclo_at_trimestral`, `estacionariedad_tests`, `var_irf`, `var_diagnosticos`, `var_modelo_resumen`.
- Script `estacionariedad_robustez.py` con PP Newey–West manual (statsmodels no expone Phillips–Perron; `arch` no está en deps).
- Johansen con factor Reinsel–Ahn `(T − p·k)/T`.
- CCF k=−6…+6; ADL anidado para evaluar lead CEED (rechazado).
- Sensibilidad IRF T12 / T18 / T18+empleo; Portmanteau Q4/Q8 + CUSUM + dummy 2022-I.
- Artefactos: `estacionariedad_robustez.md`, plots `02_*`, §2.2.2 en `relaciones.md`, staging #66–72.

## Qué se descartó o requirió corrección manual
- **Instalar `arch` para PP:** descartado — se implementó PP a mano para no ampliar `requirements.txt`.
- **Añadir lead CEED al VAR:** descartado (ΔAIC=+1.73, p=0.68); no usable en pronóstico.
- **VECM tentativo:** no estimado — EG y Johansen corregido dan r=0 en n=18.
- **Nuevo panel AT+CEED n=18:** innecesario; ya está contenido en `panel_ciclo_at_trimestral`.
- Código intermedio con bloque CCF duplicado: corregido antes de la corrida final.

## Hallazgos clave del proceso
1. PP no cambia veredictos: `pib` y `log_freq_at` siguen I(1) conservador; Δ son I(0).
2. CCF CEED→AT: ρ(0)=−0.59; **pico en k=6 (ρ=+0.58)** — alinea con 6–18 meses de 2.1.4; VAR(1) subestima ese canal.
3. Cointegración n=18: EG p=0.986; Johansen Reinsel–Ahn **r=0** (el r̂=2 de T=12 fue artefacto).
4. IRF h=1 estable: 0.037 (T12) → 0.032 (T18); empleo no absorbe.
5. Portmanteau marginal de T=12 se limpia en T=18 (p≈0.74); CUSUM p=0.85; dummy 2022-I no ayuda.
6. **Spec definitiva:** VAR en diferencias (no VECM / no niveles / no ADL como principal).

## Lecciones y advertencias relevantes
- Potencia de cointegración con T≤18 es ~20–35%; se necesitan ~50–80 trimestres para potencia ≥0.80.
- El lead estructural k=6 debe informarse al nowcast (2.3) vía features de memoria larga, no forzando p=6 en T corto.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/02-estacionariedad/estacionariedad_robustez.py` | Script |
| `.../results/estacionariedad_robustez.md` | Cuadro ADF/KPSS/PP |
| `.../results/imgs/02_*.png` | 5 figuras |
| `.../results/relaciones.md` | §2.2.2 + §5 actualizado |
| `data/staging/S02/estacionariedad_robustez.parquet` | Tests robustos |
| `data/staging/S02/ccf_rezagos*.parquet` | CCF |
| `data/staging/S02/coint_robustez.parquet` | Cointegración |
| `data/staging/S02/var_sensibilidad_irf.parquet` | IRF sensibilidad |
| `data/staging/S02/var_diagnosticos_ext.parquet` | Diagnósticos |
| `data/staging/S02/especificacion_definitiva.parquet` | Veredicto final |
| `docs/staging_data.md` | #66–72 |
| `logs/uso_de_ia/S02/2.2.2/{prompt,output}.md` | Log |
