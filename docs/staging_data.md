# Descripción de Datasets de Staging

> **Referencia:** Este documento describe los datasets intermedios generados a partir de los datos raw.
> Los archivos staging son **inmutables una vez generados por su script fuente** y deben ser regenerados
> ejecutando el script correspondiente si los datos raw cambian.
> Los datos raw originales se encuentran en `data/raw/` — **no modificar**.

---

## Índice

| Dataset | Sección origen | Ruta | Filas | Columnas |
|---|---|---|---|---|
| [`empresas_staging.parquet`](#1-empresas_stagingparquet) | S01 – 1.2 EDA (univariado) | `data/staging/S01/` | 5 000 | 13 |
| [`siniestros_staging.parquet`](#2-siniestros_stagingparquet) | S01 – 1.2 EDA (univariado) | `data/staging/S01/` | 39 894 | 14 |
| [`siniestralidad_empresa.parquet`](#3-siniestralidad_empresaparquet) | S01 – 1.2 EDA (univariado) | `data/staging/S01/` | 4 625 | 19 |
| [`empresa_siniestralidad_completa.parquet`](#4-empresa_siniestralidad_completaparquet) | S01 – 1.2 EDA (bivariado) | `data/staging/S01/` | 5 000 | 28 |
| [`bivariado_resumen_clase_riesgo.parquet`](#5-bivariado_resumen_clase_riesgoparquet) | S01 – 1.2 EDA (bivariado) | `data/staging/S01/` | 5 | 15 |
| [`bivariado_resumen_sector.parquet`](#6-bivariado_resumen_sectorparquet) | S01 – 1.2 EDA (bivariado) | `data/staging/S01/` | 15 | 15 |
| [`bivariado_resumen_segmento.parquet`](#7-bivariado_resumen_segmentoparquet) | S01 – 1.2 EDA (bivariado) | `data/staging/S01/` | 4 | 15 |
| [`bivariado_resumen_departamento.parquet`](#8-bivariado_resumen_departamentoparquet) | S01 – 1.2 EDA (bivariado) | `data/staging/S01/` | 7 | 15 |
| [`bivariado_resumen_ciudad.parquet`](#9-bivariado_resumen_ciudadparquet) | S01 – 1.2 EDA (bivariado) | `data/staging/S01/` | 7 | 15 |
| [`temporal_mensual.parquet`](#10-temporal_mensualparquet) | S01 – 1.2 EDA (temporal) | `data/staging/S01/` | 84 | 15 |
| [`temporal_anual.parquet`](#11-temporal_anualparquet) | S01 – 1.2 EDA (temporal) | `data/staging/S01/` | 7 | 14 |
| [`estacionalidad_mes.parquet`](#12-estacionalidad_mesparquet) | S01 – 1.2 EDA (temporal) | `data/staging/S01/` | 12 | 15 |
| [`temporal_empresa_anio.parquet`](#13-temporal_empresa_anioparquet) | S01 – 1.2 EDA (temporal) | `data/staging/S01/` | 35 000 | 14 |
| [`temporal_persistencia_yoy.parquet`](#14-temporal_persistencia_yoyparquet) | S01 – 1.2 EDA (temporal) | `data/staging/S01/` | 6 | 7 |
| [`outliers_deteccion_resumen.parquet`](#15-outliers_deteccion_resumenparquet) | S01 – 1.2 EDA (outliers) | `data/staging/S01/` | 9 | 25 |
| [`siniestros_con_flags_outliers.parquet`](#16-siniestros_con_flags_outliersparquet) | S01 – 1.2 EDA (outliers) | `data/staging/S01/` | 39 894 | 23 |
| [`empresa_con_flags_outliers.parquet`](#17-empresa_con_flags_outliersparquet) | S01 – 1.2 EDA (outliers) | `data/staging/S01/` | 5 000 | 26 |
| [`siniestros_tratados.parquet`](#18-siniestros_tratadosparquet) | S01 – 1.2 EDA (outliers) | `data/staging/S01/` | 39 894 | 22 |
| [`empresa_siniestralidad_tratada.parquet`](#19-empresa_siniestralidad_tratadaparquet) | S01 – 1.2 EDA (outliers) | `data/staging/S01/` | 5 000 | 37 |
| [`outliers_tratamiento_impacto.parquet`](#20-outliers_tratamiento_impactoparquet) | S01 – 1.2 EDA (outliers) | `data/staging/S01/` | 9 | 17 |

---

## 1. `empresas_staging.parquet`

**Ruta:** `data/staging/S01/empresas_staging.parquet`
**Script origen:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/01-analisis_univariado/analisis_univariado.py`
**Granularidad:** Una fila por empresa afiliada (5 000 registros).
**Base:** `data/raw/empresas.csv` con columnas adicionales derivadas.

| Campo | Tipo | Descripción | ¿Nuevo? |
|---|---|---|---|
| `id_empresa` | `texto` | Identificador único de la empresa | Raw |
| `ciiu` | `texto` | Código CIIU de la actividad económica | Raw |
| `sector` | `category` | Sección económica CIIU (cast a categoría) | Raw → cast |
| `clase_riesgo` | `category` | Clase de riesgo ARL 1–5 (cast a categoría) | Raw → cast |
| `n_trabajadores` | `entero` | Número de trabajadores afiliados | Raw |
| `ciudad` | `texto` | Ciudad de la empresa | Raw |
| `departamento` | `texto` | Departamento de la empresa | Raw |
| `antiguedad_meses` | `entero` | Meses de afiliación continua | Raw |
| `prima_anual` | `numérico` | Prima anual devengada (COP) | Raw |
| `fecha_afiliacion` | `fecha` | Fecha de inicio de afiliación | Raw |
| `anio_afiliacion` | `entero` | Año extraído de `fecha_afiliacion` | **Derivada** |
| `log_n_trabajadores` | `numérico` | `log(1 + n_trabajadores)` | **Derivada** |
| `log_prima_anual` | `numérico` | `log(1 + prima_anual)` | **Derivada** |

> **Notas de uso:** Las columnas `log_*` se construyen para estabilizar distribuciones altamente sesgadas.

---

## 2. `siniestros_staging.parquet`

**Ruta:** `data/staging/S01/siniestros_staging.parquet`
**Script origen:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/01-analisis_univariado/analisis_univariado.py`
**Granularidad:** Una fila por evento de siniestro (39 894 registros).
**Base:** `data/raw/siniestros.csv` con columnas adicionales derivadas.

| Campo | Tipo | Descripción | ¿Nuevo? |
|---|---|---|---|
| `id_siniestro` | `texto` | Identificador único del siniestro | Raw |
| `id_empresa` | `texto` | Empresa a la que pertenece el siniestrado | Raw |
| `fecha_ocurrencia` | `fecha` | Fecha del evento | Raw |
| `tipo` | `category` | `AT` Accidente de Trabajo · `EL` Enfermedad Laboral | Raw → cast |
| `parte_cuerpo` | `texto` | Segmento corporal afectado | Raw |
| `dias_incapacidad` | `entero` | Días de incapacidad generados | Raw |
| `costo_asistencial` | `numérico` | Costo médico-asistencial (COP) | Raw |
| `costo_prestacion_economica` | `numérico` | Costo de prestaciones económicas (COP) | Raw |
| `gravedad` | `category` | Nivel de gravedad del siniestro | Raw → cast |
| `anio` | `entero` | Año de ocurrencia | **Derivada** |
| `mes` | `entero` | Mes de ocurrencia (1–12) | **Derivada** |
| `costo_total` | `numérico` | `costo_asistencial + costo_prestacion_economica` | **Derivada** |
| `log_costo_total` | `numérico` | `log(1 + costo_total)` | **Derivada** |
| `log_dias_incapacidad` | `numérico` | `log(1 + dias_incapacidad)` | **Derivada** |

> **Riesgo de leakage:** Para modelos predictivos, **no usar** datos de siniestros del año de predicción como features.

---

## 3. `siniestralidad_empresa.parquet`

**Ruta:** `data/staging/S01/siniestralidad_empresa.parquet`
**Script origen:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/01-analisis_univariado/analisis_univariado.py`
**Granularidad:** Una fila por empresa con siniestros (4 625 registros).
**Base:** Agregación de `siniestros_staging` + join con `empresas_staging`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_empresa` | `texto` | Identificador único de la empresa |
| `n_siniestros` | `entero` | Total de siniestros registrados en el periodo |
| `total_dias_incapacidad` | `entero` | Suma total de días de incapacidad |
| `costo_total_empresa` | `numérico` | Suma total de costos (asistencial + prestaciones) en COP |
| `costo_asistencial_total` | `numérico` | Suma total de costos asistenciales en COP |
| `costo_prestacion_total` | `numérico` | Suma total de prestaciones económicas en COP |
| `costo_medio_siniestro` | `numérico` | Costo promedio por siniestro individual |
| `severidad_media` | `numérico` | Promedio de días de incapacidad por siniestro |
| `anio_primero` | `entero` | Año del primer siniestro registrado |
| `anio_ultimo` | `entero` | Año del último siniestro registrado |
| `n_trabajadores` | `entero` | Trabajadores afiliados (de `empresas_staging`) |
| `clase_riesgo` | `category` | Clase de riesgo ARL (de `empresas_staging`) |
| `sector` | `category` | Sector económico (de `empresas_staging`) |
| `departamento` | `texto` | Departamento (de `empresas_staging`) |
| `ciudad` | `texto` | Ciudad (de `empresas_staging`) |
| `prima_anual` | `numérico` | Prima anual en COP (de `empresas_staging`) |
| `antiguedad_meses` | `entero` | Meses de afiliación (de `empresas_staging`) |
| `frecuencia_x100` | `numérico` | Siniestros por cada 100 trabajadores |
| `log_frecuencia_x100` | `numérico` | `log(1 + frecuencia_x100)` |

> **Nota de uso:** Este es el dataset de análisis principal para S03 (modelado) y S04 (causalidad).
> Las empresas sin siniestros (~375) no aparecen; tratar como `n_siniestros = 0` en modelos de clasificación.
> Preferir [`empresa_siniestralidad_completa.parquet`](#4-empresa_siniestralidad_completaparquet) cuando se necesite el universo completo de 5 000 empresas.

---

## 4. `empresa_siniestralidad_completa.parquet`

**Ruta:** `data/staging/S01/empresa_siniestralidad_completa.parquet`
**Script origen:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/02-analisis_bivariado/analisis_bivariado.py`
**Granularidad:** Una fila por empresa afiliada (5 000 registros) — incluye empresas sin siniestros.
**Base:** Left join de `empresas_staging` + métricas de `siniestralidad_empresa`, con ceros imputados.

| Campo | Tipo | Descripción | ¿Nuevo? |
|---|---|---|---|
| *(todas las de `empresas_staging`)* | — | Atributos de la empresa | Heredadas |
| `n_siniestros` | `entero` | Total de siniestros (0 si sin eventos) | Completada |
| `total_dias_incapacidad` | `entero` | Suma de días de incapacidad (0 si sin eventos) | Completada |
| `costo_total_empresa` | `numérico` | Costo acumulado COP (0 si sin eventos) | Completada |
| `costo_asistencial_total` | `numérico` | Costo asistencial acumulado | Completada |
| `costo_prestacion_total` | `numérico` | Prestaciones económicas acumuladas | Completada |
| `costo_medio_siniestro` | `numérico` | Costo medio por siniestro (`NaN` si n_siniestros=0) | De siniestralidad |
| `severidad_media` | `numérico` | Días medios de incapacidad (`NaN` si n_siniestros=0) | De siniestralidad |
| `frecuencia_x100` | `numérico` | Siniestros por 100 trabajadores (0 si sin eventos) | Completada |
| `log_frecuencia_x100` | `numérico` | `log(1 + frecuencia_x100)` | Recalculada |
| `anio_primero` / `anio_ultimo` | `entero` | Rango temporal de siniestros (`NaN` si sin eventos) | De siniestralidad |
| `log_costo_total_empresa` | `numérico` | `log(1 + costo_total_empresa)` | **Derivada** |
| `log_n_siniestros` | `numérico` | `log(1 + n_siniestros)` | **Derivada** |
| `tiene_siniestro` | `entero` | Flag binario: 1 si `n_siniestros > 0` | **Derivada** |
| `segmento` | `category` | Micro / Pequeña / Mediana / Grande según `n_trabajadores` | **Derivada** |

> **Uso recomendado:** panel maestro para modelado, hipótesis y baseline. Evita el sesgo de selección de `siniestralidad_empresa` (solo empresas con siniestros).

---

## 5. `bivariado_resumen_clase_riesgo.parquet`

**Ruta:** `data/staging/S01/bivariado_resumen_clase_riesgo.parquet`
**Script origen:** `02-analisis_bivariado/analisis_bivariado.py`
**Granularidad:** Una fila por clase de riesgo ARL (1–5).

Campos agregados (comunes a todos los resúmenes bivariados 5–9):

| Campo | Descripción |
|---|---|
| `<dimensión>` | Variable de estratificación (`clase_riesgo`, `sector`, `segmento`, `departamento` o `ciudad`) |
| `n_empresas` | Conteo de empresas en el grupo |
| `pct_con_siniestro` | % de empresas con al menos un siniestro |
| `n_siniestros_mediana` / `_media` | Conteo de siniestros |
| `frecuencia_x100_mediana` / `_media` | Tasa relativa |
| `costo_total_mediana` / `_media` / `_suma` | Costo acumulado |
| `severidad_mediana` / `_media` | Días de incapacidad medios (sobre empresas con siniestros) |
| `n_trabajadores_mediana` | Tamaño mediano |
| `prima_anual_mediana` | Prima mediana |
| `share_costo_pct` | Participación del grupo en el costo total del portafolio (%) |

---

## 6. `bivariado_resumen_sector.parquet`

**Ruta:** `data/staging/S01/bivariado_resumen_sector.parquet`
**Granularidad:** Una fila por sector económico (15 sectores).
**Esquema:** idéntico al resumen de clase de riesgo (sección 5), con dimensión `sector`.

---

## 7. `bivariado_resumen_segmento.parquet`

**Ruta:** `data/staging/S01/bivariado_resumen_segmento.parquet`
**Granularidad:** Una fila por segmento de tamaño (Micro ≤10 / Pequeña 11–50 / Mediana 51–200 / Grande >200).
**Esquema:** idéntico al resumen de clase de riesgo (sección 5), con dimensión `segmento`.

---

## 8. `bivariado_resumen_departamento.parquet`

**Ruta:** `data/staging/S01/bivariado_resumen_departamento.parquet`
**Granularidad:** Una fila por departamento (7 departamentos).
**Esquema:** idéntico al resumen de clase de riesgo (sección 5), con dimensión `departamento`.

---

## 9. `bivariado_resumen_ciudad.parquet`

**Ruta:** `data/staging/S01/bivariado_resumen_ciudad.parquet`
**Granularidad:** Una fila por ciudad (7 ciudades; mapeo 1:1 con departamento en este dataset sintético).
**Esquema:** idéntico al resumen de clase de riesgo (sección 5), con dimensión `ciudad`.

---

## 10. `temporal_mensual.parquet`

**Ruta:** `data/staging/S01/temporal_mensual.parquet`
**Script origen:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/03-analisis_temporal/analisis_temporal.py`
**Granularidad:** Una fila por año-mes (84 registros = 7 años × 12 meses).
**Base:** Agregación de `siniestros_staging` por `anio` y `mes`.

| Campo | Tipo | Descripción |
|---|---|---|
| `anio` / `mes` | `entero` | Componentes de calendario |
| `anio_mes` | `texto` | Clave `YYYY-MM` |
| `n_siniestros` | `entero` | Conteo de siniestros en el mes |
| `n_empresas` | `entero` | Empresas distintas con al menos un siniestro |
| `costo_total` / `costo_medio` | `numérico` | Costo acumulado y medio (COP) |
| `severidad_media` / `severidad_mediana` | `numérico` | Días de incapacidad |
| `n_at` / `n_el` / `pct_at` / `pct_el` | `entero` / `numérico` | Mix AT vs EL |
| `ma3_n_siniestros` / `ma3_costo_total` | `numérico` | Media móvil de 3 meses |

> **Uso:** series temporales de portafolio, dashboards y diagnóstico de estacionalidad.

---

## 11. `temporal_anual.parquet`

**Ruta:** `data/staging/S01/temporal_anual.parquet`
**Script origen:** `03-analisis_temporal/analisis_temporal.py`
**Granularidad:** Una fila por año calendario (2018–2024).

| Campo | Tipo | Descripción |
|---|---|---|
| `anio` | `entero` | Año de ocurrencia |
| `n_siniestros` / `n_empresas` | `entero` | Volumen y cobertura |
| `costo_total` / `costo_medio` / `costo_por_siniestro` | `numérico` | Métricas de costo (COP) |
| `severidad_media` / `severidad_mediana` | `numérico` | Días de incapacidad |
| `n_at` / `n_el` / `pct_at` / `pct_el` | `entero` / `numérico` | Mix AT vs EL |
| `yoy_n_siniestros_pct` / `yoy_costo_total_pct` | `numérico` | Variación interanual (%) |

> **Uso:** tendencias de portafolio y definición de ventanas train/test temporales (T-1 → T).

---

## 12. `estacionalidad_mes.parquet`

**Ruta:** `data/staging/S01/estacionalidad_mes.parquet`
**Script origen:** `03-analisis_temporal/analisis_temporal.py`
**Granularidad:** Una fila por mes calendario (1–12), promediando años 2018–2024.

| Campo | Tipo | Descripción |
|---|---|---|
| `mes` / `mes_label` | `entero` / `texto` | Mes numérico y etiqueta (Ene…Dic) |
| `n_siniestros_media` / `_std` / `_min` / `_max` | `numérico` | Distribución del volumen entre años |
| `costo_total_media` / `_std` | `numérico` | Costo mensual promedio |
| `severidad_media` / `_std` | `numérico` | Severidad mensual promedio |
| `indice_estacional_n` | `numérico` | Media del mes / media global de volumen |
| `indice_estacional_costo` / `_sev` | `numérico` | Índices análogos para costo y severidad |
| `cv_n` | `numérico` | Coeficiente de variación interanual del mes |
| `n_anios` | `entero` | Años con observación (7) |

> **Uso:** cuantificar amplitud estacional; en este portafolio el índice de volumen oscila ~±2% (estacionalidad débil).

---

## 13. `temporal_empresa_anio.parquet`

**Ruta:** `data/staging/S01/temporal_empresa_anio.parquet`
**Script origen:** `03-analisis_temporal/analisis_temporal.py`
**Granularidad:** Una fila por empresa × año (5 000 × 7 = 35 000 registros), con ceros imputados.
**Base:** Producto cartesiano `empresas_staging` × años observados + agregados de siniestros.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_empresa` / `anio` | `texto` / `entero` | Clave del panel |
| `n_siniestros` / `costo_total` | `entero` / `numérico` | Agregados del año (0 si sin eventos) |
| `severidad_media` | `numérico` | Días medios (`NaN` si n_siniestros=0) |
| `n_at` / `n_el` | `entero` | Conteos por tipo |
| `n_trabajadores` / `clase_riesgo` / `sector` | — | Atributos de empresa (de staging) |
| `frecuencia_x100` | `numérico` | Siniestros / 100 trabajadores en el año |
| `tiene_siniestro` | `entero` | Flag 1 si hubo al menos un siniestro |
| `alta_siniestralidad` | `entero` | Target operativo: 1 si la empresa está en el **Top 10%** de `n_siniestros` del año (rank descendente; ~500 positivas / año) |
| `umbral_n_siniestros_top10` | `entero` | Mínimo `n_siniestros` observado entre las positivas del año (corte inclusivo del Top 10%) |

> **Uso recomendado:** panel para validación temporal (entrenar hasta T-1, validar en T), features de lag y target anual.
> **Definición alineada a CRISP-DM:** Top 10% por conteo de siniestros dentro de cada año (no “por encima de la media”).
> **Riesgo de leakage:** no usar `n_siniestros` / costos del año T como features para predecir el target del mismo año T.

---

## 14. `temporal_persistencia_yoy.parquet`

**Ruta:** `data/staging/S01/temporal_persistencia_yoy.parquet`
**Script origen:** `03-analisis_temporal/analisis_temporal.py`
**Granularidad:** Una fila por par de años consecutivos (6 pares: 2018→2019 … 2023→2024).

| Campo | Tipo | Descripción |
|---|---|---|
| `anio_t` / `anio_t1` | `entero` | Par de años consecutivos |
| `corr_n_siniestros` | `numérico` | Correlación Pearson del conteo empresa entre t y t+1 |
| `corr_frecuencia_x100` | `numérico` | Correlación Pearson de la tasa relativa entre t y t+1 |
| `n_alta_t` | `entero` | Empresas en Top 10% en el año t |
| `n_alta_retenidas` | `entero` | De esas, cuántas siguen en Top 10% en t+1 |
| `tasa_retencion_top10` | `numérico` | `n_alta_retenidas / n_alta_t` |

> **Uso:** evidencia de que el conteo absoluto es un predictor lag fuerte (~0.70); la tasa relativa persiste menos (~0.18). La retención del label Top 10% cuantifica estabilidad del target binario.

---

## 15. `outliers_deteccion_resumen.parquet`

**Ruta:** `data/staging/S01/outliers_deteccion_resumen.parquet`
**Script origen:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/04-analisis_outliers/analisis_outliers.py`
**Granularidad:** Una fila por variable analizada (9 variables: 4 de siniestro + 5 de empresa).
**Base:** Estadísticos de detección IQR (1.5×), MAD (z-modificado ≥ 3.5) y percentiles P1–P99.

| Campo | Tipo | Descripción |
|---|---|---|
| `nivel` | `texto` | `siniestro` o `empresa` |
| `variable` / `etiqueta` | `texto` | Nombre técnico y etiqueta en español |
| `n_valid` | `entero` | Observaciones no nulas |
| `mean` / `median` / `std` / `min` / `max` | `numérico` | Estadísticos descriptivos |
| `p1` / `p99` / `q1` / `q3` / `iqr` | `numérico` | Percentiles y rango intercuartílico |
| `iqr_lo` / `iqr_hi` | `numérico` | Cercas IQR (Q1 − 1.5·IQR, Q3 + 1.5·IQR) |
| `mad` / `mad_lo` / `mad_hi` | `numérico` | Desviación absoluta mediana y cercas MAD |
| `n_iqr` / `pct_iqr` | `entero` / `numérico` | Conteo y % fuera de IQR |
| `n_mad` / `pct_mad` | `entero` / `numérico` | Conteo y % con \|z-mod\| ≥ 3.5 |
| `n_pct` / `pct_pct` | `entero` / `numérico` | Conteo y % fuera de [P1, P99] |

> **Nota:** En variables de cola pesada, IQR/MAD marcan ~10–15% como atípicos; eso refleja leptocurtosis, no necesariamente error de dato. P1–P99 es el criterio operativo de tratamiento (~1–2% clipado).

---

## 16. `siniestros_con_flags_outliers.parquet`

**Ruta:** `data/staging/S01/siniestros_con_flags_outliers.parquet`
**Script origen:** `04-analisis_outliers/analisis_outliers.py`
**Granularidad:** Una fila por siniestro (39 894).
**Base:** `siniestros_staging` + flags binarios de outlier.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_siniestro` / `id_empresa` / `tipo` / `gravedad` / `anio` | — | Identificadores y atributos |
| `costo_total` / `dias_incapacidad` / `costo_asistencial` / `costo_prestacion_economica` | `numérico` | Valores originales |
| `out_iqr_<var>` / `out_mad_<var>` / `out_pct_<var>` | `entero` | 1 si la observación es outlier por ese método |
| `out_iqr_any_key` | `entero` | 1 si IQR-outlier en costo total **o** días |
| `out_pct_any_key` | `entero` | 1 si fuera de P1–P99 en costo total **o** días |

> **Uso:** filtrar / estratificar análisis de cola; **no** eliminar filas del portafolio (eventos reales).

---

## 17. `empresa_con_flags_outliers.parquet`

**Ruta:** `data/staging/S01/empresa_con_flags_outliers.parquet`
**Script origen:** `04-analisis_outliers/analisis_outliers.py`
**Granularidad:** Una fila por empresa (5 000).
**Base:** `empresa_siniestralidad_completa` + flags.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_empresa` / `clase_riesgo` / `sector` / `segmento` | — | Atributos de segmento |
| `n_siniestros` / `costo_total_empresa` / `frecuencia_x100` / `n_trabajadores` / `prima_anual` | `numérico` | Valores originales |
| `out_iqr_<var>` / `out_mad_<var>` / `out_pct_<var>` | `entero` | Flags por método y variable |
| `out_iqr_any_key` / `out_pct_any_key` | `entero` | Flags compuestos (conteo o costo acumulado) |

---

## 18. `siniestros_tratados.parquet`

**Ruta:** `data/staging/S01/siniestros_tratados.parquet`
**Script origen:** `04-analisis_outliers/analisis_outliers.py`
**Granularidad:** Una fila por siniestro (mismas 39 894 filas; **ninguna eliminada**).
**Base:** `siniestros_staging` + columnas winsorizadas P1–P99 (`*_w`) y sus logs.

| Campo | Tipo | Descripción |
|---|---|---|
| *(columnas de `siniestros_staging`)* | — | Valores originales intactos |
| `costo_total_w` / `dias_incapacidad_w` / `costo_asistencial_w` / `costo_prestacion_economica_w` | `numérico` | Winsorización P1–P99 |
| `log_*_w` | `numérico` | `log(1 + valor_w)` para modelado |

> **Decisión de tratamiento:** winsorizar para features de modelado; conservar originales para resultado técnico / cola catastrófica.
> **Riesgo de leakage:** igual que `siniestros_staging` — no usar siniestros del año T como features del target T.

---

## 19. `empresa_siniestralidad_tratada.parquet`

**Ruta:** `data/staging/S01/empresa_siniestralidad_tratada.parquet`
**Script origen:** `04-analisis_outliers/analisis_outliers.py`
**Granularidad:** Una fila por empresa (5 000; panel completo con ceros).
**Base:** `empresa_siniestralidad_completa` + columnas `*_w` / `log_*_w`.

| Campo | Tipo | Descripción |
|---|---|---|
| *(columnas de `empresa_siniestralidad_completa`)* | — | Originales intactos |
| `n_siniestros_w` / `costo_total_empresa_w` / `frecuencia_x100_w` / `n_trabajadores_w` / `prima_anual_w` | `numérico` | Winsorización P1–P99 |
| `log_n_siniestros_w` / `log_costo_total_empresa_w` / `log_n_trabajadores_w` / `log_prima_anual_w` | `numérico` | Logs de variables winsorizadas |

> **Uso recomendado en S03:** preferir `*_w` / `log_*_w` como features numéricas sensibles a cola; mantener originales si el objetivo es estimar carga catastrófica.

---

## 20. `outliers_tratamiento_impacto.parquet`

**Ruta:** `data/staging/S01/outliers_tratamiento_impacto.parquet`
**Script origen:** `04-analisis_outliers/analisis_outliers.py`
**Granularidad:** Una fila por variable (9).

| Campo | Tipo | Descripción |
|---|---|---|
| `nivel` / `variable` / `etiqueta` | `texto` | Identificación |
| `n` | `entero` | Observaciones válidas |
| `mean_antes` / `mean_despues` | `numérico` | Media pre/post winsorización |
| `median_antes` / `median_despues` | `numérico` | Mediana (casi invariante) |
| `std_antes` / `std_despues` | `numérico` | Desviación estándar |
| `max_antes` / `max_despues` | `numérico` | Máximo (contracción de cola) |
| `p99_antes` / `p99_despues` | `numérico` | Percentil 99 |
| `skew_antes` / `skew_despues` | `numérico` | Asimetría |
| `pct_clipados` | `numérico` | % de filas cuyo valor cambió al winsorizar |

---

## Uso en secciones futuras

| Sección | Dataset requerido | Propósito |
|---|---|---|
| S01 – 1.3 Hipótesis | `empresa_siniestralidad_completa`, `bivariado_resumen_*` | Pruebas formales de diferencia / asociación (no incluidas en 1.2.3) |
| S01 – 1.4 Datos faltantes | `siniestros_staging`, `empresas_staging` | Diagnóstico de nulos y patrones |
| S01 – 1.5 Baseline | `empresa_siniestralidad_completa`, `temporal_empresa_anio` | Definición del predictor baseline y target anual |
| S02 – Modelación económica | `empresa_siniestralidad_completa`, `bivariado_resumen_sector`, `temporal_anual` | Caracterización sectorial y tendencias |
| S03 – Reto de negocio | `empresa_siniestralidad_tratada`, `siniestros_tratados`, `temporal_empresa_anio` | Features winsorizadas + CV temporal; cola original para severidad catastrófica |
| S04 – Inferencia causal | `empresa_siniestralidad_completa` / `_tratada` | Grupo tratado / control; evaluar sensibilidad a winsorización |
| S05 – Recomendador | `empresas_staging`, `empresa_siniestralidad_completa` | Perfil de empresa para recomendación |

---

*Actualizado por: `S01 – 1.2 EDA | analisis_univariado.py` + `analisis_bivariado.py` + `analisis_temporal.py` + `analisis_outliers.py` — Prueba Técnica Grupo SURA.*
