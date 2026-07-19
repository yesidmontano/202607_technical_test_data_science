### **S04: Impacto e inferencia causal**
Objetivo: La ARL invirtió en un programa de prevención adoptado por cerca de 1500 empresas en distintos momentos entre 2019 y 2022, registrado en el archivo programas_prevencion.csv. La adopción no fue aleatoria. Se quiere saber si el programa redujo la siniestralidad.

---

### **Requerimiento 4.1**
Proponer una estrategia de identificación creíble para estimar el efecto causal del programa sobre la siniestralidad. Representar el problema con un DAG, enunciar los supuestos de identificación y las principales amenazas a la validez.

---

#### 4.1.1 Estrategia de identificación causal

**Diseño:** *Difference-in-Differences* escalonado (Callaway–Sant’Anna / cohortes por año de adopción), porque el tratamiento entra en momentos distintos (2019–2022) y no es aleatorio.

| Pieza | Definición |
|---|---|
| Unidad | Empresa–año (`temporal_empresa_anio`, 2018–2024) |
| Tratamiento | `D_it = 1` desde el año de `fecha_inicio` en `programas_prevencion` |
| Outcome | `frecuencia_x100` (principal); `costo_total / n_trabajadores` (secundario) |
| Controles | Nunca tratadas + aún no tratadas (nunca-tratadas como ancla) |
| Covariables | Clase de riesgo, sector, tamaño, siniestralidad pre-tratamiento |

**Por qué no OLS / matching solo:** la adopción se concentra en empresas de mayor riesgo (selección); DiD usa la variación *dentro* de empresa antes/después, con tendencias de controles como contrafactual.

##### DAG

DAG realizado con Mermaid.ai, resultado en `sections/S04-Impacto_Inferencia_Causal/4_1_Estrategia de identificacion causal/results/imgs/01_DAG.png`

##### Supuestos de identificación

1. **Tendencias paralelas (condicionales):** sin programa, tratadas y controles habrían seguido la misma trayectoria de siniestralidad, condicional a `X` y FE.
2. **No anticipación:** el outcome no cambia *antes* de `fecha_inicio` por el anuncio del programa.
3. **SUTVA:** el tratamiento de una empresa no afecta la siniestralidad de otra.
4. **Overlap:** hay controles comparables en cada cohorte de adopción.

##### Amenazas a la validez

| Amenaza | Riesgo | Mitigación |
|---|---|---|
| Selección por shock previo (Ashenfelter) | Adoptan tras un pico de siniestros → falsa reducción | Event-study pre-trends; excluir año −1 si hay dip |
| Confusión temporal (COVID 2020) | Shock común coincide con cohortes | FE de año; cohortes heterogéneas CS; sensibilidad sin 2020 |
| Heterogeneidad por programa | Efecto promedio oculta programas nulos | ATT por tipo de programa / intensidad (`horas`, `cobertura`) |
| TWFE clásico con adopción escalonada | Sesgo si efectos varían en el tiempo | Estimador CS / stacked DiD (no TWFE simple) |
| `U` (cultura SST) | Sesgo de selección no observable | Placebos pre-tratamiento; bound de sensibilidad |

**Estimando:** ATT promedio del programa sobre la frecuencia de siniestros (y, en 4.3, su traducción a valor económico).
