# Log de Uso de IA – S02 / 2.3.1
## Revisión del estado del arte en modelos de nowcasting para el sector construcción

---

### 1. Modelo(s) utilizado(s)

- **NotebookLM** (Gemini 1.5 Pro como motor subyacente para el procesamiento y estructuración de múltiples documentos de referencia)

---

### 2. Por qué se usó

Se utilizó **NotebookLM** porque la tarea requería consolidar una gran cantidad de literatura científica y técnica de diversas fuentes (documentos de trabajo del Banco Central Europeo, FMI, estudios actuariales y papers de machine learning/econometría aplicados) en relación a modelos de nowcasting de siniestralidad, pro-ciclicidad económica en el sector construcción e implicaciones actuariales. NotebookLM facilita la ingestión masiva de documentos, organizando y extrayendo síntesis precisas con citas referenciales cruzadas de forma eficiente.

---

### 3. Qué se tomó

| Elemento | Origen | Nivel de modificación |
|---|---|---|
| Revisión teórica de los mecanismos de pro-ciclicidad (intensificación de trabajo, tenencia, sesgo de reporte) | NotebookLM | Síntesis editorial — se organizó y estructuró con subtítulos, citas cruzadas y tabla resumen para mayor claridad teórica. |
| Caracterización de indicadores de alta frecuencia (PIB, empleo, visados, alternativos) | NotebookLM | Adoptado y adaptado para formato tabular estructurado en el documento final. |
| Comparativa metodológica de modelos econométricos (DFM, VAR, BSTS) y de Machine Learning (XGBoost, Random Forest, Deep Learning) | NotebookLM | Modificación media — se ordenaron los modelos en tablas comparativas estructurando ventajas, desventajas y métricas de desempeño documentadas. |
| Aplicación en gestión actuarial y reservas IBNR | NotebookLM | Adaptación e integración con el lenguaje del negocio de seguros (como la tarificación dinámica y el factor EMR). |
| Infografía del estado del arte (`01_infografia_estado_arte.png`) | NotebookLM | Imagen generada por la herramienta que resume la interacción de los modelos; se validó conceptualmente y se guardó en la ruta de resultados de imágenes. |

El documento consolidado de revisión está en:
[estado_del_arte.md](file:///Users/yesidmontano/Development/202607_technical_test_data_science/sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/resources/estado_del_arte.md)

---

### 4. Qué se descartó o requirió corrección manual

- **Formulación matemática excesiva de estimaciones MCMC:** Se simplificaron los detalles excesivamente teóricos del muestreador de Gibbs en los modelos Bayesian Structural Time Series (BSTS) para mantener el enfoque del negocio en el prior *spike-and-slab* y la modularidad del modelo.
- **Detalles hiperespecíficos de leyes de presunción regional:** Se redujeron los análisis sobre directrices legislativas de COVID-19 en California que no aplican a la caracterización nacional o al contexto local del reto.
- **Normalización de formatos de referencias:** NotebookLM generó 65 referencias cruzadas con URLs de soporte. Se validó manualmente que los enlaces fueran funcionales y correspondieran a los documentos reales (como el paper de Varian sobre BSTS, reportes de NYCIRB y WCIRB).

---

### 5. Lecciones y advertencias relevantes

- **Dualidad del ciclo y siniestralidad:** En expansiones, el incremento en siniestros es físico (fatiga, novatos, jornadas largas), pero en recesiones hay un riesgo de subestimación debido al infrarreporte por miedo al despido, mezclado con un posible pico de reclamaciones de "trauma acumulado" previas a despidos masivos. El nowcast debe ser sensible a este sesgo.
- **Modularidad del modelo BSTS:** El prior *spike-and-slab* en los modelos Bayesianos estructurales es el estándar de oro del nowcasting en Big Data con datos macro mixtos, ya que selecciona automáticamente variables relevantes y descompone las series de tiempo de forma transparente para los tomadores de decisiones de negocio.
- **Brecha entre ML y Econometría en Nowcast:** Los modelos de ML (ej. XGBoost, RF) son excelentes clasificadores de riesgo individual y severidad a nivel micro (proyectos), pero los modelos econométricos y de series temporales (como BSTS y DFM) son esenciales para nowcast de reservas técnicas (IBNR) y tendencias macro.
- **Actualización dinámica de reservas IBNR:** Utilizar el ciclo macroeconómico coincidente y adelantado permite al actuario corregir el método clásico de *Chain Ladder* durante giros inesperados de la actividad económica, evitando déficit de capital técnico.
