### **S05: Sistema de recomendación de servicios**
Objetivo: El área quiere recomendar a cada empresa los servicios de prevención con mayor probabilidad de ser adoptados y de reducir su riesgo. Dispone del histórico de uso en uso_servicios.csv, de los atributos de los servicios en catalogo_servicios.csv y de los atributos de las empresas en empresas.csv, que en conjunto permiten construir el recomendador y resolver el arranque en frío de empresas sin histórico.

---

### **Requerimiento 5.3**
Proponer cómo llevaría el sistema a producción y cómo mediría su impacto real de negocio.

---

#### Paso a producción

Desde mi experiencia, para pasar el sistema de recomendación a producción utilizaría Fabric y Azure ML: 

Fabric para almacenamiento de los datos (datasets de uso_servicios, catalogo, empresas, etc) y el pipeline de extracción de sus fuentes. También agregaría un pipeline que transforme estos datos a un feature store. 

En Azure ML, registraría el modelo, para versiónamiento, control de data drift, y evaluación de predicción. Este modelo lo despliego como un batch endpoint que se ejecutaría de forma programada (esto podría hacerse con un DAG de airflow u otro servicio).

Para la medición del impacto del modelo diseñado experimento A/B con grupos de control para medir el impacto o efecto real de las decisiones tomadas con el recomendador. Esto requiere una conversación y coordinación con el área de negocio. Los resultados los pondría en un Power BI, para hacer un seguimiento del desempeño del sistema.

