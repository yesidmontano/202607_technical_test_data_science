### **Requerimiento**
A partir de las preguntas que surjan del análisis exploratorio, proponer y justificar al menos tres pruebas de hipótesis pertinentes para el negocio. Para cada una formular las hipótesis nula y alterna, elegir la prueba adecuada verificando sus supuestos, corregir por comparaciones múltiples cuando corresponda, y distinguir la significancia estadística de la relevancia práctica reportando el tamaño del efecto.

---

## 1.3.1 – Pruebas sobre Decisiones de Arquitectura de Modelo (P1, P2, P4, P6)

> Generado a partir de `code/01-hip_arquitectura_modelo/hip_arquitectura_modelo.py`
> Datasets: `empresa_siniestralidad_completa.parquet` (5 000 empresas) · `siniestros_tratados.parquet` (39 894 siniestros)

---

### P1 – ¿Sobredispersión real en el conteo de siniestros?

#### Hipótesis
- **H₀:** La varianza del conteo de siniestros por empresa es igual a su media → distribución Poisson es suficiente.
- **H₁:** La varianza es significativamente mayor que la media → sobredispersión real → Binomial Negativa recomendada.

#### Justificación de la prueba elegida
Se aplica la **prueba de Cameron & Trivedi (1990)** — test asintótico con distribución N(0,1) bajo H₀ — complementada con una **razón de verosimilitud (LR) NB vs Poisson** como confirmación. Esta doble estrategia es estándar en la literatura actuarial: el test CT verifica formalmente la condición de equidispersión, y el LR cuantifica la mejora de ajuste de pasar a NB.

Se descartó la prueba F de dispersión (más común en GLM sobre datos continuos) y el test chi-cuadrado de bondad de ajuste (sensible al número de celdas vacías con recuentos altos).

#### Verificación de supuestos
| Supuesto | Verificación |
|---|---|
| Muestra independiente | ✓ Una empresa = una observación; sin dependencia longitudinal en este corte |
| n suficientemente grande para CT | ✓ n=5 000; CT asintótico válido |
| Especificación M0 correcta (Poisson intercepto) | ✓ Media estimada con MLE |

#### Resultados
| Estadístico | Valor |
|---|---|
| Media E[N] | 7.98 siniestros/empresa |
| Varianza Var[N] | 146.54 |
| Ratio Var/E[N] | **18.37** (debería ser ≈ 1 bajo Poisson) |
| T Cameron-Trivedi | **868.14** |
| p-valor (1-cola) | **< 10⁻¹⁵** |
| LR NB vs Poisson | **34 153** (df=1) |
| p-valor LR | **< 10⁻¹⁵** |
| AIC Poisson | 65 517 |
| AIC NB | 31 367 (−34 151 puntos) |

**Decisión: RECHAZAR H₀.** Sobredispersión masiva confirmada por ambas pruebas.

#### Corrección por comparaciones múltiples
Se aplica Holm-Bonferroni sobre las 4 pruebas simultáneas (P1, P2, P4, P6). p-ajustado P1 ≈ 0 → la decisión no cambia.

#### Significancia estadística vs Relevancia práctica
- **Significancia:** p < 10⁻¹⁵ — inequívoca, aun con la corrección más conservadora.
- **Tamaño del efecto:** φ = (Var − E)/E = **17.37** → sobredispersión de primer orden (φ >> 1).
- **Relevancia práctica:** Un modelo Poisson subestimaría masivamente la varianza del resultado técnico, generando intervalos de confianza demasiado estrechos y tarifas mal calibradas. El diferencial de AIC (−34 151) confirma que la NB es el modelo base correcto para S03. **No es simplemente un hallazgo estadístico — es una decisión de arquitectura obligatoria.**

![P1 Sobredispersión](imgs/01_P1_sobredispersion.png)

---

### P2 – ¿El 7.5% de ceros es excesivo más allá de la NB?

#### Hipótesis
- **H₀:** La proporción de empresas sin siniestros (ceros) es compatible con la NB estimada (ZI no necesario).
- **H₁:** Los ceros observados exceden los esperados por NB → se requiere componente adicional de ceros (ZIP/ZINB).

#### Justificación de la prueba elegida
Se usan dos pruebas complementarias:
1. **Chi-cuadrado de bondad de ajuste** en la celda de ceros: compara ceros observados vs esperados bajo la NB calibrada.
2. **Prueba binomial exacta (1-cola)**: H₁ es "más ceros que lo esperado por NB" — la prueba binomial exacta es la más conservadora y adecuada cuando n en la celda es pequeño.

El test de Vuong (comparación directa Poisson vs ZIP) fue descartado porque primero se validó Poisson en P1 y la comparación relevante es NB vs ZINB.

#### Verificación de supuestos
| Supuesto | Verificación |
|---|---|
| NB correctamente especificada bajo H₀ | ✓ α NB estimado vía MLE (α = 1.0603) |
| n·p_zero_NB > 5 para chi-cuadrado | ✓ n_esperados_ceros = 600.6 > 5 |
| Binomial exacta: observaciones i.i.d. | ✓ Una empresa = un Bernoulli |

#### Resultados
| Estadístico | Valor |
|---|---|
| α NB estimado | 1.0603 |
| r = 1/α | 0.9431 |
| P(Y=0 | NB) | 12.01% |
| Ceros observados | 375 (7.50%) |
| Ceros esperados NB | 600.6 (12.01%) |
| χ² bondad de ajuste | 96.32 |
| p-valor chi-cuadrado | < 10⁻¹⁵ |
| p-valor binomial (1-cola mayor) | **1.000** |

**Decisión: NO RECHAZAR H₀.** El resultado es sorprendente pero correcto: la NB predice *más* ceros de los observados. Los ceros observados son **37.6% menores** que los esperados bajo NB. La distribución NB "sobrepredice" los ceros.

#### Corrección por comparaciones múltiples
p-ajustado Holm = 1.0 → la no-decisión se confirma.

#### Significancia estadística vs Relevancia práctica
- **Significancia:** p = 1.0 → no se rechaza H₀. La NB absorbe y supera los ceros observados.
- **Tamaño del efecto:** exceso relativo = **−37.6%** (déficit de ceros, no exceso).
- **Relevancia práctica:** Este hallazgo tiene consecuencia directa: **no se recomienda un modelo Zero-Inflated (ZIP/ZINB) para S03**. La NB estándar es suficiente para manejar el componente de ceros; añadir una componente ZI sería sobrepatrametización. El 7.5% de ceros observados es un subconjunto del cola inferior de la NB estimada.

![P2 Exceso de ceros](imgs/01_P2_exceso_ceros.png)

---

### P4 – ¿El sector tiene efecto significativo más allá de la clase de riesgo?

#### Hipótesis
- **H₀:** El sector económico no aporta información sobre la frecuencia de siniestros una vez controlada la clase de riesgo (β_sector = 0 en el GLM).
- **H₁:** El sector tiene efecto incremental significativo controlando clase de riesgo.

#### Justificación de la prueba elegida
Estrategia de dos niveles:
1. **Kruskal-Wallis** sobre frecuencia por sector (sin controlar clase): confirma la existencia de diferencias a nivel marginal. No paramétrico dado la distribución asimétrica de frecuencia_x100.
2. **LR test GLM Poisson con offset** (log n_trabajadores): compara M₀ (solo clase) vs M₁ (clase + sector) para cuantificar el efecto incremental ajustado. Este es el test directo de la H₀.
3. **Post-hoc Dunn con Holm-Bonferroni**: identifica qué pares de sectores son distinguibles tras corrección.

Se descartó ANOVA porque la distribución de frecuencia viola normalidad e igualdad de varianzas. El GLM Poisson es el modelo canónico para datos de conteo con exposición heterogénea.

#### Verificación de supuestos
| Supuesto | Verificación |
|---|---|
| K-W: distribuciones con misma forma | Parcialmente: distribuciones sesgadas similares dentro de sector |
| K-W: muestras independientes | ✓ Cada empresa es independiente |
| GLM Poisson: independencia | ✓ |
| GLM: especificación lineal del log | Asumida; se verificó con residuales |
| Dunn: independencia de pares | ✓ |

#### Resultados

**Kruskal-Wallis (sin controlar clase):**
| Estadístico | Valor |
|---|---|
| H K-W | 2 209.90 (df=14) |
| p-valor | < 10⁻¹⁵ |
| **η²** | **0.4405** → efecto **grande** |

**LR test GLM Poisson (incremental, controlando clase):**
| Estadístico | Valor |
|---|---|
| LR | 32.36 (df=14) |
| p-valor | 0.0036 |
| p-ajustado Holm | 0.0071 |
| Pseudo-R² McFadden incremental | 0.0012 |

**Post-hoc Dunn (Holm-Bonferroni):**
- **86 de 105 pares** son significativamente distintos (82% de pares posibles).
- Solo 19 pares no se distinguen estadísticamente tras corrección.

**Decisión: RECHAZAR H₀ en ambos niveles.** El sector tiene efecto significativo, tanto marginalmente como controlando clase de riesgo.

#### Corrección por comparaciones múltiples
- Prueba global K-W: 1 prueba, no aplica corrección adicional.
- Post-hoc Dunn: corrección Holm-Bonferroni sobre 105 pares — aplicada dentro del script.
- Corrección conjunta P1–P6 (Holm): p-ajustado P4 = 0.0071 → sigue siendo significativo.

#### Significancia estadística vs Relevancia práctica
- **Significancia:** p = 0.0036 (LR GLM) y p < 10⁻¹⁵ (K-W) — significativos en ambas pruebas.
- **Tamaño del efecto (K-W):** η² = **0.44** → efecto **grande** (umbral grande = 0.14). El sector explica ~44% de la varianza del rango en frecuencia.
- **Tamaño del efecto (GLM):** Pseudo-R² incremental = **0.0012** → efecto muy pequeño en escala de log-verosimilitud ajustada por clase.
- **Tensión estadística vs práctica:** Hay una aparente contradicción: η² grande en K-W vs Pseudo-R² pequeño en GLM. La explicación es que el K-W captura la dispersión total del sector (incluyendo el efecto que comparte con clase), mientras que el GLM captura solo el efecto *adicional* de sector una vez que clase ya explica el grueso. **La conclusión práctica es que sector aporta señal incremental real pero moderada: debe incluirse en el modelo pero su peso será secundario a clase_riesgo.**

![P4 Sector incremental](imgs/01_P4_sector_incremental.png)

---

### P6 – ¿Las EL tienen mayor severidad que los AT?

#### Hipótesis
- **H₀:** La distribución de días de incapacidad es igual en AT (Accidente de Trabajo) y EL (Enfermedad Laboral).
- **H₁:** La distribución en EL está desplazada hacia valores mayores (prueba 1-cola).

#### Justificación de la prueba elegida
**Mann-Whitney U (1-cola)** es la prueba óptima dado que:
- La asimetría de severidad es 10.42 en escala original → normalidad imposible.
- MWU prueba dominancia estocástica: P(EL > AT) > 0.5 bajo H₁.
- Robusto frente a outliers y escala log-normal.

Se descartó t de Student (viola normalidad con n grande pero asimetría extrema) y ANCOVA (no aplica en variable respuesta con cola tan pesada sin transformación).

**Verificación adicional con K-S de dos muestras**: para comprobar si las distribuciones difieren solo en localización (requisito estricto para MWU como prueba de "igual distribución") o también en forma.

#### Verificación de supuestos
| Supuesto | Verificación | Resultado |
|---|---|---|
| Independencia AT vs EL | ✓ Siniestros distintos | OK |
| Ordinalidad de días (MWU) | ✓ Variable continua | OK |
| Misma forma distribucional | K-S entre AT y EL: **KS=0.1858, p < 10⁻¹²⁸** | ❌ Difieren en forma y localización |

El incumplimiento del supuesto de misma forma implica que MWU mide **dominancia estocástica general** (no solo diferencia de medianas). Esto se reporta explícitamente y no invalida la prueba — la convierte en una prueba más general y conservadora.

#### Resultados
| Estadístico | AT | EL |
|---|---|---|
| n | 33 377 | 4 860 |
| Mediana días (winsorizado) | **6.0** | **10.0** |
| Media días | 13.5 | 22.3 |
| P90 días | 35.0 | 60.0 |

| Estadístico | Valor |
|---|---|
| U Mann-Whitney | 100 185 635 |
| p-valor (1-cola, EL > AT) | **2.32 × 10⁻¹⁵⁶** |
| p-ajustado Holm | **6.96 × 10⁻¹⁵⁶** |
| **Cliff's delta (δ)** | **0.2352** → magnitud **mediana** |

**Decisión: RECHAZAR H₀.** EL es estadística y prácticamente más severa que AT.

#### Corrección por comparaciones múltiples
Corrección conjunta Holm P1–P6: p-ajustado = 6.96 × 10⁻¹⁵⁶ → la decisión no cambia.

#### Significancia estadística vs Relevancia práctica
- **Significancia:** p < 10⁻¹⁵⁵ — prácticamente en el límite de representación numérica. Con n > 38 000 cualquier diferencia pequeña sería significativa.
- **Tamaño del efecto:** Cliff's δ = **0.2352** → magnitud **mediana** (umbral mediano = 0.147). Esto significa que en ~61.8% de las comparaciones aleatorias entre un siniestro EL y un AT, el EL genera más días.
- **Relevancia práctica cuantitativa:**
  - Mediana EL = 10 días vs AT = 6 días → **1.67× más días** de incapacidad.
  - P90 EL = 60 días vs AT = 35 días → en la cola el gap se amplifica.
  - **Implicación para S03:** modelos de severidad separados por tipo de siniestro no son un capricho metodológico — son necesarios porque la distribución de fondo difiere en forma *y* localización. Un único modelo de severidad mezclaría dos procesos generadores distintos.

![P6 Severidad AT vs EL](imgs/01_P6_severidad_at_vs_el.png)

---

## Síntesis – Corrección por Comparaciones Múltiples (Holm-Bonferroni)

| Prueba | p original | p ajustado | ¿Rechaza H₀? |
|---|---|---|---|
| P1 – Sobredispersión | < 10⁻¹⁵ | < 10⁻¹⁵ | **SÍ** |
| P2 – Exceso de ceros | 1.000 | 1.000 | **NO** |
| P4 – Sector incremental | 0.0036 | 0.0071 | **SÍ** |
| P6 – AT vs EL severidad | 2.3×10⁻¹⁵⁶ | 7.0×10⁻¹⁵⁶ | **SÍ** |

---

## Implicaciones para la Arquitectura del Modelo (S03)

| Pregunta | Decisión confirmada |
|---|---|
| P1 → Sobredispersión | Usar **Binomial Negativa** como modelo base de frecuencia. Poisson descartado. |
| P2 → Exceso de ceros | **No** añadir componente Zero-Inflated. NB cubre suficientemente los ceros (predice incluso más ceros que los observados). |
| P4 → Sector incremental | Incluir `sector` en el feature set de todos los modelos. Su efecto es real pero moderado (~44% varianza de rango; ~0.1% mejora ajuste LR). Encoding recomendado: target encoding o embeddings CIIU. |
| P6 → AT vs EL | Ajustar **modelos de severidad separados** para AT y EL. Fusionarlos en uno solo mezclaría dos distribuciones con forma y localización distintas. |

---

*Análisis realizado con `sura_brand` · Sección S01-1.3 Pruebas de Hipótesis · Prueba Técnica Grupo SURA.*
