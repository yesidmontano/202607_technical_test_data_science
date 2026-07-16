# Registro de Uso de IA — 1.4.2

## Modelo utilizado
Grok 4.5

## Por qué se usó
Se necesitaba evaluar formalmente MCAR/MAR/MNAR para cada variable con nulos, con las pruebas pedidas (χ²/Fisher, t/MWU, logit de indicadoras), ancladas a las señales §D de 1.4.1, más staging, plots, Insights y log.

## Qué se tomó
- Script `mecanismos_faltantes.py`: batería univariada + Holm por variable, 9 logits (señal/full), veredictos, 5 plots.
- Reutilización de `faltantes_por_estrato` y `faltantes_patrones` (no se duplicaron resúmenes de cuantificación).
- Sección 1.4.2 de `Insights_datos_faltantes.md` y entradas 38–41 en `docs/staging_data.md`.

## Qué se descartó o requirió corrección manual
- **Little’s MCAR test global:** no se usó como único veredicto (mezcla tipos; el requerimiento pide χ²/t-MWU/logit por variable). La evidencia se construye por R × covariables + LR.
- **sklearn:** no está en el venv; logits con `statsmodels`.
- **Prueba “concluyente” de MNAR:** imposible solo con observados; se documenta *sospecha* en `costo_asistencial` (proxy `costo_prestacion` + gravedad).
- Tests t clásicos: en la práctica dominó **Mann-Whitney** por no normalidad (Shapiro).

## Hallazgos clave del proceso
1. **MCAR no rechazado:** `ciudad`/`departamento` (bloque idéntico), `parte_cuerpo`.
2. **MAR:** `dias_incapacidad` (χ²×tipo p_adj≈10⁻¹⁹⁸, V=0.15); `prima_anual` vía antigüedad/tamaño (no vía clase_riesgo — confirma §D).
3. **MAR + sospecha MNAR:** `costo_asistencial` (χ²×gravedad V=0.22; además MWU vs prestación δ=0.30).
4. Logit full más informativo: `prima_anual` pseudo-R²≈0.14; `costo_asistencial`≈0.07; `dias`≈0.05.

## Lecciones y advertencias relevantes
- “Señal plana” en §D (`prima`×clase) ≠ MCAR: había que mirar otras covariables (antigüedad).
- Rechazar MCAR no prueba MAR exclusivo; MNAR puede coexistir — por eso la etiqueta “MAR con sospecha MNAR” en costo asistencial.
- Para 1.4.3: no listwise deletion en días/costo; imputar condicionando por tipo/gravedad; sensibilidad MNAR en costo.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/02-mecanismos/mecanismos_faltantes.py` | Script ejecutable |
| `.../results/imgs/02_mecanismos_senales_D.png` | Señales D + p Holm / V |
| `.../results/imgs/02_mecanismos_heatmap_pvalores.png` | −log₁₀ p Holm |
| `.../results/imgs/02_mecanismos_logit_OR.png` | Forest OR |
| `.../results/imgs/02_mecanismos_empresas_senales.png` | Prima×clase, ciudad×sector |
| `.../results/imgs/02_mecanismos_veredictos.png` | Tabla de veredictos |
| `.../results/faltantes_mecanismos_*.csv` | Espejo de staging |
| `.../results/Insights_datos_faltantes.md` | Sección 1.4.2 |
| `data/staging/S01/faltantes_mecanismos_tests.parquet` | Tests univariados |
| `data/staging/S01/faltantes_mecanismos_logit.parquet` | Resumen LR |
| `data/staging/S01/faltantes_mecanismos_logit_coefs.parquet` | OR por término |
| `data/staging/S01/faltantes_mecanismos_veredicto.parquet` | Mecanismo por variable |
| `docs/staging_data.md` | Datasets 38–41 |
