# Resumen Ejecutivo — Sección S01: Metodología, EDA y Análisis

> **Prueba Técnica · Grupo SURA · Dirección de Analítica**  
> Secciones cubiertas: 1.1 CRISP-DM · 1.2 EDA · 1.3 Pruebas de Hipótesis · 1.4 Diagnóstico de Datos Faltantes · 1.5 Baseline

---

## 1. Encuadre Metodológico (CRISP-DM)

El problema se enmarcó con la metodología CRISP-DM. La **pregunta analítica central** es:

> *¿Cuáles empresas afiliadas presentarán alta siniestralidad el próximo año?*

El problema se traduce a una **clasificación binaria** con los siguientes elementos definitivos:

| Elemento | Definición |
|---|---|
| **Unidad de análisis** | Empresa (`id_empresa`) |
| **Variable objetivo** | `alta_siniestralidad` = 1 si la empresa estará en el **Top 10%** de `n_siniestros` en el año T |
| **Esquema de validación** | Temporal: entrenar con datos hasta T−1, validar con año T |
| **Métricas técnicas** | AUC-ROC, Recall, Precisión, F1-Score (enfoque en el decil superior) |
| **Métricas de negocio** | Reducción de costos por intervención focalizada; % mejora vs baseline |
| **Baseline** | Predecir Top 10% del año anterior (regla lag T−1 → T) |
| **Riesgo principal de leakage** | Uso de variables de siniestros del año de predicción como features |

---

## 2. Análisis Exploratorio de Datos (EDA)

El EDA se ejecutó sobre **5 000 empresas** y **39 894 siniestros** del periodo 2018–2024, en cinco módulos: univariado, bivariado, temporal, outliers y correlaciones.

### 2.1 Hallazgos del Universo de Datos

| Dimensión | Hallazgo clave |
|---|---|
| **Frecuencia** | Distribución fuertemente asimétrica, 7.5% de empresas con cero siniestros, sobredispersión marcada |
| **Severidad** | Asimetría = 10.42; mediana 6 días, P90 = 37 días; escala log aproximadamente normal |
| **Costo** | Gini ≈ 0.702; el **top 10% de empresas concentra el 56.5% del costo total** |
| **Tamaño** | Portafolio dominado por **PyMEs (86.4%)**; micro ≤ 10 trab. representan el 12% |
| **Clase de riesgo** | Gradiente monotónico claro: la frecuencia mediana de clase 5 es **6.9× la de clase 1** |
| **Sector** | Dispersión de ~6× entre extremos: Construcción (36.0) vs TIC (5.9) siniestros×100 trab. |
| **Geografía** | Rango de medianas entre departamentos: solo **2.9 puntos** — efecto débil |
| **Estacionalidad** | Amplitud del índice mensual: **±2%** — sin patrón operativo relevante |
| **Persistencia** | Correlación `n_siniestros` t→t+1 ≈ **0.70**; retención del Top 10% ≈ **50% anual** |
| **Colinealidad** | VIF máximo ≈ **1.68** — todos los predictores candidatos son incluibles sin riesgo |

### 2.2 Feature Set Definitivo (Contrato EDA → S03)

| Feature | Transformación | Rol | Prioridad |
|---|---|---|---|
| `clase_riesgo` | Ordinal (1–5) | Predictor estructural | **Obligatorio** |
| `sector` | Target encoding / embeddings CIIU | Predictor estructural | **Obligatorio** |
| `log_n_trabajadores_w` | log + winsor P1–P99 | Offset de exposición | **Obligatorio** |
| `log_lag_n_siniestros` | log(1+lag_n), shift t−1 | Baseline predictivo | **Obligatorio** |
| `log_prima_anual_w` | log + winsor P1–P99 | Proxy riesgo/tamaño | Opcional (vigilar VIF) |
| `antiguedad_meses` | Sin transformación | Control de cohorte | Opcional |
| `departamento` | Dummy nacional | Control geográfico | Baja prioridad |
| `mes` / `año` | Dummies | Control temporal | Baja prioridad |

---

## 3. Pruebas de Hipótesis

Se realizaron **12 pruebas de hipótesis** organizadas en tres bloques, con corrección Holm-Bonferroni para múltiples comparaciones. **9 rechazan H₀** y 3 no rechazan — precisamente las tres de descarte (P2, P8, P11), lo que valida la consistencia del análisis.

### 3.1 Panorama de resultados

| # | Prueba | Resultado | Efecto práctico |
|---|---|---|---|
| P1 | Sobredispersión del conteo | **RECHAZA H₀** | φ = 17.4 → **NB obligatoria** |
| P2 | Exceso de ceros | NO rechaza H₀ | NB predice más ceros; **ZI innecesario** |
| P3 | Clases de riesgo | **RECHAZA H₀** | η² = 0.53; **5 niveles distinguibles**, no colapsar |
| P4 | Sector incremental | **RECHAZA H₀** | LR p=0.004; efecto moderado pero real |
| P5 | Interacción sector×clase | **RECHAZA H₀** | Pseudo-R² incr. = 0.0012; **prioridad baja** |
| P6 | Severidad AT vs EL | **RECHAZA H₀** | Cliff's δ=0.24; medianas 10 vs 6 días → **modelos separados** |
| P7 | Microempresas (tasa relativa) | **RECHAZA H₀** | δ=0.25; frecuencia 1.7× mayor; flag `es_micro` |
| P8 | Estacionalidad mensual | NO rechaza H₀ | Amplitud 3.8 pp; **descartar dummies de mes** |
| P9 | Persistencia conteo t→t+1 | **RECHAZA H₀** | Pearson r=0.70 → **lag obligatorio** |
| P10 | Retención Top 10% | **RECHAZA H₀** | Lift **5× vs azar**; Cohen h=0.93 |
| P11 | Heterogeneidad departamentos | NO rechaza H₀ | η²=0.002; **descartar geografía como predictor** |
| P12 | Bondad de ajuste costo | **RECHAZA H₀** (Normal exacta) | AIC: **Lognormal > Gamma** (ΔAIC = +11 257) |

### 3.2 Decisiones de Arquitectura Confirmadas

| Decisión | Sustento |
|---|---|
| **Modelo de frecuencia: Binomial Negativa** | P1: φ=17.4, ΔAIC=−34 151 vs Poisson |
| **No añadir componente Zero-Inflated** | P2: NB ya supera los ceros observados |
| **Modelos de severidad separados AT y EL** | P6: distribuciones difieren en forma y localización |
| **Familia de costo: Lognormal** | P12: ΔAIC=+11 257 vs Gamma |
| **`clase_riesgo` con 5 niveles, sin colapsar** | P3: δ≈0.40 en saltos adyacentes |
| **`log_lag_n_siniestros` obligatorio** | P9+P10: r=0.70 y lift 5× vs azar |

---

## 4. Diagnóstico de Datos Faltantes

### 4.1 Completitud global

| Dataset | Completitud celda | Filas con ≥1 nulo | Variables afectadas |
|---|---:|---:|---|
| `empresas.csv` | **97.95%** | **15.50%** | 3 de 10 |
| `siniestros.csv` | **98.38%** | **13.90%** | 3 de 9 |

A nivel celda, ambos datasets son altamente completos. A nivel fila, ~1 de cada 6–7 registros tiene al menos un nulo, lo que hace inviable la eliminación ingenua.

### 4.2 Mecanismos y estrategias adoptadas

| Variable | % falt. | Mecanismo | Estrategia adoptada | Impacto en modelado |
|---|---:|---|---|---|
| `ciudad` / `departamento` | 4.48% | **MCAR** | Categoría `desconocido` | Despreciable |
| `parte_cuerpo` | 4.01% | **MCAR** | Categoría `desconocido` | Despreciable |
| `prima_anual` | 11.58% | **MAR** (antigüedad + tamaño) | OLS estocástica log; R²=0.89 | Listwise sesga ~5.3% coefs de `clase_riesgo` e infla EE ×1.5 |
| `dias_incapacidad` | 4.15% | **MAR** (tipo EL 4× AT) | OLS estocástica log por tipo; R²=0.975 | Marginal en holdout; protege representatividad EL |
| `costo_asistencial` | 6.42% | **MAR + sospecha MNAR** | OLS estocástica log; R²=0.411 | Marginal; imputados concentrados en gravedad alta |

### 4.3 Veredicto operativo

**Decisión adoptada: usar los datasets imputados** como fuente de entrenamiento para S03 y S05:

- `data/staging/S01/empresas_imputadas.parquet` → 5 000 × 20, 0 NaN
- `data/staging/S01/siniestros_imputados.parquet` → 39 894 × 21, 0 NaN

**Descartado:**
- ❌ **Listwise deletion**: pierde 15.7% de empresas de train, sesga `clase_riesgo` ~5% e infla EE ×1.5.
- ❌ **Flags `miss_*` como features**: señal nula en holdout (p≈0.78–0.91); se conservan solo para auditoría.

---

## 5. Baseline

### 5.1 Regla de predicción

> Predecir `alta_siniestralidad = 1` en el año T a las mismas empresas que estuvieron en el **Top 10%** de `n_siniestros` en T−1.

Es un baseline robusto porque usa solo información disponible al cierre de T−1, tiene evidencia empírica de persistencia (lift ≈ 5×) y es el umbral mínimo que un modelo más costoso debe superar.

### 5.2 Desempeño (evaluación principal: 2023 → 2024)

| Métrica | Valor | Lectura |
|---|---:|---|
| **AUC-ROC** | **0.740** | Discriminación moderada-alta vs azar (0.50) |
| **Recall** | **0.532** | Captura el 53.2% del Top 10% real de 2024 |
| **Precisión** | **0.532** | De las 500 alertadas, 53.2% son verdaderos positivos |
| **F1-Score** | **0.532** | Balance recall–precisión |

La mitad del Top 10% real de 2024 son empresas "nuevas" que la regla lag no detecta — ahí radica el espacio de mejora para S03.

### 5.3 Estabilidad histórica (2018–2024)

| Par | AUC-ROC | F1 |
|---|---:|---:|
| 2018→2019 | 0.723 | 0.502 |
| 2019→2020 | 0.729 | 0.512 |
| 2020→2021 | 0.726 | 0.506 |
| 2021→2022 | 0.706 | 0.470 |
| 2022→2023 | 0.713 | 0.484 |
| **2023→2024 ★** | **0.740** | **0.532** |

Rango histórico F1 ≈ **0.47–0.53**. El baseline no es un modelo nulo — captura más de la mitad del Top 10% sin features adicionales.

### 5.4 Criterio de superación para S03

Un modelo candidato debe superar al baseline de forma **estable en ≥ 2 folds temporales**:

| Umbral mínimo | Valor |
|---|---|
| **F1-Score** | > 0.53 (media histórica ≈ 0.50) |
| **AUC-ROC** | > 0.74 |
| **Recall objetivo** | ≥ 0.80 (justificación de mayor complejidad) |

El énfasis de negocio está en el **Recall del decil superior** dado que el Top 10% de empresas concentra el **56.5% del costo total** del portafolio.

---

## 6. Síntesis: Lo que S01 Condiciona al Modelado (S02–S05)

### Decisiones de arquitectura obligatorias

| Decisión | Evidencia |
|---|---|
| **Binomial Negativa** para frecuencia | φ=17.4 (EDA+P1); ΔAIC=−34 151 vs Poisson |
| **Sin componente Zero-Inflated** | P2: NB supera ceros observados |
| **Modelos separados AT y EL** (severidad) | P6: KS p<10⁻¹²⁸; medianas 10 vs 6 días |
| **Familia Lognormal** para costo | P12: ΔAIC=+11 257 vs Gamma |
| **Winsorización P1–P99** en features numéricos | EDA outliers; IQR solo como diagnóstico |
| **Sin dummies de mes** | P8: amplitud 3.8 pp, W=0.037 |
| **Geografía solo como control descriptivo** | P11: η²=0.002; 0/21 pares Dunn significativos |

### Features obligatorios para S03

`clase_riesgo` (ordinal, 5 niveles) · `sector` (target encoding) · `log_n_trabajadores_w` (offset) · `log_lag_n_siniestros` (shift estricto T−1)

### Fuentes de datos para modelado

| Archivo | Contenido | Rol |
|---|---|---|
| `data/staging/S01/empresas_imputadas.parquet` | 5 000 × 20, 0 NaN | Fuente principal de train para S03/S05 |
| `data/staging/S01/siniestros_imputados.parquet` | 39 894 × 21, 0 NaN | Severidad y costo en S03 |
| `data/staging/temporal_empresa_anio.parquet` | Panel empresa×año con lag + target | CV temporal en S03 |
| `data/staging/S01/baseline_predicciones.parquet` | Predicciones baseline 2024 | Referencia para comparación |

---

*Análisis realizado con `sura_brand` · Sección S01 – Resumen Ejecutivo · Prueba Técnica Grupo SURA.*
