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

## Uso en secciones futuras

| Sección | Dataset requerido | Propósito |
|---|---|---|
| S01 – 1.3 Hipótesis | `empresa_siniestralidad_completa`, `bivariado_resumen_*` | Pruebas formales de diferencia / asociación (no incluidas en 1.2.3) |
| S01 – 1.4 Datos faltantes | `siniestros_staging`, `empresas_staging` | Diagnóstico de nulos y patrones |
| S01 – 1.5 Baseline | `empresa_siniestralidad_completa` | Definición del predictor baseline |
| S02 – Modelación económica | `empresa_siniestralidad_completa`, `bivariado_resumen_sector` | Caracterización sectorial |
| S03 – Reto de negocio | `empresa_siniestralidad_completa` | Modelado frecuencia-severidad |
| S04 – Inferencia causal | `empresa_siniestralidad_completa` | Grupo tratado / control |
| S05 – Recomendador | `empresas_staging`, `empresa_siniestralidad_completa` | Perfil de empresa para recomendación |

---

*Actualizado por: `S01 – 1.2 EDA | analisis_univariado.py` + `analisis_bivariado.py` — Prueba Técnica Grupo SURA.*
