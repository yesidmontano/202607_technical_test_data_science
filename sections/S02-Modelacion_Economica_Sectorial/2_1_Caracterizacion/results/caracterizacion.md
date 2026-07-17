### **Requerimiento**
Caracterizar el ciclo del sector construcción. Identificar y justificar al menos tres series públicas del DANE pertinentes para el ciclo del sector y construya con ellas un indicador líder. Discutir el rezago de publicación de cada fuente y su implicación para el análisis

---

## 2.1.1 Listado de fuentes del DANE pertinentes para el ciclo del sector construcción

> **Referencia completa de la investigación:** `sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/resources/deep_research_DANE.md`
> **Infografía:** `sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/results/imgs/01_infografia_DANE.png`
El DANE cuenta con cinco operaciones estadísticas activas que permiten seguir el ciclo del sector constructor colombiano desde la intención formal hasta la ejecución física, pasando por costos e insumos. Cada fuente captura una fase distinta del ciclo y opera con frecuencias y rezagos diferenciados que deben considerarse al integrar series de tiempo.
---
### Tabla resumen de fuentes
| Operación Estadística | Sigla | Tipo | Frecuencia | Rezago | Fase del Ciclo | Indicador principal |
|---|---|---|---|---|---|---|
| Estadísticas de Licencias de Construcción | **ELIC** | Censo / Registro administrativo | Mensual | ~45 días | **Líder** – Expectativa / Intención formal | m² de área aprobada; unidades de vivienda VIS / No VIS |
| Censo de Edificaciones | **CEED** | Censo de cobertura geográfica | Trimestral | ~45 días | **Coincidente** – Ejecución física en edificación | m² área causada, iniciada y culminada |
| Indicador de Producción de Obras Civiles | **IPOC** | Encuesta de muestra de contratos | Trimestral | 45–50 días | **Coincidente** – Ejecución de infraestructura pesada | Índice de producción real por tipología CPC v2.1 |
| Índice de Costos de la Construcción de Edificaciones | **ICOCED** | Índice de precios de entrada | Mensual | ~25–28 días | **Precios de insumos** – Costos de entrada | Variación % de costos: materiales, mano de obra, maquinaria, servicios especializados |
| Estadísticas de Concreto Premezclado | **EC** | Censo de productores especializados | Mensual | 35–40 días | **Coincidente** – Abastecimiento físico inmediato | Miles de m³ de concreto despachado por destino |
---
### Descripción de cada fuente
#### 1. ELIC – Estadísticas de Licencias de Construcción
- **Rol en el ciclo:** Indicador **líder**. Registra la intención formal de construcción a través de los actos administrativos aprobados por los curadores urbanos. Una variación positiva sostenida en área licenciada anticipa con 6 a 18 meses de rezago un incremento en obras iniciadas (CEED).
- **Cobertura geográfica:** 1.104 municipios (desde enero 2024, incorporando Nuevo Belén de Bajirá).
- **Nota metodológica clave:** Las series sufren revisiones retrospectivas frecuentes por radicación extemporánea de licencias físicas. La categorización VIS fue ajustada en agosto 2019 (tope de 135 a 150 SMMLV en municipios CONPES 3819/2014).
- **Fuente DANE:** https://www.dane.gov.co/index.php/estadisticas-por-tema/construccion/licencias-de-construccion
#### 2. CEED – Censo de Edificaciones
- **Rol en el ciclo:** Indicador **coincidente** de ejecución real en terreno (contrasta con las expectativas de la ELIC). El indicador estructural es el **área causada** (m² efectivamente construidos en el trimestre).
- **Cobertura geográfica:** 91 municipios prioritarios (ampliado en mayo 2022 con 25 nuevos municipios).
- **Control de calidad:** Cálculo diario de indicadores de calidad operativa por responsable de proceso; validación de consistencia en campo.
- **Fuente DANE:** https://www.dane.gov.co/index.php/estadisticas-por-tema/construccion/censo-de-edificaciones
#### 3. IPOC – Indicador de Producción de Obras Civiles
- **Rol en el ciclo:** Mide la evolución trimestral de la **infraestructura pesada** (carreteras, puentes, tuberías, puertos, energía, hidráulica) a partir del avance técnico físico efectivo reportado por contratistas. Reemplazó al antiguo IIOC (que medía flujos presupuestales, no ejecución real).
- **Deflación:** Utiliza el ICOCIV (Índice de Costos de Obras Civiles, publicación mensual) para convertir valores nominales a precios constantes; el DANE trimestraliza el ICOCIV promediando los tres meses del trimestre.
- **Validación institucional:** Comité Interno DANE + Comité Externo (gremios, academia, gobierno) convocado 3 días hábiles antes de la difusión.
- **Fuente DANE:** https://www.dane.gov.co/index.php/estadisticas-por-tema/construccion/indicador-de-produccion-de-obras-civiles-ipoc
#### 4. ICOCED – Índice de Costos de la Construcción de Edificaciones
- **Rol en el ciclo:** Mide la **variación de precios de los insumos** de edificación formal en 10 destinos constructivos (vs. 3 del antiguo ICCV). Es el índice de referencia para reajuste de contratos civiles.
- **Renovación metodológica (2022):** El DANE retiró en 2019 la certificación de calidad al ICCV por más de 10 años sin actualizar la canasta (incumplía estándares OCDE/FMI). La nueva canasta ICOCED incorpora **Servicios Especializados con ponderador del 21,9%** (subcontratistas de redes eléctricas, hidráulicas y acabados), antes no contemplados.
- **Calidad del dato:** El **Índice de No Imputación (INI)** mide la proporción de precios recolectados efectivamente vs. imputados. Un INI ≥ 98,9% (típico en publicaciones maduras) garantiza menos del 1,1% de datos estimados.
- **Cobertura:** 57 municipios de recolección; publicación en 10 destinos constructivos.
- **Fuente DANE:** https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-costos-de-la-construccion-de-edificaciones-icoced
#### 5. EC – Estadísticas de Concreto Premezclado
- **Rol en el ciclo:** Sensor físico de **reacción más rápida**. El concreto no es almacenable (debe verterse de inmediato), por lo que sus despachos mensuales reflejan en tiempo real la intensidad de la fase de cimentación y estructura, permitiendo anticipar la variable "área causada" del CEED antes de la publicación trimestral.
- **Cifras provisionales:** Las series operan como **provisionales durante 2 años** antes de consolidarse como definitivas (margen para capturar nuevas empresas que ingresan al directorio muestral).
- **Ampliación (junio 2021):** Se incorporó la medición de concreto destinado a obras civiles, además de edificaciones.
- **Fuente DANE:** https://www.dane.gov.co/index.php/component/content/article/1831-guia-de-las-operaciones-estadisticas
---
### Fuente de síntesis: Boletín IEAC
El DANE consolida el diagnóstico del sector en el boletín **Indicadores Económicos Alrededor de la Construcción (IEAC)**, publicación trimestral que integra 14 investigaciones estadísticas internas y externas en cuatro ejes: **macroeconomía** (PIB, empleo), **oferta** (CEED, ELIC), **demanda** (créditos de vivienda) y **precios** (ICOCED, ICOCIV, IPP, índice de precios de vivienda nueva). Es el principal insumo de diagnóstico para ministerios, gremios y analistas.
- **Boletín más reciente consultado:** IV Trim 2025 (publicado marzo 2026)
- **URL:** https://www.dane.gov.co/files/operaciones/IEAC/bol-IEAC-IVtrim2025.pdf
---
### Interacciones clave entre fuentes (dinámicas de transmisión temporal)
```
ELIC (Mensual) ──[6–18 meses]──▶ CEED área iniciada/causada (Trimestral)
                                       ▲
EC (Mensual, despachos concreto) ──────┘  [anticipación coincidente]
ICOCED (Mensual, costos insumos) ──▶ Deflación / Reajuste contractual
IPOC (Trimestral) + ICOCIV (Mensual deflactor) ──▶ Producción real en infraestructura
```
- Un alza sostenida en ELIC (área licenciada) predice expansión futura en CEED (área causada) con retardo de 6–18 meses.
- Un incremento mensual en EC (concreto despachado) anticipa aceleración en el valor agregado constructor antes de que el PIB trimestral sea publicado.
- El ICOCED sirve de base para cláusulas de reajuste de precios en licitaciones de largo aliento, con soporte jurídico del INI.
