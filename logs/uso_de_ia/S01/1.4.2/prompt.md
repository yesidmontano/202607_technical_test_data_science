Evalúa formalmente las hipótesis de mecanismos de datos faltantes (MCAR / MAR / MNAR) para las variables con nulos en empresas.csv y siniestros.csv. Realizar pruebas estadísticas formales (pruebas de independencia Chi-cuadrado para variables categóricas, pruebas t de Student o Mann-Whitney U para numéricas, y regresión logística de indicadoras de nulos) sobre las señales observadas en la sección D de Insights_datos_faltantes.md para determinar el mecanismo de cada variable. Incluir código en (sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/02-mecanismos).

Transversal: 
1. Guardar datasets de staging en data/staging/S01/ para que estos sean reutilizados por futuros procesos que los requieran. Guarda la descripción detallada de cada dataset en docs/staging_data.md. Nota: No crees datasets nuevos sin antes revisar en docs/staging_data.md si ya existe uno que se pueda reutilizar.
2.Los plots deben incluirse en su respectviva carpeta de results, para este proceso correspondiente es 'sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/results/imgs'
3. Al finalizar incluye los hallazgos de este proceso en 'sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/results/Insights_datos_faltantes.md' para mi revisión.
4. Diligencia logs/uso_de_ia/S01/1.4.2/output.md como logs del proceso que realizaste.
