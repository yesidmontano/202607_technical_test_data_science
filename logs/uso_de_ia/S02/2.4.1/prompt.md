Ayudame a construir la arquitectura para una aplicación de Asistente RAG documental. Esta aplicación se almacenará en apps/Asistente_RAG. Utilzaremos Google ADK como framework, Chromdb como memoria vector store y de persistencia, y streamlit para frontend. 

Componentes: 
- Interfaz de carga de documentos pdf, con función de embedding automático mediante modelo Gemini Embeddings 2. 
- Interfaz de chat de respuesta a preguntas con citas y link a los documentos.
- Integración de modelo nowcast (ver sección 2.3) DFM para predicción

Genera flujo de ingestión de documentos, flujograma de respuesta a preguntas y flujo de integración del modelo nowcast. 

Metodologia de evaluación:
- Componente de RAG Triad para evaluación de calidad (a nivel de traces y E2E), utilizando las funciones predefinidas en ADK.



Transversal: 
1. Guarda la definición de esta arquitectura en sections/S02-Modelacion_Economica_Sectorial/2_4_Asistente RAG/results/asistente_rag.md, para mi revisión.
2. Diligencia logs/uso_de_ia/S02/2.4.1/output.md como logs del proceso que realizaste.
