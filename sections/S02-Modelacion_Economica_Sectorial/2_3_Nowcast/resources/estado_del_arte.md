# Estado del Arte en Modelos de Nowcasting para la Predicción de Accidentalidad en el Sector Construcción: Un Enfoque Basado en Indicadores del Ciclo Económico

## La Intersección entre Macroeconomía y Seguridad Operacional en la Industria del Seguro

La industria aseguradora global atraviesa un periodo de redefinición analítica, impulsado por la necesidad de mitigar la incertidumbre en sectores de alta siniestralidad como la construcción. En este contexto, el *nowcasting* —la capacidad de predecir las condiciones presentes o del futuro inmediato utilizando datos de alta frecuencia— ha emergido como una herramienta indispensable para la gestión de riesgos y la solvencia financiera [1, 2, 3]. La construcción es, por naturaleza, uno de los sectores más peligrosos, con una incidencia desproporcionada de lesiones graves y muertes [4, 5]. Solo en Estados Unidos, se reportaron más de mil muertes en sitios de construcción en 2022, lo que representa cerca del 19.5% del total de accidentes fatales en el país [4]. A nivel global, la Organización Internacional del Trabajo (OIT) estima que 374 millones de trabajadores sufren accidentes laborales anualmente, lo que acarrea un costo económico cercano al 4% del Producto Interno Bruto (PIB) mundial [6].

Para las aseguradoras, el desafío radica en que la información oficial sobre accidentalidad suele publicarse con retrasos significativos, a menudo de varios meses o incluso años [7, 8]. Este desfase informativo complica la constitución de reservas para siniestros ocurridos pero no reportados (IBNR) y la tarificación precisa de las pólizas de compensación laboral [9, 10]. Los modelos de nowcasting resuelven esta problemática al explotar la relación intrínseca entre la accidentalidad y el ciclo económico. La evidencia sugiere que la seguridad laboral no es una constante, sino una variable altamente sensible a las fluctuaciones macroeconómicas, mostrando un comportamiento pro-cíclico en la mayoría de las economías desarrolladas y en desarrollo [11, 12, 13].

La capacidad de anticipar picos de siniestralidad mediante indicadores de alta frecuencia como el consumo de energía, las horas trabajadas o los permisos de construcción permite a las aseguradoras no solo proteger sus márgenes financieros, sino también desempeñar un papel proactivo en la prevención de riesgos [14, 15, 16]. Al identificar qué fases del ciclo económico o qué indicadores de actividad están correlacionados con un aumento de los siniestros, las compañías pueden desplegar estrategias de mitigación, como auditorías de seguridad en tiempo real o ajustes en las primas basados en la exposición dinámica al riesgo [15, 17, 18].

---

## Mecanismos Teóricos de la Relación Pro-cíclica

La literatura económica y de seguridad ocupacional ha documentado extensamente que los accidentes laborales tienden a aumentar durante las expansiones económicas y a disminuir durante las recesiones [11, 19, 20, 21]. Este fenómeno, validado por estudios que se remontan a 1938, se explica a través de una serie de mecanismos causales que afectan tanto la oferta como la demanda de trabajo y la cultura de seguridad en las empresas [6, 11].

### Intensificación del Trabajo y Fatiga

Durante los periodos de auge económico, las empresas de construcción se enfrentan a una demanda creciente que a menudo supera su capacidad instalada. Esto conduce a una intensificación de los ritmos de producción, jornadas laborales extendidas y una mayor utilización de la maquinaria [6, 19, 21]. La presión por cumplir con plazos de entrega ajustados en proyectos de gran envergadura suele derivar en niveles elevados de estrés y fatiga entre los trabajadores, lo que reduce la atención a los protocolos de seguridad y aumenta la probabilidad de errores humanos [6, 13, 19]. Se ha observado que en fases de alta utilización de la capacidad, la prioridad por la producción puede desplazar temporalmente las inversiones en seguridad o el mantenimiento preventivo de los equipos [11, 21].

### Dinámica del Mercado Laboral y Tenencia del Puesto

Un factor determinante en la pro-ciclicidad es la composición de la fuerza laboral. En las expansiones, la escasez de mano de obra cualificada obliga a las constructoras a contratar trabajadores con menos experiencia o formación técnica [13, 20, 22]. Los datos actuariales demuestran que la tenencia en el empleo es un predictor crítico: los trabajadores con menos de un mes de antigüedad en su puesto tienen tasas de reclamaciones hasta tres veces superiores a las de aquellos con más de un año de experiencia [20]. Además, durante los periodos de crecimiento, la rotación laboral aumenta, lo que interrumpe la continuidad de los equipos y diluye la transferencia de conocimientos sobre riesgos específicos del sitio de obra [20, 22].

En contraste, durante las recesiones, el fenómeno se invierte. Las empresas tienden a despedir primero a los trabajadores menos experimentados o con contratos temporales, reteniendo a su personal más veterano y capacitado [20, 23]. Esto genera una mejora "estadística" en las tasas de seguridad del sector, no necesariamente porque las condiciones físicas hayan cambiado, sino porque la composición de la mano de obra se ha vuelto más resiliente al riesgo [20, 23].

### El Sesgo del Reporte y Vulnerabilidad Económica

Existe un componente psicológico y social que influye en los datos de siniestralidad. Durante las crisis económicas, los trabajadores suelen experimentar una mayor inseguridad laboral y miedo al despido. Diversas investigaciones sugieren que esta vulnerabilidad reduce la disposición de los empleados a reportar accidentes menores por temor a ser considerados "problemáticos" o prescindibles durante los recortes de personal [6, 20]. Este infrarreporte distorsiona la frecuencia de siniestros a la baja en periodos de declive, un efecto que las aseguradoras deben considerar al calibrar sus modelos para evitar una percepción errónea de la seguridad real en los proyectos [6, 20].

| Factor | Efecto en Expansión | Efecto en Recesión | Impacto en Siniestralidad |
|---|---|---|---|
| Ritmo de Trabajo | Acelerado para cumplir plazos | Desacelerado / Normal | Mayor fatiga y errores en expansión [6, 19] |
| Experiencia Laboral | Entrada masiva de novatos | Retención de expertos | Mayor frecuencia de accidentes en expansión [20, 22] |
| Mantenimiento | Postergado por uso intensivo | Riguroso por baja demanda | Fallos de equipo más comunes en expansión [11, 21] |
| Disposición al Reporte | Alta (seguridad laboral) | Baja (miedo al despido) | Subestimación de riesgos en recesión [6, 20] |

---

## Indicadores del Ciclo Económico como Predictores de Alta Frecuencia

El éxito de un modelo de nowcasting depende de la selección de variables que no solo estén correlacionadas con la accidentalidad, sino que se publiquen con mayor frecuencia y celeridad que las estadísticas de siniestros. La literatura actual identifica varios clústeres de indicadores que capturan diferentes facetas del ciclo económico.

### El PIB y el Valor Agregado del Sector

El Producto Interno Bruto (PIB) es el indicador macroeconómico más robusto para predecir la tendencia general de los accidentes. En España, se ha determinado que un cambio del 1% en la tasa de crecimiento del PIB puede provocar una variación de hasta ocho puntos en la tasa de incidencia estandarizada de accidentes laborales [11]. En economías de crecimiento rápido como la de China, las fatalidades ocupacionales están positivamente relacionadas con el valor agregado de la industria secundaria y la inversión en infraestructura [11, 12]. Sin embargo, la limitación del PIB es su frecuencia trimestral, lo que obliga a los modelos de nowcasting a utilizar indicadores *proxy* mensuales o incluso diarios para captar giros repentinos en la actividad [1, 24].

### Indicadores del Mercado de Trabajo y Horas Totales

La tasa de desempleo y el número de horas trabajadas son fundamentales. Una caída en el desempleo suele preceder a un aumento en la frecuencia de reclamaciones de compensación laboral [20, 21, 25]. No obstante, la relación no es lineal: en sectores específicos como la construcción en California, se ha observado que el aumento de las reclamaciones por "trauma acumulado" puede persistir o incluso aumentar ligeramente al inicio de las recesiones, a medida que los trabajadores reportan lesiones crónicas antes de ser despedidos [23, 26]. Las nóminas del sector construcción y el índice de trabajadores con baja antigüedad son quizás los predictores más directos de la exposición al riesgo en tiempo real [22, 27, 28].

### Indicadores Líderes de Actividad Inmobiliaria y de Infraestructura

Los visados de obra nueva, el inicio de construcción de viviendas y el consumo de cemento o acero actúan como indicadores líderes que señalan la carga de trabajo futura [11, 29]. En Corea del Sur, el inicio de construcciones de edificios se ha validado como un componente significativo en los modelos de predicción de lesiones y muertes mensuales [11]. Estos indicadores son vitales para las aseguradoras de riesgos de ingeniería (*Builder's Risk*), ya que permiten anticipar la fase de mayor riesgo de un proyecto (generalmente las fases iniciales y estructurales) [5, 30].

### Variables Financieras y de Confianza

Las tasas de interés, los índices bursátiles del sector (como el Dow Jones Construction & Materials) y las encuestas de confianza empresarial (PMI) ofrecen una visión sobre las expectativas futuras de inversión [29, 31, 32]. Un entorno de tasas de interés al alza suele enfriar la inversión en construcción, lo que eventualmente reduce la frecuencia de siniestros por la disminución de la actividad, aunque puede aumentar la presión sobre los costos de los siniestros existentes debido a la inflación social y de materiales [25, 31, 32].

| Tipo de Indicador | Ejemplos Específicos | Frecuencia | Mecanismo |
|---|---|---|---|
| Macroeconómico | PIB real, PIB sectorial | Trimestral | Volumen de actividad general [6, 11, 33] |
| Laboral | Tasa de desempleo, Horas totales | Mensual | Exposición y experiencia del trabajador [20, 25, 28] |
| Sectorial | Visados, Inicio de viviendas | Mensual | Indicador adelantado de riesgo en sitio [11, 29] |
| Financiero | Tasas de interés, SP500 | Diario | Capacidad de inversión y seguridad [21, 25, 32] |
| Alternativo | Consumo energía, Google Trends | Diario/Semanal | Actividad real y búsqueda de subsidios [12, 34, 35] |

---

## Metodología del Estado del Arte: Modelos Econométricos de Nowcasting

Los modelos econométricos tradicionales han evolucionado para manejar la naturaleza compleja de los datos de ahora: frecuencias mixtas, muestras incompletas al final del periodo (el *ragged-edge problem*) y fuertes dependencias temporales [1, 24, 36].

### Modelos de Factores Dinámicos (DFM)

El DFM es la arquitectura predominante en instituciones como el Banco Central Europeo y la Reserva Federal para el monitoreo de ciclos económicos en tiempo real [1, 37]. Su lógica se basa en que una gran cantidad de indicadores (como el empleo, la producción industrial y el consumo de energía) comparten una dinámica común impulsada por un pequeño número de factores latentes que representan el estado no observado de la economía [37, 38, 39].

En el contexto de la siniestralidad, los DFM permiten integrar, por ejemplo, los informes de accidentes anuales o trimestrales con indicadores mensuales de empleo. Mediante el uso del Filtro de Kalman, el modelo estima continuamente el factor de riesgo latente del sector construcción, actualizando la predicción cada vez que se publica un nuevo dato económico [24, 36, 40].

- **Resultados:** Los DFM han demostrado ser extremadamente robustos durante periodos de crisis. Durante la pandemia de COVID-19, las versiones de estos modelos que incluían ajustes por volatilidad estocástica superaron significativamente a los modelos autorregresivos tradicionales, reduciendo el error de predicción en un 50% en varias economías europeas [41, 42, 43].
- **Pros:** Manejo eficiente de cientos de variables; tratamiento estadístico riguroso de datos faltantes; capacidad de descomponer la revisión del pronóstico en "noticias" (*news decomposition*) de indicadores específicos [1, 37].
- **Contras:** Requieren una estructura de datos estable y son complejos de implementar; la interpretación de los factores latentes puede ser menos intuitiva para gestores no técnicos [44, 45].

### Modelos de Vectores Autorregresivos (VAR y Panel VAR)

Los modelos VAR se utilizan para capturar las interdependencias bidireccionales entre el crecimiento económico y los accidentes. En un estudio que analizó 40 estados de EE. UU., se confirmó una relación causal bidireccional en el corto plazo: el PIB por trabajador afecta la tasa de accidentes, pero los accidentes también tienen un impacto negativo en la productividad y el desempeño empresarial futuro [6].

- **Resultados:** Se ha verificado que la relación es heterogénea entre regiones; los estados con una estructura industrial más pesada en construcción muestran una mayor sensibilidad de los siniestros a las variaciones del PIB [6].
- **Pros:** Permiten realizar análisis de respuesta al impulso (*impulse-response*) para ver cuánto tiempo persiste un aumento de la siniestralidad tras un choque económico [6].
- **Contras:** Sufren de la "maldición de la dimensionalidad" si se incluyen demasiadas variables, lo que puede llevar a predicciones inestables [44, 45].

### Ecuaciones Puente (*Bridge Equations*)

Son modelos más sencillos que actúan como un "puente" entre los indicadores de alta frecuencia (mensuales) y la variable objetivo de baja frecuencia (trimestral). Se utilizan frecuentemente como un primer paso antes de pasar a modelos más complejos [1].

- **Pros:** Gran simplicidad y facilidad de comunicación; útiles cuando la relación entre un indicador específico (como las horas trabajadas) y los accidentes es muy directa [1, 45].
- **Contras:** No capturan de manera óptima las interacciones dinámicas globales del ciclo económico [1].

### Series Temporales Estructurales Bayesianas (BSTS)

El modelo BSTS ha ganado popularidad recientemente en el sector financiero y de seguros por su capacidad para manejar la incertidumbre y realizar una selección automática de variables en entornos de *Big Data* [34, 44, 46].

#### Mecanismo de Funcionamiento y Spike-and-Slab

A diferencia de los modelos frecuentistas, el BSTS utiliza un enfoque Bayesiano para promediar miles de modelos posibles. Su componente de regresión emplea una técnica denominada *prior* de pico y losa (*spike-and-slab*), que asigna una probabilidad a cada indicador de ser relevante para la predicción [34, 44, 47]. Si un indicador del ciclo económico (por ejemplo, la tasa de inflación de materiales de construcción) no aporta poder predictivo, el modelo lo elimina automáticamente (lo pone en el "pico" de probabilidad cero), dejando solo los conductores más potentes (la "losa") [34, 47, 48].

#### Modularidad y Transparencia

Una ventaja clave del BSTS es su modularidad. El modelo descompone la serie de siniestralidad en:

- **Nivel local:** Representa la tendencia actual.
- **Estacionalidad:** Ajusta los picos típicos de accidentes (por ejemplo, mayores riesgos en meses de calor extremo o lluvia) [48, 49].
- **Regresión:** Incorpora el impacto de los indicadores económicos contemporáneos [34, 44].

- **Resultados:** En aplicaciones para predecir ingresos de mercado y tendencias de salud, el BSTS ha logrado valores de error absoluto medio porcentual (MAPE) de entre el 1% y el 7%, demostrando ser altamente fiable para predecir puntos de inflexión [49].
- **Pros:** Excelente para manejar la incertidumbre; proporciona una atribución directa a indicadores observables, lo que facilita explicar el pronóstico a los suscriptores de seguros; maneja conjuntos de datos donde el número de predictores supera al de observaciones [44, 48].
- **Contras:** La precisión depende de la correcta elección de las distribuciones previas (*priors*), lo que requiere juicio de expertos [44].

---

## Modelos de Aprendizaje Automático y Arquitecturas Híbridas

La frontera del nowcasting se sitúa en el uso de algoritmos de aprendizaje automático (*Machine Learning*, ML) y aprendizaje profundo (*Deep Learning*, DL). Estos modelos son capaces de detectar patrones no lineales que los modelos econométricos tradicionales suelen omitir [50, 51, 52].

### Algoritmos de Clasificación y Regresión

Los modelos de conjunto como Random Forest (RF) y Extreme Gradient Boosting (XGBoost) se han utilizado para predecir tanto la ocurrencia como la severidad de los accidentes en la construcción [50, 53, 54]. En un estudio en Corea del Sur, el modelo Random Forest logró clasificar el riesgo de fatalidad de los trabajadores con una precisión del 91.98% (AUROC), identificando que el mes del año y el tamaño de la empresa son factores determinantes junto con las condiciones del ciclo económico [53].

Por otro lado, XGBoost ha mostrado resultados superiores en la predicción de la severidad de los incidentes (SOI), alcanzando precisiones del 89% en entornos donde se combinaron datos operativos de seguridad con indicadores económicos regionales [50, 51].

### El Uso de SHAP para la Interpretabilidad

Una crítica histórica a los modelos de ML ha sido su naturaleza de "caja negra". Sin embargo, el estado del arte actual incorpora técnicas de explicabilidad como los valores SHAP (*SHapley Additive exPlanations*). Estas herramientas permiten a las aseguradoras ver exactamente cómo un indicador económico específico (como un aumento repentino en la inversión en infraestructura) está empujando el riesgo de siniestralidad hacia arriba en un proyecto dado [4, 50, 52].

### Aprendizaje Profundo y Modelos de Costos Indirectos

Se han desarrollado modelos basados en Redes Neuronales Recurrentes (RNN) y marcos de dos niveles para estimar no solo la ocurrencia del accidente, sino también sus costos indirectos asociados (pérdida de productividad, daños materiales, gastos legales), que a menudo son de 3 a 5 veces superiores a los costos directos cubiertos por el seguro [5, 54, 55]. Un marco de dos niveles que utiliza ML logró precisiones superiores al 87% en la clasificación de costos, reduciendo las desviaciones en las estimaciones presupuestarias para las empresas y sus aseguradoras [54].

| Modelo de ML | Resultado de Precisión | Aplicación Principal | Ventaja |
|---|---|---|---|
| XGBoost | 89% en SOI | Predicción de severidad del incidente | Manejo de datos desbalanceados [50, 51] |
| Random Forest | 91.98% (AUROC) | Clasificación de riesgo de fatalidad | Estabilidad y manejo de valores atípicos [53] |
| Deep Learning | R² de 0.95 | Predicción de pérdidas financieras | Captura patrones no lineales complejos [5, 54] |
| LightGBM | Alta eficiencia en grandes datos | Identificación de factores de riesgo | Velocidad y precisión en datos masivos [52] |
| AutoML | 97.48% (condiciones controladas) | Selección automática de modelos | Optimización del flujo de trabajo [4] |

---

## Aplicación en la Gestión Actuarial y Reservas IBNR

Para la industria aseguradora, el nowcasting tiene una utilidad directa en el cálculo de las reservas y la rentabilidad técnica.

### Reservas IBNR y Retrasos de Reporte

El método tradicional del *Chain Ladder* estima las reservas basándose únicamente en el patrón histórico de pagos [9, 10]. Sin embargo, este método falla cuando el ciclo económico cambia bruscamente. Un modelo de nowcasting integrado permite ajustar los factores de desarrollo de la siniestralidad en tiempo real. Por ejemplo, si los indicadores de ahora muestran una aceleración económica masiva en el sector construcción, el actuario puede anticipar un aumento de la siniestralidad que aún no se refleja en las reclamaciones reportadas, ajustando las reservas IBNR preventivamente para evitar un déficit de capital [2, 10].

Se han propuesto algoritmos de Maximización de Expectativas (EM) que combinan ML con modelos de retraso de reporte, permitiendo a los aseguradores predecir eventos que ya han ocurrido pero que aún no han sido notificados, utilizando covariables específicas de la entidad y del entorno económico contemporáneo [10].

### Tarificación Dinámica y EMR

En seguros de compensación laboral, el Factor de Modificación de la Experiencia (EMR) ajusta la prima basándose en el historial de pérdidas del contratista. Los modelos de ahora permiten a los corredores y suscriptores ir más allá del historial estático y realizar una "suscripción prospectiva" [14, 15, 56]. Si un contratista está expandiendo rápidamente su fuerza laboral en un mercado en auge (indicado por el crecimiento de su nómina y los datos de empleo regional), el modelo de nowcasting puede señalar un aumento inminente del riesgo, permitiendo a la aseguradora ajustar las tasas o requerir medidas de control de riesgos adicionales antes de que los accidentes ocurran [14, 15, 16].

### Reducción de la "Inflación Social"

Swiss Re y Munich Re han destacado que la "inflación social" —el aumento en los costos de los siniestros debido a litigios y cambios en las expectativas de compensación— es una preocupación creciente [18, 31, 32]. Los modelos de nowcasting que incorporan variables de presión económica (inflación, salarios, costos médicos) ayudan a las aseguradoras a proyectar mejor la severidad final de los siniestros abiertos, mejorando la precisión de las reservas de casos individuales (RBNS) [10, 25, 57].

---

## Análisis Regional y Evidencia Empírica Global

La efectividad de los modelos de nowcasting varía según la disponibilidad de datos y la estructura del sector construcción en cada región.

### Estados Unidos: El Índice CFEI de Nueva York

El Consejo de Calificación de Seguros de Compensación de los Trabajadores de Nueva York (NYCIRB) desarrolló el Índice Económico de Frecuencia de Siniestros (CFEI) [22]. Este es un modelo de nowcasting ejemplar que correlaciona fuertemente la frecuencia de siniestros con dos componentes:

- **LTEI (*Low-Tenure Employment Index*):** Mide el volumen de trabajadores nuevos en el mercado.
- **Índice de Exposición:** Mide la nómina total ajustada por salarios.

El CFEI ha demostrado ser un predictor preciso de la frecuencia de siniestros en el sector construcción, demostrando que las fluctuaciones económicas a corto plazo son el principal motor de la volatilidad en las reclamaciones [22].

### California: Impacto del Desempleo y CT Claims

El WCIRB de California utiliza un modelo econométrico para proyectar la frecuencia de siniestros basándose en el pronóstico de la UCLA Anderson y datos del BLS [27, 28, 58]. Sus hallazgos indican que un aumento en la tasa de desempleo tiene una correlación directa con la disminución de la siniestralidad en construcción, aunque advierten que la introducción de leyes de presunción (como las de COVID-19) o el aumento de reclamaciones por "trauma acumulado" (CT) pueden desafiar las tendencias cíclicas tradicionales [23, 26, 59].

### España: Análisis Pro-cíclico y Puntos de Inflexión

En España, el análisis del periodo 1994–2014 reveló que la recuperación económica iniciada en 2014 revirtió una tendencia descendente de 13 años en la siniestralidad laboral [11]. Los modelos aplicados en el caso español han subrayado que la debilidad de los sistemas de prevención se hace más evidente en las fases de crecimiento rápido del PIB, donde la seguridad no escala al mismo ritmo que la actividad productiva [11, 60].

### Asia: Corea y China

En Corea del Sur, la frecuencia de accidentes muestra una relación estadísticamente significativa con la utilización de la capacidad manufacturera [11]. En China, se ha utilizado el modelo Gris de Gauss (*Gaussian Grey Model*) para analizar la correlación entre accidentes y cinco indicadores económicos, descubriendo que la inversión en investigación y educación tiene la correlación negativa más fuerte con la siniestralidad, sugiriendo que el desarrollo económico basado en el conocimiento puede eventualmente desacoplar el crecimiento de los accidentes [12, 13, 61].

---

## Fronteras Tecnológicas: IA Generativa e Internet de las Cosas (IoT)

El estado del arte está incorporando fuentes de datos no tradicionales y nuevas capacidades de procesamiento que están transformando el nowcasting de algo reactivo a algo preventivo en tiempo real.

### IA Generativa y Grandes Modelos de Lenguaje

Investigaciones recientes sugieren que la IA Generativa (como los modelos basados en GPT) puede complementar a los modelos de AutoML en la predicción de accidentes de construcción [4]. Mientras que el AutoML es superior en la precisión predictiva pura sobre datos tabulares (alcanzando el 97.48%), los modelos de IA Generativa son más hábiles para interpretar descripciones textuales de incidentes previos y *near-misses*, proporcionando una mayor robustez en la validación externa y una mejor usabilidad para los gerentes de seguridad en el campo [4].

### IoT, Wearables y Sensores de Sitio

La integración de datos de sensores de IoT integrados en equipos (como grúas), dispositivos *wearables* para trabajadores y cámaras con visión artificial está permitiendo un "nowcasting de micro-escala" [14, 17, 62]. Estos sistemas alimentan algoritmos que detectan condiciones inseguras en tiempo real —como la proximidad a zonas de caída o fatiga del trabajador detectada por sensores biométricos— permitiendo intervenciones inmediatas antes de que el siniestro ocurra [17, 62]. Para la aseguradora, estos datos ofrecen una visibilidad sin precedentes sobre el perfil de riesgo real del asegurado, permitiendo una tarificación mucho más granular [17, 63, 64].

### Análisis de Sentimiento y Google Trends

El uso de *Alternative Data*, como las búsquedas en Google relacionadas con desempleo o subsidios por incapacidad, se ha integrado en modelos BSTS para predecir la frecuencia de reclamaciones semanas antes de que se presenten formalmente [2, 34, 35]. Esta capacidad de "predecir el presente" basándose en el comportamiento digital es vital en situaciones de crisis económica, donde los patrones tradicionales de reclamación pueden romperse [1, 35, 37].

---

## Comparativa Exhaustiva de Modelos: Rendimiento, Ventajas y Desafíos

La elección del modelo depende del objetivo específico de la aseguradora: desde la alta dirección que busca tendencias macro hasta el suscriptor que evalúa un riesgo específico.

| Familia de Modelos | Resultados Destacados | Pros Principales | Contras y Desafíos |
|---|---|---|---|
| Modelos de Factores (DFM) | Capturan el 20% de la variación global mediante *spillovers* financieros [43] | Ideales para monitoreo de ciclo económico general y política de alto nivel [1] | Opacidad en la relación variable-factor; requieren personal altamente técnico [1, 44] |
| BSTS (Bayesianos) | MAPE de 4.0% en predicciones de ingresos y tendencias [49] | Transparencia total; excelente manejo de la incertidumbre y datos ruidosos [44, 48] | Pueden ser computacionalmente costosos (MCMC) para datasets masivos [44] |
| Machine Learning (XGB/RF) | Reducción de incidentes del 50% y de costos del 75% en primer año [15, 16] | Máxima precisión en la identificación de proyectos de alto riesgo [15, 50] | Riesgo de *overfitting*; requieren procesos de limpieza de datos exhaustivos [17, 51] |
| VAR / Panel VAR | Identifican causalidad en 28 de 40 estados analizados [6] | Permiten simular escenarios de "qué pasa si" (choques económicos) [6] | Supuestos de linealidad que pueden no cumplirse en crisis extremas [1, 45] |
| Modelos Híbridos (DL + Econ) | R² de 0.95 en predicción de costos indirectos [54] | Combinan la teoría económica con la potencia de detección del DL [54, 55] | Muy complejos de calibrar y validar para cumplimiento regulatorio [4] |

---

## Conclusiones y Recomendaciones Estratégicas

El estado del arte en modelos de nowcasting para la accidentalidad en la construcción revela una convergencia entre la econometría clásica y la inteligencia artificial. La premisa fundamental de que el ciclo económico dicta el ritmo de los accidentes está hoy más validada que nunca por la evidencia empírica global [6, 11, 12].

Para las instituciones aseguradoras que busquen implementar estas herramientas, se sugieren las siguientes conclusiones y recomendaciones:

1. **Priorizar la selección de variables de alta frecuencia.** El PIB es un buen ancla, pero el verdadero poder del nowcasting reside en indicadores mensuales como las horas trabajadas en construcción, el índice de empleo de baja antigüedad (LTEI) y los visados de obra nueva [11, 22, 27].
2. **Adoptar enfoques bayesianos para la transparencia.** Para la toma de decisiones estratégicas y actuariales, los modelos BSTS ofrecen una ventaja competitiva al permitir la selección automática de variables y una comunicación clara de los conductores del riesgo a las partes interesadas [34, 44, 48].
3. **Utilizar Machine Learning para la gestión operativa.** Los modelos de Gradient Boosting (como XGBoost) deben integrarse en los procesos de suscripción y prevención para identificar los "proyectos estrella" que concentran la mayor probabilidad de accidentes graves, optimizando el despliegue de recursos de ingeniería de riesgos [15, 50, 52].
4. **Considerar la dualidad del ciclo económico.** Es crucial reconocer que el riesgo aumenta en las expansiones por la falta de experiencia y la fatiga, pero también debe vigilarse el infrarreporte en las recesiones y el aumento de las reclamaciones de trauma acumulado al cierre de los ciclos [6, 20, 23].
5. **Invertir en datos propios y tecnologías de sitio.** El futuro del nowcasting está en los datos de *leading indicators* internos (observaciones de seguridad, cuasi-accidentes, datos de telemetría de maquinaria), que al combinarse con los indicadores macroeconómicos, producen los pronósticos más precisos y accionables [14, 17, 65].

La capacidad de "ver el presente" a través del lente de la economía no solo mejora la rentabilidad de las aseguradoras, sino que permite un entorno de construcción más seguro, donde la protección financiera y la vida de los trabajadores están resguardadas por la precisión de los datos.

---

## Referencias

1. Working Paper Series - Nowcasting made easier: a toolbox for economists - European Central Bank. <https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3004~3ce9d0d8ca.en.pdf>
2. Henrique Fernandes Pires. Essays on nowcasting with high dimensional data - PUC Rio. <https://www.econ.puc-rio.br/api/uploads/adm/trabalhos/files/23_mai_2022_1811819_2022_completo.pdf>
3. Macroeconomic Nowcasting and Forecasting with Big Data - ResearchGate. <https://www.researchgate.net/publication/325612519_Macroeconomic_Nowcasting_and_Forecasting_with_Big_Data>
4. Construction Accident Prediction via Generative AI and AutoML Approaches - MDPI. <https://www.mdpi.com/2076-3417/16/5/2412>
5. Predicting financial losses due to apartment construction accidents utilizing deep learning techniques - PMC. <https://pmc.ncbi.nlm.nih.gov/articles/PMC8967902/>
6. The relationship between the economic cycle and work accidents in the United States: A time series analysis - SciELO. <https://www.scielo.sa.cr/scielo.php?script=sci_arttext&pid=S1659-33592023000100001>
7. Nowcasting and monitoring SDG 8 - PMC - NIH. <https://pmc.ncbi.nlm.nih.gov/articles/PMC8890028/>
8. Looking ahead – developments in public sector finance statistics: 2026. <https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance/articles/lookingaheaddevelopmentsinpublicsectorfinancestatistics/2026>
9. Bayesian Nowcasting Data Breach IBNR Incidents | Variance. <https://variancejournal.org/article/133953-bayesian-nowcasting-data-breach-ibnr-incidents>
10. Machine learning in an expectation-maximisation framework for nowcasting - arXiv. <https://arxiv.org/pdf/2512.07335>
11. A systematic review of the relationship between economic growth and occupational accidents - SciELO SA. <https://scielo.org.za/scielo.php?script=sci_arttext&pid=S2222-34362025000100031>
12. Accidents measurement in the investigation of the relationship between... - ResearchGate. <https://www.researchgate.net/figure/Accidents-measurement-in-the-investigation-of-the-relationship-between-the-economic_tbl1_320641532>
13. Analysis of the Correlation between Occupational Accidents and Economic Factors in China. <https://pmc.ncbi.nlm.nih.gov/articles/PMC8535984/>
14. Leveraging Data to Transform Construction Safety & Health - NFP. <https://www.nfp.com/insights/leveraging-data-to-transform-construction-safety-and-health/>
15. How a new safety system aims to predict accidents before they happen. <https://www.constructionbriefing.com/news/how-a-new-safety-system-aims-to-predict-accidents-before-they-happen/8116181.article>
16. Oracle Transforms Construction Safety Management with AI. <https://www.oracle.com/news/announcement/oracle-transforms-construction-safety-management-with-ai-2026-03-05/>
17. Predictive Analytics in Construction: A Constructive Guide (2025) - RTS Labs. <https://rtslabs.com/predictive-analytics-in-construction/>
18. RiskScan 2026: (Re)insurance - Munich Re. <https://www.munichre.com/us-non-life/en/insights/reinsurance-riskscan.html>
19. Business-cycle Influences on Work-related Disability in Construction and Manufacturing - Milbank Memorial Fund. <https://www.milbank.org/wp-content/uploads/mq/volume-67/issue-s2/67-S2-Business-cycle-Influences-on-Work-related-Disability-in-Construction-and-Manufacturing.pdf>
20. Workers' compensation and the business cycle - Institute for Work & Health. <https://www.iwh.on.ca/plain-language-summaries/workers-compensation-and-business-cycle>
21. Abstract: cross-sectional time series techniques for workers compensation frequency - CAS. <https://www.casact.org/sites/default/files/database/proceed_proceed97_97660.pdf>
22. RESEARCH BRIEF - New York Compensation Insurance Rating Board. <https://www.nycirb.org/nycirb-documents/documents/2024-Claim-Frequency-and-The-Economy-Report.pdf>
23. Impact of Economic Downturn on California Workers' Compensation Claim Frequency - WCIRB. <https://www.wcirb.com/sites/default/files/documents/rb-impact_of_economic_downturn-audienceready_0.pdf>
24. Nowcasting GDP Growth for Kenya, WP/26/32, February 2026. <https://www.elibrary.imf.org/view/journals/001/2026/032/article-A001-en.pdf>
25. Impact of Economic Indicators on Insurance Claim Frequency in Namibia - AJPO Journals. <https://ajpojournals.org/journals/AJE/article/download/2257/2899/8553>
26. WCIRB 2025 State of the System. <https://www.wcirb.com/sites/default/files/2025-07/WCIRB-2025%20State%20of%20the%20System%20Report-California%20Workers%20Compensation%20Insurance%20System-2025-07-23.pdf>
27. 2025 Impact of Economic Changes on California Workers' Compensation - WCIRB. <https://www.wcirb.com/sites/default/files/2025-07/2025_impact_of_economic_changes_on_california_workers_compensation.pdf>
28. Impact of Economic Changes on California Workers' Compensation - WCIRB. <https://www.wcirb.com/sites/default/files/documents/wcirb-2023-impact_of_economic_changes-report-ar_1.pdf>
29. Predictive Modelling for Residential Construction Demands Using ElasticNet Regression. <https://www.mdpi.com/2075-5309/15/10/1649>
30. Owner-Controlled Insurance Programs for Public Construction Projects | MMA - Marsh McLennan Agency. <https://www.marshmma.com/us/insights/details/owner-controlled-insurance-programs-public-sector-projects.html>
31. Global Economic And Insurance Market Outlook 2020/2021 | Swiss Re. <https://www.swissre.com/dam/jcr:60421a3b-f246-4718-8374-f4170d52b492/global-economic-and-insurance-outlook-2021.pdf>
32. Financial Stability Review, November 2023 - European Central Bank. <https://www.ecb.europa.eu/pub/pdf/fsr/ecb.fsr202311~bfe9d7c565.en.pdf>
33. Working Paper: GDP Nowcasting: From Traditional Econometric Models to Machine Learning Algorithms. <https://efsd.org/en/research/working-papers/working-paper-working-paper-gdp-nowcasting-from-traditional-econometric-models-to-machine-learning-a/>
34. Predicting the Present with Bayesian Structural Time Series - ResearchGate. <https://www.researchgate.net/publication/264816307_Predicting_the_Present_with_Bayesian_Structural_Time_Series>
35. Nowcasting macroeconomic indicators with alternative data: a literature review. <https://www.researchgate.net/publication/373884918_Nowcasting_macroeconomic_indicators_with_alternative_data_a_literature_review>
36. Dynamic Mortality Forecasting via Mixed-Frequency State-Space Models - arXiv. <https://arxiv.org/html/2601.05702v1>
37. The New York Fed Staff Nowcast 2.0. <https://www.newyorkfed.org/medialibrary/media/research/blog/2023/NYFed-Staff-Nowcast_technical-paper>
38. Dynamic Factor Models - ResearchGate. <https://www.researchgate.net/publication/281908680_Dynamic_Factor_Models>
39. Economic Policy Review - Federal Reserve Bank of New York. <https://www.newyorkfed.org/research/epr/medialibrary/6501bd82d3bc482891b59df93e24011d.ashx>
40. Releasing dfms 1.0: Fast and Feature-Rich Estimation of Dynamic Factor Models in R. <https://sebkrantz.github.io/Rblog/2026/01/29/releasing-dfms-1-0-fast-and-feature-rich-estimation-of-dynamic-factor-models-in-r/>
41. Nowcasting GDP - A Scalable Approach Using DFM, Machine Learning and Novel Data, Applied to European Economies - IMF eLibrary. <https://www.elibrary.imf.org/view/journals/001/2022/052/article-A001-en.xml>
42. Todd Clark - IDEAS/RePEc. <https://ideas.repec.org/e/c/pcl55.html>
43. Global Macro-Financial Cycles and Spillovers – Research Dept. Working Paper No. 2512. <https://www.dallasfed.org/~/media/documents/research/papers/2025/wp2512.pdf>
44. Nowcasting Growth Using the Bayesian Structural Time Series Model: Application to Tanzania - IMF eLibrary. <https://www.elibrary.imf.org/view/journals/001/2026/049/article-A001-en.xml>
45. Testing big data in a big crisis: Nowcasting under Covid-19 - PMC. <https://pmc.ncbi.nlm.nih.gov/articles/PMC9633630/>
46. Nowcasting Growth Using the Bayesian Structural Time Series Model: Application to Tanzania - IMF. <https://www.imf.org/-/media/files/publications/wp/2026/english/wpiea2026049-source-pdf.pdf>
47. Predicting the Present with Bayesian Structural Time Series - ResearchGate. <https://www.researchgate.net/publication/314478843_Predicting_the_Present_with_Bayesian_Structural_Time_Series>
48. Bayesian Modeling of Labor Earnings in Construction - ASCE Library. <https://ascelibrary.org/doi/10.1061/JCEMD4.COENG-12392>
49. Implementation of Bayesian Structural Time Series (BSTS) Method for Predicting Traditional Market Revenue Achievement in Surabaya. <https://ijeeemi.org/index.php/ijeeemi/article/download/82/73/891>
50. Machine learning applications for predicting safety incidents in construction industry - ResearchGate. <https://www.researchgate.net/publication/399657275_Machine_learning_applications_for_predicting_safety_incidents_in_construction_industry>
51. Machine learning applications for predicting safety incidents in construction industry - PMC. <https://pmc.ncbi.nlm.nih.gov/articles/PMC12867970/>
52. A Machine Learning Approach for Factor Analysis and Scenario-Based Prediction of Construction Accidents - MDPI. <https://www.mdpi.com/2075-5309/15/23/4343>
53. Machine learning predictive model based on national data for fatal accidents of construction workers - KAIST. <https://pure.kaist.ac.kr/en/publications/machine-learning-predictive-model-based-on-national-data-for-fata/>
54. Estimating Indirect Accident Cost Using a Two-Tiered Machine Learning Algorithm for the Construction Industry - MDPI. <https://www.mdpi.com/2075-5309/15/21/3947>
55. 43rd International Symposium on Forecasting. <https://isf.forecasters.org/wp-content/uploads/BookOfAbstractsISF2023.pdf>
56. Predicting Future Claims. <https://lni.wa.gov/safety-health/safety-research/ongoing-projects/predicting-future-claims>
57. An overview of (re)insurance buyers' and sellers' top risk concerns. <https://www.iii.org/sites/default/files/docs/pdf/risk_scan_report_2026.pdf>
58. Impact of Economic Changes on California Workers' Compensation - WCIRB. <https://www.wcirb.com/sites/default/files/2024-06/economic_report_2024.pdf>
59. WCIRB 2023 State of the System. <https://www.wcirb.com/sites/default/files/documents/wcirb_2023_state_of_the_system.pdf>
60. Analysis of occupational accidents in Spain using shrinkage regression methods - ResearchGate. <https://www.researchgate.net/publication/346777466_Analysis_of_occupational_accidents_in_Spain_using_shrinkage_regression_methods>
61. Analysis of the Correlation between Occupational Accidents and Economic Factors in China. <https://pubmed.ncbi.nlm.nih.gov/34682524/>
62. The Role of Predictive Analytics in Construction Success - Beck Technology. <https://www.beck-technology.com/blog/the-role-of-predictive-analytics-in-construction-success>
63. Technology Revolutionizes Real-Time Modeling and Response - Aon. <https://www.aon.com/en/insights/articles/technology-revolutionizes-real-time-modeling-and-response>
64. Hybrid AI Models for Short-Term Photovoltaic Forecasting: A Systematic Review - MDPI. <https://www.mdpi.com/1424-8220/26/6/1793>
65. Incident Analysis and Prediction of Safety Performance on Construction Sites - MDPI. <https://www.mdpi.com/2673-4109/3/3/39>
