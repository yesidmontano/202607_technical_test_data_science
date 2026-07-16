# Descripción de Datasets de Staging

> **Referencia:** Este documento describe los datasets intermedios generados a partir de los datos raw.
> Los archivos staging son **inmutables una vez generados por su script fuente** y deben ser regenerados
> ejecutando el script correspondiente si los datos raw cambian.
> Los datos raw originales se encuentran en `data/raw/` — **no modificar**.

---

## Índice

| Dataset | Sección origen | Ruta | Filas | Columnas |
|---|---|---|---|---|
| [`empresas_staging.parquet`](#1-empresas_stagingparquet) | S01 – 1.2 EDA | `data/staging/S01/` | 5 000 | 13 |
| [`siniestros_staging.parquet`](#2-siniestros_stagingparquet) | S01 – 1.2 EDA | `data/staging/S01/` | 39 894 | 14 |
| [`siniestralidad_empresa.parquet`](#3-siniestralidad_empresaparquet) | S01 – 1.2 EDA | `data/staging/S01/` | 4 625 | 19 |

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

---

## Uso en secciones futuras

| Sección | Dataset requerido | Propósito |
|---|---|---|
| S01 – 1.3 Hipótesis | `siniestralidad_empresa`, `siniestros_staging` | Pruebas de diferencia de medias / proporciones |
| S01 – 1.4 Datos faltantes | `siniestros_staging`, `empresas_staging` | Diagnóstico de nulos y patrones |
| S01 – 1.5 Baseline | `siniestralidad_empresa` | Definición del predictor baseline |
| S02 – Modelación económica | `empresas_staging`, `siniestralidad_empresa` | Caracterización sectorial |
| S03 – Reto de negocio | `siniestralidad_empresa` | Modelado frecuencia-severidad |
| S04 – Inferencia causal | `siniestralidad_empresa` | Grupo tratado / control |
| S05 – Recomendador | `empresas_staging` | Perfil de empresa para recomendación |

---

*Generado por: `S01 – 1.2 EDA | analisis_univariado.py` — Prueba Técnica Grupo SURA.*
