# Diccionario de Datos

> **Referencia:** Este diccionario es la fuente de verdad para los campos de los datasets sintéticos del proyecto.
> Los archivos fuente se encuentran en `data/raw/` y son **inmutables** según las reglas definidas en [`.agents/AGENTS.md`](../.agents/AGENTS.md).

---

## Índice

| Dataset | Descripción corta | ~Filas |
|---|---|---|
| [`empresas.csv`](#1-empresascsv) | Empresas afiliadas a la ARL | 5 000 |
| [`siniestros.csv`](#2-siniestroscsv) | Eventos de siniestro registrados | 40 000 |
| [`programas_prevencion.csv`](#3-programas_prevencioncsv) | Empresas tratadas con programas de prevención | 1 500 |
| [`uso_servicios.csv`](#4-uso_servicioscsv) | Registros de uso de servicios | 100 000 |
| [`catalogo_servicios.csv`](#5-catalogo_servicioscsv) | Catálogo de servicios de prevención | ~40 |
| [`macro_sectorial.csv`](#6-macro_sectorialcsv) | Variables macro por sector y trimestre | ~160 |

---

## 1. `empresas.csv`

**Ruta:** `data/raw/empresas.csv`
**Granularidad:** Una fila por empresa afiliada (~5 000 registros).
**Clave primaria:** `id_empresa`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_empresa` | `texto` | Identificador único de la empresa |
| `ciiu` | `texto` | Código CIIU de la actividad económica (4 dígitos) |
| `sector` | `texto` | Sección económica según clasificación CIIU |
| `clase_riesgo` | `entero` | Clase de riesgo ARL — valores de 1 a 5 |
| `n_trabajadores` | `entero` | Número de trabajadores afiliados |
| `ciudad` | `texto` | Ciudad de ubicación de la empresa |
| `departamento` | `texto` | Departamento de ubicación de la empresa |
| `antiguedad_meses` | `entero` | Meses de afiliación continua a la ARL |
| `prima_anual` | `numérico` | Prima anual devengada en pesos colombianos |
| `fecha_afiliacion` | `fecha` | Fecha de inicio de la afiliación |

> **Nota de uso:** `clase_riesgo` y `sector` son las dimensiones principales de segmentación en el análisis económico (S02) y el reto de negocio (S03).

---

## 2. `siniestros.csv`

**Ruta:** `data/raw/siniestros.csv`
**Granularidad:** Una fila por evento de siniestro (~40 000 registros).
**Clave primaria:** `id_siniestro`
**Clave foránea:** `id_empresa` → `empresas.id_empresa`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_siniestro` | `texto` | Identificador único del siniestro |
| `id_empresa` | `texto` | Empresa a la que pertenece el siniestrado |
| `fecha_ocurrencia` | `fecha` | Fecha del evento |
| `tipo` | `texto` | `AT` = Accidente de Trabajo · `EL` = Enfermedad Laboral |
| `parte_cuerpo` | `texto` | Segmento corporal afectado |
| `dias_incapacidad` | `entero` | Días de incapacidad generados por el evento |
| `costo_asistencial` | `numérico` | Costo médico-asistencial en pesos |
| `costo_prestacion_economica` | `numérico` | Costo de prestaciones económicas en pesos |

> **⚠️ Riesgo de leakage:** Para modelos predictivos, **no usar** datos de siniestros del año de predicción como features. Entrenar hasta T-1, validar en T. Ver reglas en [AGENTS.md](../.agents/AGENTS.md).

---

## 3. `programas_prevencion.csv`

**Ruta:** `data/raw/programas_prevencion.csv`
**Granularidad:** Una fila por empresa tratada con un programa (~1 500 registros).
**Clave foránea:** `id_empresa` → `empresas.id_empresa`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_empresa` | `texto` | Empresa que recibió el programa |
| `programa` | `texto` | Nombre del programa de prevención |
| `fecha_inicio` | `fecha` | Inicio de la intervención (rango 2019–2022) |
| `horas_intervencion` | `numérico` | Horas totales de intervención impartidas |
| `cobertura_trabajadores` | `numérico` | Proporción de trabajadores cubiertos (0–1) |

> **Nota de uso:** Dataset central para la inferencia causal (S04). El grupo de control son las empresas **no presentes** en este archivo.

---

## 4. `uso_servicios.csv`

**Ruta:** `data/raw/uso_servicios.csv`
**Granularidad:** Una fila por evento de uso de servicio (~100 000 registros).
**Claves foráneas:** `id_empresa` → `empresas.id_empresa` · `id_servicio` → `catalogo_servicios.id_servicio`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_empresa` | `texto` | Empresa que usó el servicio |
| `id_servicio` | `texto` | Identificador del servicio (referencia a catálogo) |
| `fecha_uso` | `fecha` | Fecha en que se usó el servicio |
| `canal` | `texto` | `presencial` · `virtual` · `autogestión` |

> **Nota de uso:** Base principal del sistema recomendador (S05). La matriz empresa × servicio se construye a partir de este dataset.

---

## 5. `catalogo_servicios.csv`

**Ruta:** `data/raw/catalogo_servicios.csv`
**Granularidad:** Una fila por servicio disponible (~40 registros).
**Clave primaria:** `id_servicio`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_servicio` | `texto` | Identificador único del servicio |
| `servicio` | `texto` | Nombre descriptivo del servicio |
| `categoria` | `texto` | Categoría temática del servicio |
| `modalidad` | `texto` | `presencial` · `virtual` · `autogestión` |
| `dirigido_a` | `texto` | Clase de riesgo o sector objetivo del servicio |

---

## 6. `macro_sectorial.csv`

**Ruta:** `data/raw/macro_sectorial.csv`
**Granularidad:** Panel sector × trimestre (2018Q1 – 2024Q4, ~160 registros).
**Clave compuesta:** `sector` + `anio` + `trimestre`
**Clave foránea:** `sector` → `empresas.sector`

| Campo | Tipo | Descripción |
|---|---|---|
| `sector` | `texto` | Sección económica (referencia a `empresas.sector`) |
| `anio` | `entero` | Año del periodo |
| `trimestre` | `entero` | Trimestre del periodo (1 a 4) |
| `pib_sectorial_var` | `numérico` | Variación porcentual del valor agregado sectorial |
| `empleo_sectorial` | `numérico` | Índice de empleo sectorial |
| `ipp_sectorial` | `numérico` | Índice de precios al productor del sector |
| `tasa_informalidad` | `numérico` | Tasa de informalidad sectorial (%) |

> **Nota de uso:** Dataset de contexto para la modelación económica (S02) y para el nowcast sectorial. Se cruza con `empresas.csv` por la columna `sector`.

---

## Relaciones entre datasets

```
empresas ──┬── siniestros           (id_empresa)
           ├── programas_prevencion  (id_empresa)
           ├── uso_servicios         (id_empresa)
           └── macro_sectorial       (sector)

uso_servicios ── catalogo_servicios  (id_servicio)
```

---

*Diccionario generado para la Prueba Técnica de Ciencia de Datos — Grupo SURA.*
*Todos los datos son sintéticos. Ver reglas de manejo en [`.agents/AGENTS.md`](../.agents/AGENTS.md).*