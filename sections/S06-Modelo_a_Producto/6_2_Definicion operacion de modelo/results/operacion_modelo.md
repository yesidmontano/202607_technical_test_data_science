### **S06: De modelo a producto**
Objetivo: Paso de modelo a producto


---

### **Requerimiento 6.2**
Definir la operación del modelo en el tiempo: monitoreo de desempeño y de deriva de datos y de concepto, mecanismo de detección y alertamiento, política y disparadores de reentrenamiento, y el gobierno del ciclo de vida mediante el versionamiento de datos, código y modelo, con trazabilidad y reproducibilidad.

---

#### 6.2.1 Operación del modelo Nowcast y Asistente RAG en producción 

1. Monitoreo de desempeño

Para el nowcast, como se ejecuta bajo demanda en Azure ML (batch), haría un seguimiento de cada corrida: MAE, RMSE y MAPE frente al valor observado cuando ya esté disponible el trimestre, y también revisaría si los intervalos de incertidumbre se comportan bien. Los resultados los dejaría visibles en un dashboard (por ejemplo Power BI) para que negocio pueda ver cómo viene el modelo trimestre a trimestre.

Para el asistente RAG, al ser un web service, monitorearía latencia, tasa de error y calidad de las respuestas. En calidad me enfocaría en si responde con citas, si alucina poco y si el usuario encuentra útil la respuesta (feedback simple de thumbs up/down o revisión periódica de una muestra).

2. Monitoreo de deriva (datos y concepto)

En el nowcast usaría Azure ML para detectar cambios en las features (distribución de indicadores, AT parcial, rezagos) respecto al período con el que se entrenó. Si los datos de entrada se mueven mucho, es una señal temprana de que el modelo puede degradarse. La deriva de concepto la vería cuando el error empieza a subir de forma sostenida aunque los datos “se vean bien”: por ejemplo, si cambia la relación entre ciclo económico y siniestralidad.

En el RAG, la deriva no es solo numérica: también importa si el corpus se queda viejo, si llegan documentos nuevos o si las preguntas de los usuarios se alejan de lo indexado. Ahí monitorearía cobertura del retrieval (si encuentra fragmentos relevantes) y calidad de citas.

3. Detección y alertamiento

Definiría umbrales claros y alertas por correo o Teams (o el canal que use la organización). Ejemplos: si el error del nowcast supera un tope acordado con negocio, si Azure ML marca drift alto en features clave, o si el servicio RAG sube mucho la latencia / falla en respuestas. La idea no es alertar por todo, sino por señales que sí ameriten revisar o reentrenar.

4. Política y disparadores de reentrenamiento

Para el nowcast no reentrenaría en automático cada semana: el dato es trimestral y el modelo se usa bajo demanda. Lo reentrenaría cuando (a) llegue información nueva suficiente del trimestre o del siguiente ciclo de datos, (b) el monitoreo muestre deterioro claro de métricas, o (c) cambie de forma relevante el information set (nuevas fuentes, cambios de rezago, etc.). El reentrenamiento lo haría en Azure ML (o Databricks si el volumen lo pide), validaría contra un holdout temporal, y solo promovería la nueva versión en el Model Registry si mejora o al menos no empeora lo que ya hay en producción.

Para el RAG, el “reentrenamiento” en la práctica es más bien reindexar / actualizar el corpus y, cuando haga falta, ajustar prompts o el pipeline de LangChain. Disparadores: documentos nuevos o actualizados en el Data Lake, baja en calidad de respuestas, o cambios de modelo/embedding en Azure AI Foundry. El despliegue seguiría siendo el contenedor del web service, con versión nueva solo después de una evaluación básica (RAG triad o set de preguntas de control).

5. Gobierno del ciclo de vida (versionamiento, trazabilidad y reproducibilidad)

Mantendría tres líneas de versionamiento alineadas con lo de 6.1:

- Datos: datasets y features versionados (Fabric / Feature Store) y corpus documental en ADLS con control de qué versión se usó en cada corrida o indexación.
- Código: repositorio con el pipeline y el servicio dockerizado; cada despliegue apunta a un commit concreto.
- Modelo: Azure ML Model Registry con MLflow, para saber qué versión del nowcast (y con qué datos/features) se usó en cada predicción.

Así, si negocio pregunta “¿con qué modelo salió este nowcast?” o “¿qué documentos usó el asistente esa semana?”, se puede responder. La reproducibilidad viene de amarrar datos + código + modelo en cada ejecución, no de dejarlo solo en notebooks sueltos.
