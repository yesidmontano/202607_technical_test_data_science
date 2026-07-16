# Registro de Uso de IA — 1.3.2

## Modelo utilizado
Claude Sonnet 4.6 (Thinking)

## Por qué se usó
Se necesitaba diseñar e implementar las pruebas de hipótesis formales para las 4 preguntas de arquitectura de modelo (P1, P2, P4, P6) identificadas en el registro 1.3.1. La tarea requería: (1) seleccionar la prueba estadística correcta para cada caso, (2) verificar sus supuestos, (3) implementar en Python reproducible, (4) aplicar corrección por comparaciones múltiples, y (5) reportar tamaños de efecto.

## Qué se tomó
- Código Python completo del script `hip_arquitectura_modelo.py` — generado por el modelo y tomado con mínimas correcciones de bugs de API.
- Diseño estadístico completo de las 4 pruebas (selección de tests, supuestos a verificar, métricas de efecto).
- Texto completo del `Insights_pruebas_hipotesis.md` — tomado directamente con leve revisión de formato.

## Correcciones realizadas (bugs de API)
1. **`ax3.boxplot(labels=...)`** → corregido a `tick_labels=...` (API nueva de matplotlib).
2. **Extracción del parámetro α de NB**: `nb_res.params` es `ndarray` (no Series), se corrigió a `nb_res.params[-1]` directamente.
3. Tres ejecuciones totales hasta convergencia: primera con error de boxplot, segunda con error de extracción de α, tercera limpia.

## Qué se descartó o requirió corrección manual
- La primera propuesta de extracción de α usaba `.get()` de diccionario (no aplica a ndarray) — corregido.
- El test de Vuong (ZIP vs NB) fue descartado durante el diseño porque la pregunta correcta es comparar NB vs ZINB, no Poisson vs ZIP.
- La prueba F de dispersión fue descartada porque aplica a distribuciones continuas, no a conteos.

## Hallazgos clave del proceso
1. **P1 – Sobredispersión:** CONFIRMADA masivamente (φ=17.37, LR=34 153). NB es obligatoria en S03.
2. **P2 – Exceso de ceros:** REFUTADO — la NB predice *más* ceros (12.01%) de los observados (7.50%). No se requiere ZIP/ZINB. Resultado contraintuitivo que cambia la arquitectura.
3. **P4 – Sector incremental:** CONFIRMADO — sector aporta señal real más allá de clase (η²=0.44 en K-W; p=0.0036 en LR GLM). 86/105 pares de sectores son distinguibles post-hoc. Pero el efecto incremental sobre clase es pequeño en escala GLM (pseudo-R²=0.0012).
4. **P6 – AT vs EL:** CONFIRMADO — EL tiene mayor severidad (mediana 10 vs 6 días; δ=0.24 mediano). Las distribuciones difieren en forma y localización → modelos separados obligatorios en S03.

## Lecciones y advertencias relevantes
- El resultado de P2 (la NB predice MÁS ceros de los observados) es el hallazgo más contraintuitivo y de mayor impacto: simplifica la arquitectura de S03 descartando la familia ZI.
- La "tensión" de P4 (η² grande en K-W pero pseudo-R² pequeño en GLM) debe comunicarse explícitamente: el sector explica mucho de manera bruta, pero poco *incrementalmente* sobre clase de riesgo. Es importante para calibrar expectativas sobre el peso del sector en el modelo final.
- Los datasets de staging utilizados (`empresa_siniestralidad_completa`, `siniestros_tratados`) son los mismos de S01-1.2 EDA — no se crearon datasets nuevos, en cumplimiento de la regla de reutilización.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `sections/.../code/01-hip_arquitectura_modelo/hip_arquitectura_modelo.py` | Script ejecutable, reproducible con semilla fija |
| `sections/.../results/imgs/P1_sobredispersion.png` | Histograma observado vs Poisson + Q-Q plot |
| `sections/.../results/imgs/P2_exceso_ceros.png` | Distribución observada vs NB + barras de ceros |
| `sections/.../results/imgs/P4_sector_incremental.png` | Boxplot sector + gradiente sector × clase |
| `sections/.../results/imgs/P6_severidad_at_vs_el.png` | Histograma log + CDF + boxplot AT vs EL |
| `sections/.../results/hip_arquitectura_resumen.csv` | Tabla resumen de los 4 tests con p-valores ajustados |
| `sections/.../results/Insights_pruebas_hipotesis.md` | Documento de hallazgos para revisión |
