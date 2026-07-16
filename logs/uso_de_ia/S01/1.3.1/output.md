# Registro de Uso de IA — 1.3.1

## Modelo utilizado
Claude Sonnet 4.6 (Thinking)

## Por qué se usó
Se necesitaba un análisis crítico de los resultados del EDA (secciones 1.2.2–1.2.6) para identificar qué hallazgos descriptivos permanecen como preguntas abiertas que requieren validación estadística formal en S01-1.3. La tarea exigía distinguir entre hallazgos ya concluyentes visualmente y aquellos donde la incertidumbre estadística justifica una prueba de hipótesis.

## Qué se tomó
Listado completo de 12 preguntas abiertas con justificación, generado íntegramente a partir del contenido del `Insights_EDA.md`. Se tomó sin modificaciones. La clasificación en 4 categorías de impacto (arquitectura de modelo, feature set, confirmación/descarte) fue producida por el modelo y se considera correcta.

## Qué se descartó o requirió corrección manual
- No se descartó ninguna pregunta; el listado fue aceptado en su totalidad.
- Se decidió **no solicitar** el análisis completo (H0/H1/test/resultado esperado) en esta iteración — eso corresponde a la implementación en `code/` de S01-1.3.

## Lecciones y advertencias relevantes
- Las preguntas P1 y P2 (sobredispersión y exceso de ceros) son **dependientes**: si P1 se rechaza (no hay sobredispersión), P2 pierde sentido. Ejecutar en orden.
- P10 (retención Top 10%) es la prueba con mayor impacto en la narrativa de negocio: el lift de 50% vs 10% esperado por azar es el argumento central para el feature `log_lag_n_siniestros` en S03.
- P8 (estacionalidad) y P11 (geografía) son pruebas de **confirmación de nulidad**: el objetivo es *no* rechazar H0. Diseñarlas con potencia suficiente para que el resultado negativo sea creíble.

---

## Listado de preguntas abiertas que ameritan prueba de hipótesis

### I. Distribución de la frecuencia

**P1 – ¿El conteo de siniestros exhibe sobredispersión real o es artefacto muestral?**
El EDA muestra que el Q-Q vs Poisson se desvía sistemáticamente en la cola, y la varianza supera la media. La decisión de usar Binomial Negativa en S03 debe estar respaldada por un test formal, no solo por inspección visual.

**P2 – ¿El 7.5% de ceros es excesivo respecto a lo esperado por Binomial Negativa?**
Un exceso de ceros *más allá* de la sobredispersión justificaría un modelo Zero-Inflated (ZIP/ZINB) en lugar de NB estándar. El EDA no puede distinguir entre estos dos escenarios sin un test de exceso de ceros.

---

### II. Efectos de predictores estructurales

**P3 – ¿Las medianas de frecuencia relativa difieren significativamente entre las 5 clases de riesgo?**
El gradiente visual es claro (clase 1: 5.6 × 100 vs clase 5: 38.7 × 100), pero una prueba formal confirma si las diferencias entre clases *adyacentes* (e.g., clase 2 vs 3) son estadísticamente distinguibles o si solo los extremos difieren — información crítica para decidir si tratar `clase_riesgo` como ordinal continua o como factor con grupos colapsables.

**P4 – ¿El sector económico tiene un efecto significativo sobre la frecuencia, más allá de la clase de riesgo?**
El EDA muestra un spread de ~6× entre Construcción y TIC. La pregunta es si ese efecto persiste *controlando* por clase de riesgo, o si el sector es simplemente un proxy de la clase. Esto determina si `sector` aporta señal incremental al modelo.

**P5 – ¿Existe interacción significativa entre sector y clase de riesgo sobre la frecuencia?**
El heatmap sector × clase (1.2.3-B3) sugiere que el gradiente por clase no es uniforme entre sectores. Formalizarlo define si se deben modelar interacciones o si la aditividad es suficiente.

---

### III. Diferencias por tipo de siniestro

**P6 – ¿La severidad media (días de incapacidad) de las EL es significativamente mayor que la de los AT?**
El boxplot (1.2.2-B2) muestra diferencia visual clara, pero dada la asimetría extrema (skewness 10.42) la comparación visual es engañosa. Un test no paramétrico formal (Mann-Whitney) es necesario para respaldar la decisión de modelos separados AT vs EL en S03.

---

### IV. Tamaño y efecto de exposición

**P7 – ¿Las microempresas (≤10 trabajadores) tienen una tasa de siniestralidad significativamente mayor que los demás segmentos?**
El EDA sugiere que la tasa *relativa* es más alta en micro (25.0 × 100) pero con mucha varianza y denominador pequeño. Un test formal permite separar si el efecto es real o artefacto estadístico del denominador — lo que define si el segmento merece tratamiento especial en S05.

---

### V. Estructura temporal

**P8 – ¿Existe estacionalidad mensual significativa en el volumen de siniestros?**
El índice estacional muestra amplitud de solo ±2%, pero eso podría ser suficiente para un test formal dado el tamaño muestral (~39k siniestros). La conclusión del EDA es "no invertir en componentes estacionales"; confirmar estadísticamente que la variación entre meses *no es distinguible del ruido* solidifica esa recomendación para S02/S03.

**P9 – ¿La persistencia del conteo de siniestros año t → t+1 (ρ ≈ 0.70) es significativamente mayor que cero?**
Es el fundamento del `log_lag_n_siniestros` como feature obligatorio. Un test de autocorrelación formal (Spearman o Ljung-Box en panel) convierte una correlación descriptiva en evidencia estadística para incluir el lag en S03.

**P10 – ¿La retención del Top 10% entre años consecutivos (~50%) es significativamente superior a la esperada por azar (~10%)?**
Si la asignación fuera aleatoria, esperaríamos ~10% de retención. El EDA observa ~50%. Un test binomial formal cuantifica el lift y refuerza la utilidad predictiva del historial — argumento clave para justificar el diseño del recomendador en S05 y la estrategia causal en S04.

---

### VI. Geografía

**P11 – ¿Las frecuencias medianas entre departamentos son estadísticamente distintas?**
El EDA reporta un rango de apenas ~3 puntos entre departamentos, lo que *sugiere* efecto nulo, pero no lo confirma. Un test formal de Kruskal-Wallis sobre los 7 departamentos permite cerrar definitivamente la pregunta y justificar la decisión de descartarlo como predictor principal en S03/S05.

---

### VII. Bondad de ajuste distribucional

**P12 – ¿Los costos log-transformados siguen suficientemente una distribución Normal/Lognormal para justificar la familia Gamma o Lognormal en el modelo de severidad?**
El EDA muestra que `log(costo)` se ve "aproximadamente simétrico", pero con n ≈ 39k un test de bondad de ajuste (Kolmogorov-Smirnov o Anderson-Darling) revelará si los extremos de la cola aún violan los supuestos, lo que podría orientar hacia Gamma sobre Lognormal o viceversa.

---

**Resumen: 12 preguntas — 4 con impacto en decisiones de arquitectura de modelo (P1, P2, P4, P6), 5 con impacto en el feature set (P3, P5, P7, P9, P10), 3 de confirmación/descarte (P8, P11, P12).**
