### **S02: Modelación económica y sectorial del sector construcción**
 Objetivo: El sector construcción es uno de los de mayor accidentalidad y mayor sensibilidad al ciclo económico. La Dirección quiere anticipar la siniestralidad del sector a partir de su ciclo. El candidato debe combinar el panel sintético de macro_sectorial.csv con series públicas del DANE que él mismo debe identificar. Esta sección es el eje de la prueba y exige rigor econométrico, criterio de fuentes y un componente de soporte documental.

---

### **Requerimiento 2.2**
Modelar la relación dinámica entre el ciclo del sector y la frecuencia de accidentes de trabajo del sector. Tratar estacionariedad, rezagos y adelantos, y una posible relación de largo plazo entre actividad sectorial y siniestralidad. Justificar la especificación frente a alternativas y presentar diagnósticos.

---

## 2.2.1 Modelamiento de la relación dinámica entre el ciclo del sector y la frecuencia de accidentes de trabajo del sector

> **Script:** `sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/code/01-modelamiento/modelamiento_relaciones.py`
> **Staging:** `data/staging/S02/` (#58–65 en `docs/staging_data.md`)
> **Figuras:** `results/imgs/01_*.png`
> **Síntesis de ciclo (insumo):** `caracterizacion.md` §2.1.4

---

### 1. Construcción de la serie objetivo y alineación

**Universo:** 442 empresas con `sector == Construccion` (`empresas.csv`, cruzado con `temporal_empresa_anio`).

**Frecuencia AT trimestral:** se agregó `tipo == AT` desde `siniestros_imputados` por año-trimestre. Los totales anuales coinciden exactamente con `temporal_empresa_anio.n_at` (validación de integridad). La frecuencia operativa es:

\[
\texttt{freq\_at\_x100}_t = \frac{n\_AT_t}{n\_trabajadores\_sector_t}\times 100
\]

**Por qué trimestral:** CEED e IPOC son trimestrales; `macro_sectorial` es trimestral; EC se reduce a media trimestral en `panel_fuentes_trimestral`. Una frecuencia mensual obligaría a interpolar CEED/IPOC y debilitaría la identificación.

**Panel alineado** (`panel_ciclo_at_trimestral`): AT + CEED (`proceso_nueva_m2` como proxy de flujo / iniciaciones; el CSV no trae “área causada” literal) + EC + IPOC + macro (`pib_sectorial_var`, `empleo_sectorial`, `ipp_sectorial`, `tasa_informalidad`).

| Ventana | Contenido | n |
|---|---|---|
| 2018-I → 2024-IV | AT + macro | 28 |
| 2020-III → 2024-IV | + CEED/IPOC | 18 |
| **2022-I → 2024-IV** | **+ EC (muestra edificación)** | **12** |

![Series alineadas](imgs/01_series_at_ciclo.png)

---

### 2. Estacionariedad (ADF + KPSS, α=0.05)

Regla: I(0) solo si ADF rechaza raíz unitaria **y** KPSS no rechaza estacionariedad; en conflicto o evidencia de raíz → tratar como I(1) y verificar Δ.

| Serie | I(d) | Decisión |
|---|---|---|
| `log_freq_at` | **I(1)** | Conflicto nivel → Δ estacionaria |
| `log_ceed_flujo` | **I(1)** | Idem |
| `log_ec` | **I(1)** | Idem |
| `log_ipoc` | **I(1)** | Idem |
| `pib_sectorial_var` | **I(1)**† | Conflicto (tasa; muestra corta) |
| `log_empleo` / `log_ipp` | **I(1)** | Concordancia ADF+KPSS |

† Con T pequeño, una tasa de variación puede clasificarse I(1) por baja potencia; se diferencia igual que el resto para coherencia del sistema.

**Decisión:** todas las endógenas del núcleo se modelan en **primeras diferencias** (o VECM si hubiera cointegración robusta).

![Orden de integración](imgs/01_estacionariedad_orden.png)

---

### 3. Especificación elegida

**Tests de cointegración (bloque edificación, Y = log AT, log CEED, log EC):**

| Test | Resultado | Lectura |
|---|---|---|
| Engle-Granger | p = **0.995** | No rechaza “sin cointegración” |
| Johansen (trace) | r̂ = **2** | Sugiere cointegración, pero **T=12** |

**Elección: VAR(1) en primeras diferencias**, con exógenas Δ(`pib_sectorial_var`, `log_empleo`).

**Justificación (frente a alternativas):**

1. **vs VECM:** con T=12, Johansen tiene distorsión de tamaño conocida; la regla adoptada privilegia Engle-Granger. Sin cointegración EG → VECM no está justificado.
2. **vs VAR en niveles:** series I(1) → riesgo de regresión espuria y IRF no estacionarias.
3. **vs OLS estático:** ignora dinámica y rezagos documentados del ciclo (6–18 meses ELIC→CEED en 2.1.4); coef. CEED no significativo (β=−0.28, p=0.38).
4. **vs ADL(1):** buen ajuste en muestra (R²=0.96) pero es uniecuacional; no permite IRF/FEVD del sistema ni shocks ortogonales CEED↔AT.

![Selección de rezagos](imgs/01_lag_selection.png)

**Rezagos:** AIC/BIC/HQ sobre p∈{1…4}; con T_diff=11 y k=3 (+2 exóg.), el máximo factible es **p=1** (elegido unánimemente). El techo p=4 pedido en el enunciado no es estimable sin colapsar grados de libertad en esta ventana.

---

### 4. IRF y FEVD — bloque edificación

Shock ortogonal de 1 d.e. en el VAR(1) en diferencias.

![IRF CEED ↔ AT](imgs/01_irf_ceed_at.png)

| Horizonte | IRF CEED → AT | IRF AT → CEED |
|---|---|---|
| h=1 | **+0.037** | +0.023 |
| h=2 | −0.015 | +0.022 |
| h=3 | −0.011 | −0.032 |
| h=4 | +0.015 | +0.010 |

**Lectura:** un shock positivo de actividad edificación (CEED flujo) eleva la frecuencia AT en el trimestre siguiente (~+3.7% en log), con oscilación que se disipa hacia h=6–8. El feedback AT→CEED es del mismo orden y también de corta memoria — coherente con un VAR(1) en diferencias y T corto.

![FEVD](imgs/01_fevd_at.png)

**FEVD de `log_freq_at`:**

| Horizonte | Propia (AT) | CEED | EC |
|---|---|---|---|
| **h=4** | 80.5% | **10.1%** | 9.4% |
| **h=8** | 78.9% | **11.2%** | 9.9% |

CEED + EC explican ~20% de la varianza de AT a 1–2 años; la inercia propia domina (muestra corta y p=1).

---

### 5. Diagnósticos (residuos)

![Diagnósticos](imgs/01_diagnosticos_residuos.png)

| Modelo | AIC | Portmanteau | ARCH | Jarque-Bera |
|---|---|---|---|---|
| **VAR_diff edificación (elegido)** | −15.4 | p_min=0.041 ⚠ | ✓ (0.31) | ✓ (0.63) |
| OLS estático | −19.3 | ✓ | ✓ | ✓ |
| ADL(1) | −27.6 | ✓ | ✓ | ✓ |
| VAR niveles | −16.3 | ✓ | ✓ | ✓ |
| VAR_diff IPOC | −8.9 | ✓ | ✓ | ✓ |

El Portmanteau del VAR edificación queda en el margen (p≈0.04): con T≈10 residuales no se interpreta como rechazo fuerte; ARCH y normalidad pasan. ADL/OLS tienen mejor AIC pero **no** responden a la pregunta de dinámica multi-ecuacional ni a IRF del ciclo.

---

### 6. Bloque auxiliar IPOC (infraestructura)

Especificación: **VAR(2) en diferencias** (AT, IPOC) + exógenas macro; EG AT~IPOC p=0.986 → sin cointegración. Ventana más larga (n=18).

![IPOC vs CEED](imgs/01_irf_ipoc_vs_ceed.png)

| Evidencia | Valor | Interpretación |
|---|---|---|
| Spearman CEED↔IPOC (muestra edif.) | **−0.80** | Confirma desacople 2.1.4 (ρ≈−0.72) |
| Spearman CEED↔AT | −0.62 | Contemporáneo negativo en 2022–24 (contracción CEED + alza AT) |
| Spearman IPOC↔AT | **+0.41** | Infraestructura y AT co-mueven en esta ventana |
| IRF IPOC→AT (h=1…4) | +0.026, **−0.058**, +0.013, +0.003 | Pulso distinto al de CEED (pico negativo en h=2) |
| FEVD IPOC→AT h=4 / h=8 | 18.0% / 18.2% | IPOC explica ~18% de la varianza de AT |

**Conclusión del bloque:** edificación (CEED/EC) e infraestructura (IPOC) **no operan en la misma fase** del ciclo respecto a AT. Mezclarlas en un solo VAR endógeno contaminaría la identificación — se mantienen modelos separados, como anticipaba §2.1.4.

---

### 7. Implicaciones para 2.3 (nowcast) y negocio ARL

1. La señal cíclica de edificación aporta ~10–11% de la varianza de AT a 4–8 trimestres; útil como **covariable de anticipación**, no como predictor único.
2. EC entra en el sistema endógeno y aporta ~9–10% en FEVD → refuerza su rol de bridge de alta frecuencia hacia el nowcast.
3. IPOC debe entrar como **escenario / bloque paralelo** (obras civiles), no como sustituto de CEED.
4. **Limitación crítica:** n=12 en el bloque con EC restringe p y potencia; ampliar historial ELIC/EC o usar solo CEED+AT en ventana 2020–2024 (n=18) es la sensibilidad natural del siguiente paso.

---

### Artefactos generados

| Tipo | Ruta |
|---|---|
| Script | `code/01-modelamiento/modelamiento_relaciones.py` |
| Staging | `at_construccion_trimestral`, `panel_ciclo_at_trimestral`, `estacionariedad_tests`, `var_lag_selection`, `var_irf`, `var_fevd`, `var_diagnosticos`, `var_modelo_resumen` |
| Plots | `01_series_at_ciclo.png`, `01_estacionariedad_orden.png`, `01_lag_selection.png`, `01_irf_ceed_at.png`, `01_fevd_at.png`, `01_diagnosticos_residuos.png`, `01_irf_ipoc_vs_ceed.png` |
