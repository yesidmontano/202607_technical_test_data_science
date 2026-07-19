### **S03: Modelación para reto de negocio**
Objetivo: El reto de negocio: la Dirección necesita anticipar el resultado técnico del portafolio y decidir dónde ajustar la suscripción y la tarifa. Usted debe modelar el costo esperado de siniestralidad y convertirlo en una recomendación.

---

### **Requerimiento 3.4**
Documentar el modelo de forma integral y traduzcir el resultado en una recomendación accionable de negocio, explicitando los límites y los riesgos del modelo.

---

### 3.4 Documentación integral y recomendación

#### Pregunta respondida
¿Cuál es el costo esperado de siniestralidad del próximo año por empresa y clase, y dónde la prima no cubre ese costo, de modo que haya que ajustar **suscripción** o **tarifa**?

---

#### Modelo

| Pieza | Elección | Evidencia |
|---|---|---|
| Frecuencia | **Binomial Negativa** + offset `log(n_trabajadores)` | Sobredispersión (S01–P1); α≈0.114 |
| Severidad | **Lognormal** AT/EL separados, condicionada a clase × tamaño × gravedad | P6, P12; S1 dependencia freq–sev |
| Costo esperado | Pure premium `E[N]×E[Sev\|X]` | Holdout 2024: Spearman≈0.57; portafolio pred/obs≈0.99 |
| Proyección | Base vs adverso (+36% YoY histórico) + bootstrap | CR base **80%**; adverso **102%** |

**Inputs clave:** clase de riesgo, segmento, sector, lag de siniestros, exposición (trabajadores).  
**Outputs:** `modelo_pred_empresa`, `proyeccion_escenarios` / `proyeccion_empresa` en `data/staging/S03/`.

---

#### Proyección próximo año

| Escenario | Siniestralidad | Primas | LR | CR* | Resultado |
|---|---|---|---|---|---|
| **Base** | 15.9 B | 28.8 B | 55% | **80%** | **+5.7 B** |
| **Adverso** | 21.6 B | 28.8 B | 75% | **102%** | **−0.6 B** |

\*CR = LR + expense ratio (supuesto 25% / 27% adverso). P(CR>100%) en simulación ≈ **8%**.  
Clases **4–5** concentran **~72%** del costo esperado; clase 5 tiene el CR más alto (~92% base).

---

#### Recomendación accionable

1. **Suscripción (corto plazo):** restringir o condicionar nueva afiliación / aumentos de exposición en el Top de `costo_pred` y en las **169 empresas** con LR predicho > 1 (`insuficiente_pred=1`), con foco en **Micro + clases 4–5**.
2. **Tarifa (ciclo tarifario):** revisar al alza segmentos `clase × sector × tamaño` con LR histórico > 1 (**25 celdas** en staging de supuestos), priorizando Micro en sectores de alto costo (p. ej. Alojamiento/comida, Minería, Agricultura, Construcción).
3. **Monitoreo de portafolio:** usar CR base ~80% como escenario de planificación y el adverso (CR>100%) como **umbral de alerta** para reservas y acciones preventivas; no gestionar solo con el punto central.
4. **Gobernanza:** no usar el modelo claim-by-claim con gravedad observada para pricing; el E[Sev] de negocio ya marginaliza gravedad/tipo.

---

#### Límites y riesgos del modelo

| Límite / riesgo | Implicación |
|---|---|
| Expense ratio **supuesto** (no hay gastos en datos) | El CR es indicativo; sensibilizar ±5 pp antes de decisions de capital |
| Severidad **promedia** gravedad | Subestima cola de eventos graves/mortales a nivel empresa |
| Dependencia freq–sev solo vía covariables | No hay cópula; en estrés extremo el costo puede ser peor que el adverso puntual |
| Prima estática como “devengada” | No modela cambios de tarifa ni mix de cartera mid-year |
| Cola pesada (R² costo empresa bajo) | Buen ranking y calibración de portafolio ≠ precisión individual |
| Shock adverso anclado a un solo YoY máx. (+36%) | Escenario creíble pero no “catástrofe”; stress adicional si se requiere capital regulatorio |

---

#### Lectura para Dirección

El portafolio entra al próximo año con **margen técnico en el escenario base (CR≈80%)**, pero un año de siniestralidad como el peor histórico observado **borra ese margen (CR≈102%)**; la acción de valor está en **ajustar suscripción y tarifa en Micro / clases altas / segmentos con LR>1**, no en mover la tarifa promedio del portafolio completo.

