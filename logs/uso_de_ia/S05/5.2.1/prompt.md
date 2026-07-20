Dado el contexto del modelo seleccionado en 5.1.1 (ver contexto en sections/S05-Sistema_Recomendador/5_1_Diseño de recomendador/results/diseño_recomendador.md), ayudame a implementar un prototipo funcional y evaluarlo con una metodología de validación apropiada que incluya partición temporal. Reportar las métricas que indico abajo y discutir las limitaciones de la evaluación offline. 

Métricas principales a evaluar:
Primarias: NDCG@5 y Recall@5 (warm / cold).
De negocio: ΔRisk@5 vs popularidad.
Guardrails: coverage + % cold con K válidas.
Calibración de α: curva NDCG@5 vs ΔRisk@5 al variar α — elegir el punto donde el riesgo sube sin tumbar demasiado la adopción.

Guardar código en sections/S05-Sistema_Recomendador/5_2_Implementacion de prototipo/code/01-prototipo

Transversal:
1. Guardar datasets de staging en data/staging/S05/ para que estos sean reutilizados por futuros procesos que los requieran. Guarda la descripción detallada de cada dataset en docs/staging_data.md
2. Los plots deben incluirse en su respectiva carpeta de results, para este proceso correspondiente es 'sections/S05-Sistema_Recomendador/5_2_Implementacion de prototipo/results/imgs'
3. Al finalizar incluye los resultados obtenidos en 'sections/S05-Sistema_Recomendador/5_2_Implementacion de prototipo/results/prototipo_recomendador.md' para mi revisión y elección de con cual diseño quedarme.
4. Diligencia logs/uso_de_ia/S05/5.1.1/output.md como logs del proceso que realizaste.
5. Usa el paquete sura_brand para los gráficos.