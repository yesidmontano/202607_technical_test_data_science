# Resumen Ejecutivo — Sección S06: De Modelo a Producto

> **Prueba Técnica · Grupo SURA · Dirección de Analítica**  
> Secciones cubiertas: 6.1 Arquitectura de producción · 6.2 Operación del modelo

---

## 1. Encuadre

Se lleva a producto corporativo (Azure + Databricks/Fabric) el par **Nowcast DFM** (S02-2.3) + **Asistente RAG** (S02-2.4): arquitectura punta a punta y operación en el tiempo (monitoreo, drift, reentrenamiento, gobierno).

| Elemento | Definición |
|---|---|
| **Productos** | Nowcast (señal macro → siniestralidad) · Asistente RAG (consulta documental + tool nowcast) |
| **Stack** | Fabric / ADLS · Databricks (orquestación, Feature Store, AI Search) · Azure ML · Azure AI Foundry |
| **Serving** | Nowcast = **batch on-demand** · RAG = **web service** (Docker) |
| **Origen analítico** | DFM 1F + puente OLS (MAPE≈6.6%) · prototipo RAG en `apps/Asistente_RAG` |
| **Referencias** | `arquitectura_producto.md` · `operacion_modelo.md` (AGENTS #17–18) |

---

## 2. Arquitectura de producción (6.1)

| Capa | Decisión | Justificación |
|---|---|---|
| **Ingesta** | Fabric (estructurado) + ADLS (no estructurado/RAG) · orquestación Databricks Workflows (Spark / Auto Loader) | Un solo plano de datos; evita Airflow externo |
| **Features / vectores** | Databricks Feature Store · Databricks AI Search (reemplaza Chroma) | Versionado, aislamiento y escala corporativa |
| **Train / registry** | Azure ML + MLflow Registry (Databricks notebooks solo si volumen extremo) | Control de versiones y promoción a prod |
| **RAG stack prod** | LangChain + Azure AI Foundry (LLM + embeddings) | Sale de ADK/Gemini del prototipo hacia stack Azure |
| **Despliegue Nowcast** | Batch Azure ML **bajo demanda** | Uso trimestral / on-demand, no cron fijo |
| **Despliegue RAG** | Web service Azure (repo dockerizado) | Latencia interactiva y despliegue rápido |

---

## 3. Operación en el tiempo (6.2)

### Desempeño

| Producto | Qué se monitorea | Visibilidad |
|---|---|---|
| **Nowcast** | MAE / RMSE / MAPE vs valor observado al cerrar trimestre · calibración de IC | Power BI (trimestre a trimestre) |
| **RAG** | Latencia · tasa de error · citas · alucinaciones · feedback (👍/👎) / muestra periódica | Observabilidad del servicio |

### Deriva

| Producto | Datos | Concepto |
|---|---|---|
| **Nowcast** | Drift de features (indicadores, AT parcial, rezagos) vía Azure ML | Error sostenido aunque inputs “se vean bien” (cambia ciclo ↔ siniestralidad) |
| **RAG** | Corpus desactualizado / docs nuevos / preguntas fuera de cobertura | Baja cobertura de retrieval y calidad de citas |

### Alertas y reentrenamiento

Alertas solo ante señales accionables (correo/Teams): error Nowcast sobre umbral de negocio, drift alto en features clave, latencia/fallos RAG.

| Producto | Disparadores | Promoción |
|---|---|---|
| **Nowcast** | (a) dato nuevo suficiente del ciclo · (b) deterioro claro de métricas · (c) cambio del information set | Holdout temporal → Registry solo si no empeora prod |
| **RAG** | Docs nuevos en ADLS · baja calidad · cambio LLM/embedding Foundry | Reindex / ajuste pipeline; eval RAG Triad o set de control antes de nueva imagen |

### Gobierno

Tres líneas amarradas por corrida: **datos** (Fabric / Feature Store + corpus ADLS) · **código** (commit + imagen Docker) · **modelo** (Azure ML Registry / MLflow). Responde “¿con qué modelo salió este nowcast?” y “¿qué documentos usó el asistente?”.

---

## 4. Mensaje para Dirección

El Nowcast y el Asistente RAG pasan de prototipo a producto Azure con roles claros: **batch on-demand** para la señal trimestral y **servicio web** para la consulta. La operación no es reentrenar por calendario, sino **monitorear error y drift**, alertar con umbrales de negocio y promover versiones solo con evidencia (métricas + holdout / RAG Triad) y trazabilidad datos–código–modelo.

---

## 5. Artefactos clave

| Ruta | Contenido |
|---|---|
| `sections/S06-.../6_1_.../arquitectura_producto.md` | Arquitectura (ref. AGENTS #17) |
| `sections/S06-.../6_2_.../operacion_modelo.md` | Operación (ref. AGENTS #18) |
| `sections/S02-.../2_3_.../nowcast.md` | Modelo DFM origen (ref. AGENTS #6) |
| `sections/S02-.../2_4_.../asistente_rag.md` | Prototipo RAG origen (ref. AGENTS #7) |
| `apps/Asistente_RAG/` | Implementación local del asistente |
