### **S02: Modelación económica y sectorial del sector construcción**
 Objetivo: El sector construcción es uno de los de mayor accidentalidad y mayor sensibilidad al ciclo económico. La Dirección quiere anticipar la siniestralidad del sector a partir de su ciclo. El candidato debe combinar el panel sintético de macro_sectorial.csv con series públicas del DANE que él mismo debe identificar. Esta sección es el eje de la prueba y exige rigor econométrico, criterio de fuentes y un componente de soporte documental.

---

### **Requerimiento 2.3**
Producir un nowcast de la frecuencia de accidentes de trabajo del trimestre en curso combinando la siniestralidad parcial observada con los indicadores líderes, considerando de forma explícita los distintos rezagos de publicación de las fuentes. Reportar la incertidumbre del nowcast.

---

### 2.3.1 Revisión de estado del arte.
Posterior a la revisión del estado del arte en relación a modelos nowcast de siniestralidad en el sector construcción, se encontró lo siguiente:

El documento 'sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/resources/estado_del_arte.md' presenta una revisión exhaustiva sobre el uso de modelos de nowcasting para predecir la siniestralidad en la construcción, vinculando directamente la seguridad laboral con las fluctuaciones del ciclo económico. La tesis central sostiene que los accidentes son pro-cíclicos, aumentando en periodos de auge debido a la fatiga, la contratación de personal inexperto y la aceleración de la producción, mientras que las recesiones suelen mostrar una baja estadística influenciada por el miedo al reporte y la retención de trabajadores veteranos. Para superar los retrasos en las estadísticas oficiales, el texto explora diversas metodologías que van desde la econometría tradicional, como los Modelos de Factores Dinámicos, hasta innovaciones en Inteligencia Artificial y Series Temporales Bayesianas que permiten una selección automática de variables. En última instancia, la fuente busca proporcionar a la industria aseguradora herramientas para una gestión de riesgos proactiva, optimizando el cálculo de reservas y permitiendo una tarificación dinámica basada en indicadores de alta frecuencia como el empleo y el consumo de materiales.

A partir de esto entrenaremos los siguientes modelos:
1. Modelos de Machine Learning: Random Forest
2. Modelos Econometricos y de Series temporales: BSTS y DFM.

---

## 2.3.2 Producción del nowcast (RF, BSTS, DFM)

> **Scripts:** `code/02-produccion/{nowcast_common,01_random_forest,02_bsts,03_dfm,04_comparativo}.py`
> **Figuras:** `results/imgs/02_*.png`
> **Staging:** `nowcast_panel_ragged`, `nowcast_{rf,bsts,dfm}_*`, `nowcast_comparativo_*`, `nowcast_forward_2025T1`, `nowcast_resumen_final` (#73–87)

### 1. Diseño del information set (ragged-edge)

Se reproduce el vintage operativo ≈ **día 40 del trimestre T** (cuando EC del mes 1 ya salió; CEED/IPOC de T aún no):

| Fuente | Rezago pub. | En el nowcast de T |
|---|---|---|
| AT parcial | interno | Claims del **mes 1** → `freq_at_parcial_x100` (~32% del total trimestral en media) |
| EC | ~38 d | m³ del mes 1 → `log_ec_parcial` |
| CEED / IPOC | ~45–48 d | Solo **lag-1** (+ MA3 lag-1 y lag-4 como memoria del canal CCF k≈6 de 2.2.2) |
| Macro | trimestral | `pib_lag1`, `log_empleo_lag1` |

**Target:** `freq_at_x100` del trimestre completo.  
**Ventana modelable:** 17 trimestres (CEED disponible). **Splits temporales:** train ≤2023-T2 (n=11), val 2023-T3–T4 (n=2), test 2024 (n=4). **Forward:** 2025-T1 (sin AT observado; AT parcial imputado con share histórico × lag-1).

### 2. Modelos

| # | Familia | Implementación | Incertidumbre |
|---|---|---|---|
| 1 | ML | Random Forest (grid `max_depth`/`min_samples_leaf`/`n_estimators` en val) | Cuantiles 10–90% entre árboles |
| 2 | Series bayesianas | BSTS: local level UC + spike-and-slab (PIP) sobre regresores; AT parcial forzado | SE del forecast + escala residual |
| 3 | Factores | DFM 1 factor (Kalman) sobre indicadores lag + puente OLS `AT ~ factor + AT_parcial` | Bootstrap residual del puente |

### 3. Métricas train / val / test

| Modelo | Split | n | MAE | RMSE | MAPE (%) |
|---|---|---|---|---|---|
| **DFM** | train | 11 | 0.059 | 0.070 | 6.2 |
| **DFM** | val | 2 | 0.079 | 0.103 | 6.0 |
| **DFM** | **test** | **4** | **0.077** | **0.098** | **6.6** |
| Random Forest | train | 11 | 0.052 | 0.066 | 5.6 |
| Random Forest | val | 2 | 0.259 | 0.287 | 20.2 |
| Random Forest | test | 4 | 0.132 | 0.153 | 10.3 |
| BSTS | train | 11 | 0.162 | 0.367 | 15.7 |
| BSTS | val | 2 | 0.115 | 0.115 | 9.4 |
| BSTS | test | 4 | 0.136 | 0.209 | 12.6 |

![Comparativo métricas](imgs/02_comparativo_metricas.png)

![Test 2024](imgs/02_comparativo_test.png)

**Veredicto test:** el **DFM** domina (menor RMSE/MAE/MAPE y R²>0). RF generaliza peor que su ajuste in-sample (val frágil con n=2). BSTS aporta intervalos amplios y selección PIP coherente con CEED lag, pero con T corto el componente estructural es ruidoso.

### 4. Nowcast forward 2025-T1 (trimestre sin AT)

| Modelo | Punto | IC 80% |
|---|---|---|
| **DFM (preferido)** | **1.158** | [1.062, 1.285] |
| Random Forest | 1.084 | [0.916, 1.245] |
| BSTS | 1.379 | [0.965, 1.793] |

![Forward](imgs/02_comparativo_forward.png)

Interpretación de negocio: con el DFM, la frecuencia AT esperada en 2025-T1 se sitúa cerca de **1.16 por 100 trabajadores**, con banda 80% relativamente estrecha gracias al AT parcial (proxy) y al factor de ciclo. BSTS es más conservador/alcista y más incierto — útil como escenario de estrés, no como punto central.

### 5. Figuras por modelo

| Modelo | Artefactos |
|---|---|
| RF | `02_rf_pred_vs_actual.png`, `02_rf_importancia.png`, `02_rf_forward_uncertainty.png` |
| BSTS | `02_bsts_pred_vs_actual.png`, `02_bsts_pip.png`, `02_bsts_forward_uncertainty.png` |
| DFM | `02_dfm_pred_vs_actual.png`, `02_dfm_factor.png`, `02_dfm_loadings.png`, `02_dfm_forward_uncertainty.png` |

### 6. Limitaciones

1. **n=17** (test n=4): métricas de test son orientativas; val n=2 es frágil para tuning.
2. Forward 2025-T1 **no tiene AT parcial real** → se usa share histórico × `freq_at_lag1`; el IC del DFM puede subestimar error de proxy.
3. El canal CCF k=6 no entra como p=6; se aproxima con lag-4 / MA3 (coherente con 2.2.2).
4. IPOC sigue en el factor DFM pero con divergencia edificación/infra (2.1.3); el puente se ancla en AT parcial.



