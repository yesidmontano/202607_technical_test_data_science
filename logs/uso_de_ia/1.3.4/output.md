# Registro de Uso de IA — 1.3.4

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba diseñar e implementar las pruebas de hipótesis de confirmación/descarte (P8, P11, P12) identificadas en 1.3.1. La tarea exigía: (1) formular H₀/H₁, (2) elegir pruebas con verificación de supuestos, (3) corregir por comparaciones múltiples, (4) distinguir significancia vs relevancia práctica (crítico en P8/P11, diseñadas como confirmación de nulidad), (5) reutilizar staging y documentar Insights + log.

## Qué se tomó
- Código Python completo de `hip_confirmaciones.py` — generado y ejecutado en una sola corrida limpia.
- Diseño estadístico: Friedman/KW/χ² (P8), KW+Dunn (P11), AD/KS/JB + AIC Gamma vs Lognormal (P12).
- Sección 1.3.4 de `Insights_pruebas_hipotesis.md`, entradas 32–33 en `docs/staging_data.md`, plots `03_P{8,11,12}_*.png`.

## Qué se descartó o requirió corrección manual
- **ANOVA para P8/P11:** descartada (pocas obs/mes en agregados; Shapiro viola normalidad en departamentos).
- **Interacción estacional compleja (STL/Fourier):** descartada — la pregunta de negocio es binaria (“¿invertir en mes?”), no estimar ciclo.
- No se crearon datasets redundantes: se reutilizaron `temporal_mensual`, `estacionalidad_mes`, `empresa_siniestralidad_completa`, `siniestros_tratados`, `bivariado_resumen_departamento`. Nuevos: resumen + GOF P12.

## Hallazgos clave del proceso
1. **P8 – Estacionalidad:** NO rechazar H₀ (Friedman p=0.99; χ² p=0.93). Amplitud índice=3.82 pp, Kendall W=0.037, Cramér V=0.003 → **descartar features de mes**.
2. **P11 – Departamento:** p crudo=0.037 pero **p Holm=0.074 → NO rechazar**; η²=0.0016; Dunn 0/21 pares → **descartar geografía como predictor principal**. Caso didáctico de significancia vs efecto.
3. **P12 – Bondad de ajuste:** rechaza Normal exacta (esperado con n≈37k), pero skew=0.41 y kurtosis≈0 son leves; **AIC prefiere Lognormal** sobre Gamma (ΔAIC≈11 257).

## Lecciones y advertencias relevantes
- En pruebas de *confirmación de nulidad*, el p-valor solo no basta: P11 habría “rechazado” sin Holm y sin η², llevando a una decisión de feature set incorrecta.
- Con n grande, GOF de normalidad (P12) casi siempre rechaza; la decisión de familia debe anclarse en AIC + forma (skew/kurtosis), no en el p-valor del KS/JB.
- 2 562 siniestros sin `costo_total_w` en staging fueron excluidos del GOF — documentado; no implica eliminación del portafolio.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `sections/.../code/03-hip_confirmaciones/hip_confirmaciones.py` | Script ejecutable, semilla fija |
| `sections/.../results/imgs/03_P8_estacionalidad_mensual.png` | Series mensuales + índice estacional |
| `sections/.../results/imgs/03_P11_departamento_frecuencia.png` | Boxplot + medianas por depto |
| `sections/.../results/imgs/03_P12_bondad_ajuste_costo.png` | Hist+Normal, Q-Q, AIC Gamma vs Lognormal |
| `sections/.../results/hip_confirmaciones_resumen.csv` | Tabla resumen 3 tests |
| `sections/.../results/Insights_pruebas_hipotesis.md` | Sección 1.3.4 + cierre del bloque 12 preguntas |
| `data/staging/S01/hip_confirmaciones_resumen.parquet` | Resumen en staging |
| `data/staging/S01/hip_p12_bondad_ajuste_costo.parquet` | Métricas GOF / AIC para S03 |
| `docs/staging_data.md` | Documentación datasets 32–33 |
