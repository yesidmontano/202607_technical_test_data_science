### **S01: Formulación, análisis exploratorio y fundamentos estadísticos**
Objetivo: El negocio quiere anticipar qué empresas tendrán alta siniestralidad el próximo año para focalizar la prevención.

---

### **Requerimiento 1.1**
Enmarcar el problema con la metodología CRISP-DM: Explicar qué haría en las fases de comprensión de negocio y comprensión de los datos para este caso. Formular el problema analítico con unidad de análisis, variable objetivo y su definión operativa, esquema de validación y métricas de éxito frente a una línea base, e identifique los riesgos de fuga de información presentes en estos datos.

### **CRISP-DM**

#### **1. Comprensión del negocio**

Para la fase de comprensión de negocio hay un conjunto de preguntas que me enfocaria en responder, abajo especifico como abordaría cada una:

1. **Cuál es el problema principal que la empresa está intentando resolver?**
Esto ya nos lo especifica la descripción de la sección 1, el objetivo para este caso es *anticipar qué empresas tendrán alta siniestralidad el próximo año para focalizar la prevención*. En un contexto real, separaría espacio con el área o stakeholders a las cuáles esta información les aporta valor e intentaría cuantificar el impacto de esta información en sus procesos, así los accionables que tomarían con ella.

2. **Existen objetivos comerciales o estrategicos especificos de la empresa atados a este problema?**
En el mismo espacio de la pregunta 1, me enfocaría en entender como se alínea este proyecto con los objetivos comerciales y estratégicos de la empresa. Ejemplo, reducir costos, aumentar la retención de clientes, aumentar la rentabilidad, etc. Esto debido que 'focalizar la prevención' no es un objetivo en sí mismo.

3. **Cómo mediriamos el éxito del proyecto?**
Es clave definir con los stakeholders las métricas que se usariamos para medir el éxito del proyecto, al igual que la metodologia de medición de estas métricas. Por lo general , para este tipo de proyectos suelo enfocarme en métricas de negocio (ROI, reducción de costos, etc.) y métricas técnicas (Precisión, Recall, F1-Score, etc.), para tener la perspectiva desde ambos frentes.

4. **Cuál es la situacion actual con respecto al problema?**
En este espacio buscaria entender el contexto del problema, como se abordan actualmente las decisiones relacionadas a este, qué herramientas tecnologicas y humanas estan disponibles, cuáles son los riesgos, restricciones o requisitos legales en relación con la politica de privacidad de datos, y qué supuestos de negocio estamos asumiendo como ciertos, entre otros.

5. **Cómo traducimos el problema a objetivos de ciencia de datos?**
En este punto con la información anterior, traduciría el problema a un problema de ciencia de datos y sus métricas técnicas de éxito. En este caso particular, el problema es predecir qué empresas presentarán alta siniestralidad el próximo año, lo que técnicamente se traduce a un problema de clasificación donde la variable objetivo es binaria: 1 si la empresa presentará alta siniestralidad y 0 en caso contrario. 

6. **Plan de trabajo**
Por último traduciría todo lo anterior a un plan de trabajo. Algo similar al que estoy usando para desarrollar esta prueba técnica (ver [Plan de trabajo](https://docs.google.com/spreadsheets/d/1bRKRcoZ_dMUjZsmecg4rygDzyv3yOo4bhVnY-VOMmGg/edit?usp=sharing)


#### **2. Comprensión de los datos**

En la fase de comprensión de los datos, también hay un conjunto de preguntas y procesos que realizo:

1.  **Recopilación de datos inicial**
Verifico que datos y fuentes de datos tenemos disponibles, y como se conectan o relacionan estas fuentes entre si.

2. **Volumetría y descripción de los datos**
Cuantifico cuantos datos tenemos disponibles (filas, columnas, temporalidad, tipos de archivos, etc). Valido o creo el diccionario de datos correspondiente a los datos disponibles.

3. **EDA: Análisis exploratorio de los datos**
Realizo un análisis exploratorio de los datos para entender su estructura, distribución, relaciones entre variables, etc. Con esto puedo tener una mejor comprensión del problema y los datos, y puedo identificar patrones o anomalías que me puedan ser útiles para el análisis.

4. **Calidad de los datos**
Cuantifico los datos faltantes y qué fenómeno los explica, analizo los outliers e inconsistencias en los datos. Por ultimo, vería que datos tienen riesgo de data leakage al ejecutar la inferencia.


### **Ejecución**

#### **Formulación de problema analítico**

- **Problema**: Diseñar un modelo de clasificación binaria que permita predecir qué empresas presentarán alta siniestralidad el próximo año.

- **Unidad de análisis**: Empresas, identificadas por el campo id_empresa.

- **Variable objetivo (y)**: Variable binaria definida como 1 si la empresa presentará alta siniestralidad en el próximo año, y 0 en caso contrario.

- **Definición operativa de 'Alta siniestralidad'**: Top 10% de las empresas con mayor número de siniestros.

- **Esquema de validación**: Se utilizará un esquema de validación temporal, donde se dividirán los datos en entrenamiento y prueba basándose en la fecha. Específicamente, se entrenará el modelo con los datos hasta el año T-1 y se validará con los datos del año T. Esto permitirá evaluar el rendimiento del modelo en datos no vistos y simular un escenario de producción real. Adicionalmente, se utilizará una validación cruzada temporal para obtener una estimación más robusta del rendimiento del modelo.

- **Métricas de éxito**: Las métricas de éxito se dividirán en métricas de negocio y métricas técnicas.

    - **Métricas técnicas**: 
        - *Área bajo la curva ROC (AUC-ROC)*: Esta métrica evalúa la capacidad del modelo para distinguir entre clases positivas y negativas. Un valor de 1 indica un clasificador perfecto, mientras que un valor de 0.5 indica un clasificador aleatorio.
        - *Sensibilidad (Recall)*: Mide la capacidad del modelo para identificar correctamente las empresas que presentarán alta siniestralidad.
        - *Precisión*: Mide la capacidad del modelo para identificar correctamente las empresas que presentarán alta siniestralidad.
        - *F1-Score*: Esta métrica es la media armónica de la precisión y la sensibilidad. 
    
    - **Métricas de negocio**: 
        - *Reducción de costos*: La reducción de costos se medirá como el costo evitado en seguros por la reducción en la tasa de siniestros en las empresas que presentarán alta siniestralidad, debido a la priorización en la intervención. 
        - *Porcentaje de mejora*: Calcular el porcentaje de mejora en la tasa de siniestros en comparación con la línea base.

- **Baseline (Línea base)**: La línea base para este caso será un modelo que predice el mismo top 10% de empresas del año anterior.

- **Riesgos de fuga de información (Data Leakage)**: El principal riesgo de fuga de información es que se utilicen los datos de prueba (del futuro) de los siniestros en el entrenamiento del modelo.











