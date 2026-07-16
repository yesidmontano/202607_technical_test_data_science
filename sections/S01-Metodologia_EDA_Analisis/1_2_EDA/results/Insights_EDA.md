### **Requerimiento**
Realizar un análisis exploratorio completo: distribuciones univariadas de la frecuencia, la severidad, los costos y el tamaño de las empresas; asociaciones bivariadas de la siniestralidad con la clase de riesgo, el sector, el tamaño y la geografía; estructura temporal y estacionalidad; detección y tratamiento de valores atípicos; y correlación y colinealidad entre los predictores candidatos. Acompañar cada hallazgo con la visualización que lo sustenta y cierre con la síntesis de lo que condiciona el modelado.

---

## 1.2.2 – Análisis Univariado (resultados preliminares)

> Generado a partir de `01-analisis_univariado/analisis_univariado.py` · 5 000 empresas · 39 894 siniestros · 2018–2024.

---

### A. Frecuencia de Siniestros

**A1 – Número de siniestros por empresa**
![Histograma frecuencia + Q-Q vs Poisson](imgs/01_A1_frecuencia_siniestros_empresa.png)

- La distribución del conteo de siniestros por empresa es **fuertemente asimétrica positiva** (cola larga derecha): la mayoría de empresas registra pocos eventos, mientras un pequeño grupo acumula muchos.
- El Q-Q contra una distribución Poisson muestra desviaciones sistemáticas en la cola superior, evidenciando **sobredispersión** — condición favorable para modelos Binomial Negativa o hurdle/zero-inflated en S03.

**A2 – Tasa de siniestros por 100 trabajadores**
![Frecuencia relativa por clase de riesgo](imgs/01_A2_frecuencia_relativa_clase_riesgo.png)

- La frecuencia relativa también exhibe asimetría importante. Al segmentar por clase de riesgo, la **separación de distribuciones es notoria**: las clases 4 y 5 desplazan la moda hacia tasas más altas, confirmando que `clase_riesgo` es un predictor fuerte.
- Un **7.5% de empresas** no registró ningún siniestro en el periodo, lo cual deberá tratarse en el modelado (modelos de conteo con componente de ceros).

**A3 – Evolución temporal anual**
![Volumen anual de siniestros](imgs/01_A3_frecuencia_anual_temporal.png)

- El volumen de siniestros se mantiene relativamente estable año a año, sin una tendencia creciente o decreciente pronunciada, lo que sugiere que el portafolio es estacionario en primer orden. **Implicación para modelado:** las features de año calendario pueden tener baja contribución marginal.

---

### B. Severidad (días de incapacidad)

**B1 – Distribución de días de incapacidad**
![Distribución severidad + log + CDF](imgs/01_B1_severidad_dias_incapacidad.png)

- **Mediana: 6 días. P90: 37 días. Asimetría: 10.42** → distribución extremadamente leptocúrtica con cola derecha pesada.
- La transformación logarítmica produce una distribución aproximadamente simétrica, confirmando que la variable se debe modelar en escala log (familia Gamma o Lognormal).
- La CDF muestra que el 90% de siniestros genera 37 días o menos de incapacidad, pero la cola restante concentra carga desproporcionada.

**B2 – Severidad por tipo de siniestro (AT vs EL)**
![Severidad AT vs EL](imgs/01_B2_severidad_por_tipo.png)

- Las **Enfermedades Laborales (EL)** presentan distribuciones de severidad con media y cola superior significativamente más altas que los **Accidentes de Trabajo (AT)**. Esta diferencia estructural exige modelos separados de severidad (S03).

**B3 – Boxplot por nivel de gravedad**
![Boxplot severidad por gravedad](imgs/01_B3_boxplot_severidad_gravedad.png)

- La variable `gravedad` discrimina correctamente los días de incapacidad: medianas crecientes de leve → mortal. No obstante, la varianza intra-grupo es alta, especialmente en categorías moderado y grave — confirma la necesidad de features adicionales más allá de la gravedad.

---

### C. Costos

**C1 – Distribución de costos por siniestro**
![Distribución costos por componente](imgs/01_C1_distribucion_costos_siniestro.png)

- **Mediana del costo total por siniestro: $1,272,000 COP. P90: $7,232,000 COP.**
- Tanto el costo asistencial como las prestaciones económicas exhiben distribuciones log-normales, con colas muy pesadas. La transformación `log(1+x)` normaliza satisfactoriamente ambas variables.
- **Implicación:** el resultado técnico del portafolio depende desproporcionadamente de una fracción pequeña de siniestros costosos (candidatos a manejo separado como "eventos catastróficos" en S03).

**C2 – Costo acumulado por empresa**
![Costo acumulado por empresa](imgs/01_C2_costo_acumulado_empresa.png)

- La distribución del costo acumulado por empresa es también fuertemente sesgada. La versión logarítmica es razonablemente simétrica, apta para regresión estándar.

**C3 – Concentración de costos (Curva de Lorenz)**
![Curva de Lorenz – costos](imgs/01_C3_lorenz_concentracion_costos.png)

- **Gini ≈ 0.702** → concentración muy alta de costos.
- El **top 10% de empresas** concentra el **56.5% del costo total** del portafolio. Esto implica que las estrategias de prevención focalizadas en el decil superior tienen un retorno potencial enorme.
- **Implicación para el negocio (S03/S04):** el modelo debe poder identificar correctamente ese decil crítico — la métrica prioritaria no debe ser accuracy global sino Recall/Precisión en el extremo superior.

---

### D. Tamaño de las Empresas

**D1 – Distribución del número de trabajadores**
![Distribución de tamaño de empresas](imgs/01_D1_distribucion_n_trabajadores.png)

- La distribución de `n_trabajadores` es **bimodal en escala natural** con fuerte sesgo positivo. El logaritmo revela una distribución aproximadamente unimodal.
- Segmentación por tamaño del portafolio:
  - **Micro (≤10 trab.):** ~12% de empresas
  - **Pequeñas/Medianas (11-200 trab.):** ~86.4% de empresas ← segmento dominante
  - **Grandes (>200 trab.):** ~1.6% de empresas
- El portafolio está **dominado por PyMEs**, lo que es un dato crítico para el diseño del sistema de recomendación (S05): las recomendaciones deben ser aplicables a empresas con pocos recursos.

**D2 – Prima anual**
![Prima anual por empresa](imgs/01_D2_prima_anual_empresa.png)

- La prima anual también exhibe alta asimetría. La correlación esperada entre `prima_anual`, `n_trabajadores` y `clase_riesgo` se verificará en el análisis bivariado (1.2.3). Posible proxy del riesgo total asumido por la ARL.

**D3 – Antigüedad por clase de riesgo**
![Antigüedad por clase de riesgo](imgs/01_D3_antiguedad_clase_riesgo.png)

- La distribución de antigüedad es relativamente homogénea entre clases de riesgo, sin una diferencia sistemática clara. No se evidencia sesgo de selección por antigüedad asociado al riesgo.

---

### E. Variables Categóricas

**E1 – Tipo de siniestro**
![Tipo de siniestro](imgs/01_E1_tipo_siniestro.png)

- Predominio de **AT (Accidentes de Trabajo)** sobre EL, lo cual es consistente con el perfil de un portafolio PyME industrial.

**E2 – Gravedad**
![Gravedad del siniestro](imgs/01_E2_gravedad_siniestro.png)

- La categoría **"leve"** es la más frecuente, seguida por "moderado". Los eventos graves y mortales son poco frecuentes pero concentran costos desproporcionados — confirma necesidad de modelar la cola derecha.

**E3 – Sector económico**
![Empresas por sector](imgs/01_E3_empresas_por_sector.png)

- El portafolio tiene representación diversa por sector. Los sectores con mayor número de empresas serán analizados en detalle en el análisis bivariado para identificar si la exposición al riesgo difiere significativamente entre ellos.

---

## Síntesis preliminar (tras univariado)

| Hallazgo | Implicación para S03 / S04 / S05 |
|---|---|
| Frecuencia sobredispersa, 7.5% de ceros | Modelo Binomial Negativa o Zero-Inflated Poisson |
| `clase_riesgo` separa claramente distribuciones | Feature crítico; incluir en todos los modelos |
| Costos log-normales con cola pesada | Modelar severidad en escala log (Gamma / Lognormal) |
| Gini costos ≈ 0.70; top 10% = 56.5% del costo | Recall en el decil superior es la métrica de negocio central |
| PyMEs dominan (86.4%) | Recomendaciones deben ser factibles para empresas con recursos limitados |
| Asimetría severidad = 10.42 | Transformación log obligatoria; winsorizar outliers extremos |
| AT y EL tienen distribuciones distintas | Modelos de severidad separados por tipo de siniestro |

---

## 1.2.3 – Análisis Bivariado (resultados preliminares)

> Generado a partir de `02-analisis_bivariado/analisis_bivariado.py` · Panel completo de 5 000 empresas (incluye ceros) · Exploración descriptiva (sin pruebas formales; estas se abordan en S01-1.3).

---

### A. Siniestralidad × Clase de riesgo

**A1 – Boxplots de frecuencia, costo y severidad**
![Siniestralidad por clase de riesgo](imgs/02_A1_siniestralidad_por_clase_riesgo.png)

- Gradiente monotónico claro en las tres métricas: a mayor clase ARL, mayor frecuencia relativa, mayor costo acumulado y mayor severidad media.

**A2 – Medianas por clase**
![Gradiente de medianas](imgs/02_A2_gradiente_mediana_clase_riesgo.png)

| Clase | n empresas | Freq.×100 (mediana) | Costo acum. (mediana) | Severidad (mediana) |
|---|---|---|---|---|
| 1 | 1 322 | 5.6 | $1.7M | 6.2 días |
| 2 | 950 | 10.3 | $4.2M | 8.0 días |
| 3 | 1 001 | 17.5 | $10.4M | 10.5 días |
| 4 | 1 056 | 26.5 | $21.2M | 13.3 días |
| 5 | 671 | 38.7 | $41.6M | 17.0 días |

- La frecuencia mediana de la **clase 5 es 6.9× la de la clase 1**.

**A3 – Participación del costo del portafolio**
![Share de costo por clase](imgs/02_A3_share_costo_clase_riesgo.png)

- Las clases **4 y 5 concentran ~73.3% del costo total** del portafolio (34.6% + 38.8%), pese a representar solo el 34.5% de las empresas.
- **Implicación:** priorizar prevención y modelado en clases altas maximiza impacto económico.

---

### B. Siniestralidad × Sector económico

**B1 – Frecuencia relativa por sector**
![Frecuencia por sector](imgs/02_B1_frecuencia_por_sector.png)

- **Top 5 (mayor frecuencia mediana):** Construcción (36.0), Minería (33.3), Energía (30.2), Manufactura (27.1), Transporte (25.3).
- **Bottom 5 (menor frecuencia):** TIC (5.9), Financiero (6.1), Inmobiliario (6.5), Servicios profesionales (7.1), Educación (9.8).
- El spread top/bottom es ~6× — el sector aparece como predictor de primer orden, comparable en magnitud a la clase de riesgo.

**B2 – Costo acumulado por sector**
![Costo por sector](imgs/02_B2_costo_por_sector.png)

- El ranking de costos sigue el de frecuencia en sectores industriales, con matices: algunos sectores de frecuencia media pueden tener costos elevados por severidad o tamaño medio.

**B3 – Interacción sector × clase de riesgo**
![Heatmap sector × clase](imgs/02_B3_heatmap_sector_clase_riesgo.png)

- Dentro de cada sector el gradiente por clase se mantiene; los sectores de alto riesgo base (Construcción, Minería) alcanzan frecuencias extremas en clases 4–5.
- **Implicación para S02/S03:** modelar interacción `sector × clase_riesgo` o estratificar; no asumir aditividad perfecta.

---

### C. Siniestralidad × Tamaño

**C1 – Scatter tamaño vs siniestralidad**
![Scatter tamaño](imgs/02_C1_scatter_tamano_siniestralidad.png)

- El conteo absoluto de siniestros crece con `n_trabajadores` (efecto de exposición).
- La frecuencia relativa muestra patrón inverso leve: las microempresas tienden a tasas más altas (posible efecto de denominador pequeño / mayor volatilidad).

**C2 – Boxplots por segmento**
![Boxplot segmento](imgs/02_C2_boxplot_segmento_tamano.png)

| Segmento | n | Freq.×100 (med) | n siniestros (med) | Costo (med) |
|---|---|---|---|---|
| Micro (≤10) | 598 | 25.0 | 2 | $2.1M |
| Pequeña (11–50) | 2 961 | 15.4 | 4 | $5.9M |
| Mediana (51–200) | 1 359 | 13.4 | 11 | $22.5M |
| Grande (>200) | 82 | 12.4 | 38 | $76.2M |

- El **costo y el conteo crecen con el tamaño**; la **tasa relativa es mayor en micro**. Para modelado de frecuencia relativa, el tamaño actúa como control/offset, no como driver lineal positivo.

**C3 – Prima vs costo**
![Prima vs costo](imgs/02_C3_scatter_prima_vs_costo.png)

- La prima anual se alinea visualmente con el costo acumulado de siniestros (proxy de exposición + riesgo tarifado).
- Útil como feature o baseline de pricing en S02/S03; vigilar colinealidad con `n_trabajadores` y `clase_riesgo`.

---

### D. Siniestralidad × Geografía

**D1 – Por departamento**
![Siniestralidad por departamento](imgs/02_D1_siniestralidad_por_departamento.png)

- Rango de medianas entre departamentos: **solo 2.9 puntos** de frecuencia×100 — efecto geográfico **débil en magnitud práctica**.
- Atlántico lidera en frecuencia y costo medianos; Santander en el extremo inferior.

**D2 – Por ciudad**
![Siniestralidad por ciudad](imgs/02_D2_siniestralidad_por_ciudad.png)

- Resultados idénticos al departamento: en este dataset sintético hay **mapeo 1:1 ciudad–departamento** (7 ciudades / 7 departamentos). No aporta señal adicional.

**D3 – Mix de clase de riesgo por departamento**
![Composición clase por depto](imgs/02_D3_composicion_clase_por_departamento.png)

- La composición de clases de riesgo es similar entre departamentos → las pequeñas diferencias geográficas **no se explican por un mix de riesgo muy distinto**.
- **Implicación:** geografía es candidata secundaria/control; priorizar clase y sector en el feature set.

---

### E. Matriz de correlación descriptiva

**E1 – Predictores numéricos vs siniestralidad**
![Heatmap correlación](imgs/02_E1_heatmap_correlacion_predictores.png)

| Par | Correlación por rangos | Lectura descriptiva |
|---|---|---|
| `clase_riesgo` ~ `frecuencia_x100` | ~0.73 | Asociación fuerte; predictor dominante |
| `prima_anual` ~ `costo_total_empresa` | ~0.80 | Proxy fuerte de carga |
| `n_trabajadores` ~ `n_siniestros` | ~0.60 | Efecto de exposición |
| `n_trabajadores` ~ `frecuencia_x100` | ~−0.16 | Débil / inverso |
| `antiguedad_meses` ~ métricas | ≈ 0 | Baja relevancia bivariada |

> Las pruebas formales de estas asociaciones se realizarán en **S01-1.3**.

---

## Síntesis bivariada y condicionantes para el modelado

| Hallazgo | Implicación para S02 / S03 / S04 / S05 |
|---|---|
| Gradiente claro por `clase_riesgo`; clases 4–5 = 73% del costo | Feature obligatorio; posible estratificación o pesos por clase |
| Sector discrimina ~6× entre extremos (Construcción vs TIC) | Incluir `sector` (o embedding CIIU); explorar interacción con clase |
| Tamaño ↑ conteo y costo; ↓ levemente la tasa relativa | Usar offset/exposición (`n_trabajadores`) en modelos de conteo; no confundir tasa con volumen |
| Prima alineada con costo acumulado | Buen proxy / baseline; chequear VIF vs tamaño y clase |
| Geografía: rango de medianas ~3 pts | Feature de baja prioridad; evitar sobreajustar con dummies geográficas |
| Panel completo en staging (`empresa_siniestralidad_completa`) | Usar este dataset (no el de solo siniestros) para modelado con ceros |

---

*Análisis realizado con `sura_brand` · Sección S01-1.2 EDA · Prueba Técnica Grupo SURA.*
