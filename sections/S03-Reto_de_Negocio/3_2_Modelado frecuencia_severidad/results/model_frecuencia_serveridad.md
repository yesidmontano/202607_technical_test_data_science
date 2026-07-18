### **S03: Modelación para reto de negocio**
Objetivo: El reto de negocio: la Dirección necesita anticipar el resultado técnico del portafolio y decidir dónde ajustar la suscripción y la tarifa. Usted debe modelar el costo esperado de siniestralidad y convertirlo en una recomendación.

---

### **Requerimiento 3.2**
Modelar la frecuencia y la severidad de los siniestros para estimar el costo esperado de siniestralidad por empresa y por clase de riesgo. Justificar las distribuciones elegidas y el tratamiento de la exposición, y validar el ajuste y la capacidad predictiva del modelo.

---

### 3.2.1. Modelado de frecuencia y severidad de siniestros

**Script:** `code/01-modelo/01-modelo.py`  
**Staging:** `data/staging/S03/modelo_*.parquet`
**Figuras:** `results/imgs/01_modelo_*.png`

---

#### Arquitectura (alineada a 3.1.2 y S01)

| Componente | Familia | Especificación | Justificación |
|---|---|---|---|
| **Frecuencia** | Binomial Negativa + offset `log(n_trabajadores)` | `n_siniestros ~ C(clase)+C(segmento)+C(sector)+log1p(lag_n)` | P1 sobredispersión; P2 sin ZI; predictores 1.2.6 |
| **Severidad** | Lognormal (OLS en log), **AT / EL separados** | `log(costo_w) ~ C(clase)+C(segmento)+C(gravedad)` | P6 AT≠EL; P12 lognormal; S1 dependencia → condicionar |
| **Pure premium** | `E[Costo]=E[N]×E[Sev\|X]` | Sev marginaliza `P(tipo\|clase)` y `P(gravedad\|clase,tipo)` | Gravedad no observable en pricing |

**Train:** 2019–2023 (requiere lag) · **Holdout:** 2024 · **Proyección:** features 2024 + lag = n_siniestros_2024 → próximo año.

α NB (MLE) = **0.114**.

---

#### Métricas holdout 2024

| Componente | MAE | Spearman | Otras |
|---|---|---|---|
| Frecuencia E[N] | **0.81** siniestros | **0.60** | mean pred 1.17 vs obs 1.14 |
| Severidad AT | **1.50 M** COP | **0.57** | R²_log = **0.54** |
| Severidad EL | **1.40 M** COP | **0.53** | R²_log = **0.57** |
| Costo empresa | **3.54 M** COP | **0.57** | Portafolio pred/obs = **0.985** |

Calibración de portafolio casi perfecta (pred **17.55 B** vs obs **17.82 B** COP).

---

#### Efectos de clase de riesgo (frecuencia)

IRR vs clase 1: C2=**1.54** · C3=**2.39** · C4=**3.56** · C5=**5.00** (todos p≪0.001).

![Frecuencia obs vs pred](imgs/01_modelo_freq_obs_vs_pred.png)

![IRR por clase](imgs/01_modelo_freq_irr_clase.png)

---

#### Severidad condicionada

E[costo|siniestro] crece con clase y es mayor en Micro (heatmap clase × tamaño). La gravedad concentra el poder explicativo (R²_log ~0.54); en pricing se promedia con el mix histórico por clase×tipo.

![Severidad heatmap](imgs/01_modelo_sev_heatmap_clase_segmento.png)

![Costo holdout](imgs/01_modelo_costo_obs_vs_pred.png)

---

#### Proyección próximo año (por clase de riesgo)

| Clase | E[N] media | E[Costo] agregado | Share costo | LR pred (agregado) |
|---|---|---|---|---|
| 1 | 0.37 | 0.78 B | 4.5% | 0.57 |
| 2 | 0.68 | 1.27 B | 7.3% | 0.60 |
| 3 | 1.10 | 2.76 B | 15.9% | 0.54 |
| 4 | 1.73 | 5.78 B | 33.2% | 0.58 |
| 5 | 2.57 | 6.82 B | 39.2% | 0.67 |
| **Total** | **5 788** siniestros | **17.42 B** COP | 100% | — |

- Empresas con LR predicho > 1: **169 (3.38%)** → candidatos prioritarios a ajuste de tarifa/suscripción.
- Clases 4–5 concentran **~72%** del costo esperado del portafolio.

![Proyección por clase](imgs/01_modelo_proyeccion_clase.png)

![Top empresas](imgs/01_modelo_top_empresas_costo.png)

![Distribución LR](imgs/01_modelo_lr_distribucion.png)

---

#### Implicaciones para 3.3 / 3.4 (revisión)

1. Usar `modelo_pred_empresa` (`horizonte=proximo_anio`) como base de la proyección de portafolio.
2. Priorizar suscripción en el Top de `costo_pred` y tarifa donde `insuficiente_pred=1`.
3. Clase 5 aporta ~39% del costo esperado con LR agregado más alto (0.67) — foco de monitoreo.
4. Limitación: severidad marginaliza gravedad; un modelo de claim-by-claim con gravedad conocida es más preciso pero no aplica a pricing ex-ante.
5. Próximo paso natural (3.3): agregar intervalos / escenarios de estrés sobre el mix sectorial (S2).

---

### 3.2.2 Justificación de distribuciones elegidas, el tratamiento de la exposición, y validación del ajuste y la capacidad predictiva del modelo

Esta sección formaliza *por qué* la arquitectura de 3.2.1 es la adecuada para responder la pregunta de negocio (costo esperado por empresa y por clase), anclada en evidencia de S01, en los supuestos validados en 3.1.2 y en las métricas de holdout 2024.

---

#### 1. Justificación de las distribuciones

##### Frecuencia → Binomial Negativa (no Poisson, no zero-inflated)

| Evidencia | Hallazgo | Implicación |
|---|---|---|
| S01–P1 (Cameron–Trivedi + LR) | Sobredispersión masiva; AIC NB ≪ Poisson | Poisson subestima la varianza del resultado técnico → tarifas e IC mal calibrados |
| S01–P2 | Ceros observados ≤ esperados bajo NB | No hace falta ZIP/ZINB; la NB ya cubre la masa en cero |
| 3.2.1 (MLE) | α NB = **0.114** (sobredispersión confirmada en el panel 2019–2023) | Se mantiene NB como familia de frecuencia en producción |
| 3.2.1 (IRR) | Clase 5 vs 1: IRR = **5.0** (monótono C2…C5) | La NB con `C(clase_riesgo)` captura el gradiente ARL esperado |

**Descartado:** Poisson (equidispersión rechazada) y zero-inflated (P2 no rechaza H₀ de ceros compatibles con NB).

##### Severidad (costo por siniestro) → Lognormal, modelos AT / EL separados

| Evidencia | Hallazgo | Implicación |
|---|---|---|
| S01–P12 | Lognormal preferida frente a Gamma para costo | OLS en `log(costo_w)` + corrección `E[Y]=exp(μ+σ²/2)` |
| S01–P6 | AT ≠ EL en localización y forma | Un solo modelo mezclaría dos procesos generadores |
| 3.1.2–S1 | Dependencia freq–sev material (ρ≈0.35–0.42) | Severidad **condicionada** a clase × tamaño (+ gravedad) |
| 3.2.1 | R²_log AT/EL = **0.54 / 0.57**; sin gravedad R²≈0.04 | `C(gravedad)` es el driver principal; clase/tamaño aportan el perfil de pricing |

**Descartado:** severidad independiente de la frecuencia; un único modelo AT+EL; Gamma como familia base (runner-up en P12, no elegida tras lognormal).

##### Agregación a costo esperado → pure premium `E[N] × E[Sev|X]`

Es la descomposición actuarial estándar del costo agregado. Permite:
1. Explicar a Dirección *cuánto* viene de frecuencia vs. severidad.
2. Condicionar severidad (S1) sin romper la interpretación de la NB.
3. Proyectar por empresa y agregar por clase de riesgo (requerimiento 3.2).

Como en pricing la gravedad y el tipo (AT/EL) no se observan *ex ante*, E[Sev|X] **marginaliza** `P(tipo|clase)` y `P(gravedad|clase,tipo)` estimados en train — coherente con decisión de negocio, no con un modelo claim-by-claim post-evento.

---

#### 2. Tratamiento de la exposición

La exposición relevante es el **número de trabajadores afiliados** (`n_trabajadores`): más personas expuestas → más siniestros esperados, a tasa relativa comparable.

| Decisión | Implementación | Motivo |
|---|---|---|
| Offset en la NB | `offset = log(max(n_trabajadores, 1))` | Modela la **tasa** λ = E[N]/exposición; evita que el tamaño absorba espuriamente el efecto de clase |
| Clip en 1 | Empresas con 0 trabajadores no generan log indefinido | Robustez numérica; no altera el ranking del portafolio |
| Segmento de tamaño como covariable | `C(segmento)` además del offset | Captura heterogeneidad de tasa por Micro/Pequeña/Mediana/Grande (P7: Micro con frecuencia relativa mayor) |
| Lag de frecuencia | `log1p(n_siniestros_{t−1})` | Persistencia documentada en S01; sin leakage (solo pasado) |
| Sin usar prima como exposición | Prima entra solo en el **loss ratio** post-modelo | La pregunta pide costo esperado; la prima es el comparador tarifario (S3), no el denominador del conteo |

En severidad no hay offset de exposición: el target es el **costo por siniestro** (unidad de análisis = evento), no el costo por trabajador.

---

#### 3. Validación del ajuste y de la capacidad predictiva

**Diseño de evaluación (evita leakage temporal):**
- Train: 2019–2023 (primer año con lag disponible).
- Holdout: 2024 (mismo esquema que el baseline 1.5).
- Proyección de negocio: features 2024 + lag = n_2024 → E[Costo] del próximo año.

##### Ajuste / discriminación en holdout

| Nivel | Métrica | Valor | Lectura |
|---|---|---|---|
| Frecuencia | MAE / Spearman / R² | 0.81 / **0.60** / 0.66 | Ranking y nivel medios bien recuperados |
| Severidad AT | MAE / Spearman / R²_log | 1.50 M / 0.57 / **0.54** | Ajuste log-escala sólido cuando gravedad es conocida |
| Severidad EL | MAE / Spearman / R²_log | 1.40 M / 0.53 / **0.57** | Idem; n menor pero estable |
| Costo empresa | MAE / Spearman / R² | 3.54 M / **0.57** / 0.22 | Discriminación útil; R² bajo típico de colas pesadas a nivel empresa |
| Portafolio | pred / obs | **0.985** (17.55 vs 17.82 B) | Calibración agregada casi perfecta — crítica para Dirección |

##### Validación por clase de riesgo (objeto del requerimiento)

- Los IRR son monótonos y altamente significativos → el modelo respeta el ordenamiento ARL.
- En proyección, clases 4–5 concentran ~72% del costo esperado; la clase 5 tiene el LR agregado más alto (0.67).
- El holdout por clase (barras obs vs pred en figuras de 3.2.1) muestra alineación de medias de frecuencia y de costo agregado.

##### Límites del ajuste (transparencia)

1. **R² de costo a nivel empresa (0.22)** refleja rareza y cola pesada: pocas empresas concentran gran parte del costo. La métrica de negocio prioritaria es calibración de portafolio + ranking (Spearman), no R² individual.
2. **Severidad en pricing** promedia gravedad: el R²_log 0.54 aplica al modelo claim-level con gravedad observada; el E[Sev] ex-ante es deliberadamente más suave.
3. **Dependencia freq–sev (S1)** se mitiga condicionando a clase×tamaño×mix de gravedad, no con un cópula completo — suficiente para la decisión tarifaria/suscripción, mejorable en iteraciones futuras.

##### Criterio de aceptación frente al uso de negocio

El modelo se considera **apto para soportar las decisiones de 3.1.1** porque:
1. Estima E[Costo] por empresa y por clase con discriminación Spearman ≈ 0.57–0.60.
2. Recupera el total del portafolio en holdout (ratio 0.985).
3. Señala bolsas de insuficiencia (169 empresas con LR pred > 1; foco en clases altas) alineadas al supuesto S3.
4. Usa familias y exposición justificadas empíricamente (S01 + 3.1.2), no por conveniencia computacional.

---

#### 4. Síntesis decisional

| Pregunta del requerimiento 3.2 | Respuesta a partir de 3.2.1 |
|---|---|
| ¿Qué distribución de frecuencia? | **NB** con α≈0.114; Poisson y ZI descartados |
| ¿Qué distribución de severidad? | **Lognormal** separada AT/EL, condicionada a clase × tamaño × gravedad |
| ¿Cómo se trata la exposición? | **Offset** `log(n_trabajadores)` en frecuencia; segmento como covariable de tasa |
| ¿El modelo ajusta y predice? | Sí a nivel portafolio (0.985) y ranking (Spearman≈0.57–0.60); con limitaciones explícitas en cola individual |


