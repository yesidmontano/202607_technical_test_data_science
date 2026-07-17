### **S02: Modelación económica y sectorial del sector construcción**
 Objetivo: El sector construcción es uno de los de mayor accidentalidad y mayor sensibilidad al ciclo económico. La Dirección quiere anticipar la siniestralidad del sector a partir de su ciclo. El candidato debe combinar el panel sintético de macro_sectorial.csv con series públicas del DANE que él mismo debe identificar. Esta sección es el eje de la prueba y exige rigor econométrico, criterio de fuentes y un componente de soporte documental.

---

### **Requerimiento 2.3**
Producir un nowcast de la frecuencia de accidentes de trabajo del trimestre en curso combinando la siniestralidad parcial observada con los indicadores líderes, considerando de forma explícita los distintos rezagos de publicación de las fuentes. Reportar la incertidumbre del nowcast.

---

### 2.3.1 Revisión de estado del arte.
Posterior a la revisión del estado del arte en relación a modelos nowcast de siniestralidad en el sector construcción, se encontró lo siguiente:

El documento 'sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/resources/estado_del_arte.md' presenta una revisión exhaustiva sobre el uso de modelos de nowcasting para predecir la siniestralidad en la construcción, vinculando directamente la seguridad laboral con las fluctuaciones del ciclo económico. La tesis central sostiene que los accidentes son pro-cíclicos, aumentando en periodos de auge debido a la fatiga, la contratación de personal inexperto y la aceleración de la producción, mientras que las recesiones suelen mostrar una baja estadística influenciada por el miedo al reporte y la retención de trabajadores veteranos. Para superar los retrasos en las estadísticas oficiales, el texto explora diversas metodologías que van desde la econometría tradicional, como los Modelos de Factores Dinámicos, hasta innovaciones en Inteligencia Artificial y Series Temporales Bayesianas que permiten una selección automática de variables. En última instancia, la fuente busca proporcionar a la industria aseguradora herramientas para una gestión de riesgos proactiva, optimizando el cálculo de reservas y permitiendo una tarificación dinámica basada en indicadores de alta frecuencia como el empleo y el consumo de materiales.

A partir de esto entrenaremos los siguientes modelos:
1. Modelos de Machine Learning: Random Forest
2. Modelos Econometricos y de Series temporales: BSTS y DFM.