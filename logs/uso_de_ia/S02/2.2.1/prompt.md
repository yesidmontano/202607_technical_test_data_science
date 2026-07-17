Modela la relación dinámica entre el ciclo del sector construcción y la frecuencia de accidentes de trabajo. Lee la síntesis de la caracterización sectorial en `sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/results/caracterizacion.md` (sección 2.1.4). Las fuentes de entrada son:
- **DANE (staging):** `data/staging/S02/panel_fuentes_trimestral.parquet` (CEED + IPOC + EC alineadas) — covariables cíclicas observadas.
- **Macro sintético:** `data/raw/macro_sectorial.csv` — filtra filas donde `sector == 'Construccion'`; contiene `pib_sectorial_var`, `empleo_sectorial`, `ipp_sectorial` y `tasa_informalidad` a frecuencia trimestral. Úsalas como controles macroeconómicos adicionales en el modelo (variables exógenas o bloque ampliado del VAR).
- **Serie objetivo:** construye la frecuencia trimestral de AT del sector construcción a partir de `data/staging/S01/temporal_empresa_anio.parquet`, filtrando por sector construcción con ayuda de `data/raw/empresas.csv`.

Alinea las tres fuentes en un único panel trimestral antes de modelar (ventana de solapamiento efectiva: trimestrales disponibles en todas las fuentes). Sigue esta secuencia de análisis:

1. **Construcción de la serie objetivo:** agrega a nivel trimestral el número de siniestros de las empresas del sector construcción (años disponibles en el panel). Justifica la unidad de tiempo elegida (trimestral) en función de la frecuencia de las fuentes DANE.
2. **Análisis de estacionariedad:** aplica tests ADF y KPSS a la serie de AT y a cada indicador cíclico (área causada CEED, producción IPOC, concreto EC, `pib_sectorial_var`, `empleo_sectorial`, `ipp_sectorial`). Clasifica cada serie como I(0), I(1) o I(2) y selecciona el número de diferencias necesario. Documenta la decisión con criterio estadístico explícito.
3. **Selección de especificación:** evalúa si existe cointegración (Engle-Granger o Johansen según el número de series) entre AT y las series I(1). Si hay cointegración, estima un **VEC (VECM)**; si no, estima un **VAR en diferencias**. Justifica la elección frente a las alternativas (OLS simple, ADL, VAR en niveles) con argumentos teóricos y estadísticos.
4. **Selección de rezagos:** usa AIC/BIC/HQ para determinar el orden p del VAR/VECM. Incluye hasta p=4 trimestres dada la ventana disponible y los rezagos ELIC→CEED de 6–18 meses documentados en 2.1.4.
5. **Estimación e interpretación:** estima el modelo seleccionado. Reporta funciones impulso-respuesta (IRF) para medir el efecto de un shock de 1 desviación estándar en CEED sobre AT (y viceversa). Incluye descomposición de varianza (FEVD) a 4 y 8 trimestres.
6. **Diagnósticos:** verifica ausencia de autocorrelación serial en residuos (test Portmanteau), homocedasticidad (test ARCH multivariado) y normalidad (Jarque-Bera multivariado). Reporta tabla de diagnósticos comparando modelo VAR/VECM contra alternativas simples.
7. **Bloque IPOC separado:** dado que CEED e IPOC muestran correlación negativa (ρ ≈ −0.72), estima un modelo auxiliar independiente con IPOC como variable de ciclo de infraestructura. Compara sus IRF con el bloque edificación (CEED/EC) y discute si operan en fases opuestas del ciclo.

Incluye código en `sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/code/01-modelamiento`.

Transversal:
1. Guardar datasets de staging intermedios que se produzcan en `data/staging/S02/` y documentar cada uno en `docs/staging_data.md`. No crees datasets nuevos sin antes revisar si ya existe uno reutilizable.
2. Los plots deben guardarse en `sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/results/imgs/`.
3. Al finalizar, incluye los hallazgos (especificación elegida, IRF clave, diagnósticos) en `sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/results/relaciones.md` bajo la sección 2.2.1, para mi revisión.
4. Diligencia `logs/uso_de_ia/S02/2.2.1/output.md` como log del proceso que realizaste.
