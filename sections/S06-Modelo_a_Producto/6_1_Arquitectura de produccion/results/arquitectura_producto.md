### **S06: De modelo a producto**
Objetivo: Paso de modelo a producto


---

### **Requerimiento 6.1**
Elegir uno de los modelos anteriores y describir la arquitectura de puesta en producción de punta a punta: ingesta y preparación de datos, cómputo de features, entrenamiento, validación, empaquetado, despliegue como proceso batch o como servicio, y entrega de las predicciones al negocio. Asumir un stack en la nube corporativo sobre Azure y Databricks y justifique cada decisión.

---

#### 6.1.1 Arquitectura para el modelo Nowcast y el Asistente RAG 

1. Ingesta y preparación de los datos

Para la ingesta y preparación de los datos utilizaría una conbinación de Fabric (para datos estructurados y preparación) y Azure Data Lake Storage (para datos no estructurados y retrieval de RAG). Utilizaría Databricks workflow (Spark y Auto loaders) para la orquestación de estos procesos, esto para no utilizar un servicio externo como airflow. 

2. Computo de features

Utilizaría Databricks Feature Store para almacenar y versionar las features y Databricks AI Search como vector store en reemplazo de chromadb. Para mantener sistema de datos aislado y fácil de escalar.

3. Entrenamiento, tuning y evaluación

Todo el entrenamiento tuning, y modelado lo haría desde Azure Machine Leanrning, solo en caso de que estemos en frente de muchos (pero muchos datos), obtaría por utilizar los Notebooks de databricks, con spark.
Nota: En producción es muy importante el versionamiento y control de los modelos, por lo que utilizaría Azure ML Model Registry con mlflow.

En cuanto al asistente RAG, cambiaría el framework ADK por langchain, y la api del modelo a Azure AI foundry (tanto el LLM como el embedding).


4. Desppliegue

El nowcast lo despliegue como batch en Azure ML. Esto porque es un modelo que se ejecuta bajo demanda (no de manera programada).

El despliegue del asistente RAG, lo haría como un web service en azure.  Con el repo dockerizado, estaría listo para uso de forma rápida.




