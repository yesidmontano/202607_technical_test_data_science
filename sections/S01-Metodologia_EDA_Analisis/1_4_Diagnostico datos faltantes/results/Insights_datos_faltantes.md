### **Requerimiento**
Diagnosticar los datos faltantes de empresas.csv y siniestros.csv: cuantifícarlos, plantear una hipótesis sobre su mecanismo entre MCAR, MAR o MNAR, proponer y aplicar una estrategia de imputación, y evaluar su efecto sobre el modelado frente a la alternativa de descartar registros.

---

## 1.4.1 – Cuantificación de datos faltantes (resultados preliminares)

> Generado a partir de `01-cuantificacion/cuantificacion_faltantes.py` · fuentes: `data/raw/empresas.csv` (5 000 × 10) y `data/raw/siniestros.csv` (39 894 × 9) · nulos de columnas raw contrastados con `empresas_staging` / `siniestros_staging` (coinciden).

---

### A. Completitud global

![Completitud global y filas afectadas](imgs/01_completitud_datasets.png)

| Dataset | Filas | Columnas | Celdas faltantes | Completitud celdas | Filas con ≥1 nulo |
|---|---:|---:|---:|---:|---:|
| empresas | 5 000 | 10 | 1 027 (2.05%) | **97.95%** | 775 (**15.50%**) |
| siniestros | 39 894 | 9 | 5 820 (1.62%) | **98.38%** | 5 544 (**13.90%**) |

- A nivel **celda** ambos datasets están muy completos (>97%).
- A nivel **fila**, ~1 de cada 6–7 registros tiene al menos un faltante → un listwise deletion ingenuo descartaría **15.5%** de empresas y **13.9%** de siniestros.
- **Implicación:** la cuantificación ya descarta “completeness total” como supuesto; el modelado debe tratar nulos de forma explícita (imputación o modelos que los toleren), no ignorarlos.

---

### B. Faltantes por columna

![% faltantes por columna](imgs/01_faltantes_por_columna.png)

**empresas** — 3 de 10 columnas con nulos:

| Columna | N faltantes | % filas |
|---|---:|---:|
| `prima_anual` | 579 | **11.58%** |
| `ciudad` | 224 | 4.48% |
| `departamento` | 224 | 4.48% |

Columnas 100% completas: `id_empresa`, `ciiu`, `sector`, `clase_riesgo`, `n_trabajadores`, `antiguedad_meses`, `fecha_afiliacion`.

**siniestros** — 3 de 9 columnas con nulos:

| Columna | N faltantes | % filas |
|---|---:|---:|
| `costo_asistencial` | 2 562 | **6.42%** |
| `dias_incapacidad` | 1 657 | 4.15% |
| `parte_cuerpo` | 1 601 | 4.01% |

Columnas 100% completas: `id_siniestro`, `id_empresa`, `fecha_ocurrencia`, `tipo`, `costo_prestacion_economica`, `gravedad`.

- `prima_anual` es la única columna que supera el **10%** de faltantes.
- `costo_asistencial` supera el **5%** y arrastra nulos a `costo_total` / `log_costo_*` / `*_w` en staging (ya observado en 1.3.4 / GOF P12: 2 562 filas sin costo winsorizado).
- No se detectaron strings vacíos ni sentinels tipo `"NA"`/`"-"` adicionales: los faltantes son NaN explícitos del CSV.

---

### C. Patrones de co-ocurrencia

![Patrones de co-ocurrencia](imgs/01_patrones_coocurrencia.png)

![Matriz visual (muestra de filas incompletas)](imgs/01_matriz_faltantes_muestra.png)

**empresas** (orden del patrón: ciudad | departamento | prima):

| Patrón | N filas | % | Lectura |
|---|---:|---:|---|
| completo | 4 225 | 84.50% | — |
| solo `prima_anual` | 551 | 11.02% | Dominante |
| `ciudad` + `departamento` | 196 | 3.92% | Geo siempre junta |
| las tres | 28 | 0.56% | — |
| solo ciudad / solo depto | 0 | 0% | **Nunca** ocurre |

- `ciudad` y `departamento` son un **bloque**: si falta una, falta la otra (224 filas). Compatible con un único campo geográfico mal capturado o no reportado.
- La mayoría de faltantes de prima (**551/579**) ocurren con geo completa → no son el mismo mecanismo que el bloque geográfico.

**siniestros** (orden: parte_cuerpo | dias | costo_asistencial):

| Patrón | N filas | % |
|---|---:|---:|
| completo | 34 350 | 86.10% |
| solo `costo_asistencial` | 2 352 | 5.90% |
| solo `dias_incapacidad` | 1 492 | 3.74% |
| solo `parte_cuerpo` | 1 431 | 3.59% |
| pares / triple | 269 | 0.67% |

- Predominan faltantes **univariados** (casi independientes entre sí); la intersección de las tres columnas es mínima (7 filas).
- Esto favorece estrategias de imputación **por variable** (no un único “registro inválido” a descartar).

---

### D. Tasas estratificadas (señales para 1.4.2)

![Tasas estratificadas](imgs/01_faltantes_estratificados.png)

Cuantificación condicionada (aún **sin** test formal de mecanismo):

| Variable faltante | Estrato | Tasa |
|---|---|---:|
| `dias_incapacidad` | tipo = AT | 2.95% |
| `dias_incapacidad` | tipo = EL | **11.68%** |
| `costo_asistencial` | gravedad = leve | 3.62% |
| `costo_asistencial` | gravedad = grave | 12.84% |
| `costo_asistencial` | gravedad = mortal | **35.77%** |
| `prima_anual` | por `clase_riesgo` | ~10.7–12.4% (casi plano) |
| `ciudad` | por `sector` | ~3–7% (variación moderada) |

- La tasa de faltantes de `dias_incapacidad` en **EL (~4× AT)** y de `costo_asistencial` creciente con **gravedad** (hasta ~36% en mortal) son señales fuertes de dependencia respecto de variables observadas → candidatas a **MAR** en 1.4.2.
- `prima_anual` no varía mucho por clase de riesgo → menos evidencia estratificada aquí; el mecanismo se evaluará con otras covariables / tests.

---

### E. Implicaciones preliminares para modelado (sin imputar aún)

1. **No hacer listwise deletion** sobre el universo de empresas/siniestros: se perdería ~14–15% de filas y, en siniestros, se sesgaría la cola de severidad/costo (faltantes concentrados en EL y mortal).
2. **Features geográficas** (`ciudad`/`departamento`): ya descartadas como predictores principales en 1.3 (P11); el 4.5% de nulos refuerza tratarlas como opcionales / con categoría “desconocido” si se usan solo para segmentación.
3. **`prima_anual` (11.6%)**: predictor candidato con hueco material → requiere estrategia de imputación o flag de missing antes de S03.
4. **`costo_asistencial` / `dias_incapacidad`**: outcomes o componentes de severidad; imputar o modelar con missingness informativa puede sesgar el resultado técnico — evaluar en 1.4.3–1.4.4 frente a descartar solo esas filas en modelos de severidad.
5. Staging de resumen reutilizable: `faltantes_resumen_datasets`, `faltantes_resumen_columnas`, `faltantes_patrones`, `faltantes_por_estrato` en `data/staging/S01/`.

---

### Pendiente (siguientes procesos de 1.4)

- [ ] 1.4.2 – Hipótesis de mecanismo (MCAR / MAR / MNAR) con pruebas formales sobre las señales de la sección D.
- [ ] 1.4.3 – Estrategia de imputación (y aplicación).
- [ ] 1.4.4 – Evaluación del efecto sobre el modelado vs descartar registros.
