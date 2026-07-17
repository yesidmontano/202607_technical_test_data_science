# Log de Uso de IA – S02 / 2.1.1
## Listado de fuentes del DANE para el ciclo del sector construcción

---

### 1. Modelo(s) utilizado(s)

- **Gemini Deep Research** (investigación primaria y síntesis de fuentes DANE)
- **NotebookLM** (organización temática y generación de infografía HTML)

---

### 2. Por qué se usó

Se utilizó **Gemini Deep Research** porque la tarea requería un rastreo sistemático y profundo de las operaciones estadísticas activas del DANE relacionadas con el sector construcción, incluyendo documentación técnica oficial (fichas metodológicas, boletines, catálogo de microdatos) que no es fácilmente sintetizable sin capacidades de búsqueda extendida y análisis de múltiples fuentes primarias.

**NotebookLM** se empleó como herramienta complementaria para organizar los hallazgos de Deep Research en una estructura temática cohesiva y generar la infografía interactiva (`01_research.html`) que resume visualmente las cinco fuentes y sus interrelaciones de ciclo.

---

### 3. Qué se tomó

| Elemento | Origen | Nivel de modificación |
|---|---|---|
| Caracterización de las 5 fuentes (ELIC, CEED, IPOC, ICOCED, EC) | Deep Research | Síntesis editorial — se reorganizó y condensó el texto original en formato tabular y descripción estructurada por fuente |
| Tabla comparativa (frecuencia, rezago, fase del ciclo, unidad de medida) | Deep Research | Adoptada directamente con ajustes menores de formato Markdown |
| Diagrama de interacciones temporales entre fuentes | Deep Research | Traducido a notación ASCII para el documento de resultados |
| Sección del boletín IEAC como fuente de síntesis | Deep Research | Incorporada con edición mínima |
| Infografía PNG (`01_infografia_DANE.png`) | NotebookLM | Generada por la herramienta como imagen estática PNG; revisada y validada conceptualmente |

El documento de investigación completo está en:
`sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/resources/deep_research_DANE.md`

---

### 4. Qué se descartó o requirió corrección manual

- **Fórmulas matemáticas en formato imagen:** El informe de Deep Research incluye ecuaciones embebidas como imágenes base64 (fórmula de deflación del IPOC con ICOCIV, fórmula del INI). Estas **no se trasladaron** al resumen de `caracterizacion.md` por no ser renderizables en Markdown estándar; se describe el procedimiento en lenguaje natural en su lugar.
- **Referencias bibliográficas numeradas:** El informe original usa un sistema de citación numerado (44 fuentes). En el resumen se consolidaron únicamente las URLs primarias de cada operación estadística para mantener el documento limpio y operativo.
- **Tablas de ponderación ICCV vs. ICOCED:** Se mencionan los cambios clave (incorporación del 21,9% de servicios especializados) pero no se reproduce la tabla completa de pesos, disponible en el documento de recursos.

---

### 5. Lecciones y advertencias relevantes

- **Revisiones retrospectivas en ELIC:** Las series de licencias son frecuentemente revisadas hasta 2+ meses después de su publicación inicial por radicación extemporánea. Cualquier integración de la ELIC en modelos predictivos debe contemplar versiones "vintage" de los datos, no solo la serie más reciente.
- **Cifras provisionales en EC:** Los datos de concreto premezclado son provisionales por 2 años. Usar la serie de concreto como variable coincidente requiere aceptar este nivel de revisabilidad.
- **IPOC vs. IIOC:** El IPOC (vigente) mide ejecución física real; el IIOC (discontinuado) medía flujos financieros. No son comparables retroactivamente sin corrección metodológica.
- **INI como proxy de calidad:** El Índice de No Imputación del ICOCED es un indicador de calidad publicado mensualmente. Valores por debajo del 97% deben generar alertas sobre la representatividad del índice de costos en ese mes.
- **IEAC como punto de entrada:** Para análisis de coyuntura, el boletín IEAC trimestral del DANE es el documento más eficiente; consolida en un solo lugar las 14 series relevantes con interpretación sectorial integrada.
