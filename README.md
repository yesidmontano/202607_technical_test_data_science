# Prueba Técnica de Ciencia de Datos — ARL / Analítica

Repositorio completo de la prueba técnica (Grupo SURA · Dirección de Analítica). Resuelve, de punta a punta, modelación sectorial, proyección de portafolio, inferencia causal, recomendación de servicios y paso a producto — sobre **datos 100 % sintéticos**.

| | |
|---|---|
| **Autor** | Yesid Montaño |
| **Entrega** | Repositorio Git con historia de commits, scripts `.py` (sin notebooks), resultados versionados y registro de uso de IA |
| **Python** | 3.12 (probado con 3.12.0) |
| **Semilla** | `RANDOM_SEED = 42` en todo proceso estocástico |

---

## Quick path (reproducir en 5 minutos)

Los artefactos de `data/staging/` y `sections/**/results/` ya están en el repositorio. Para **consultar** el trabajo no hace falta re-ejecutar modelos:

```bash
git clone <url-del-repo>
cd 202607_technical_test_data_science

python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt

# Verificar que el paquete de marca quedó instalado
python -c "import sura_brand as sb; print(sb.AZUL_SURA.hex)"
```

**Puntos de entrada para revisión:**

1. Resúmenes por sección → [`docs/summaries/`](docs/summaries/)
2. Informe para junta → [`sections/S07-Comunicacion/7_1_Resumen ejecutivo/resources/resumen_manual_stakeholder.md`](sections/S07-Comunicacion/7_1_Resumen%20ejecutivo/resources/resumen_manual_stakeholder.md) y el one-pager HTML en `results/resumen_ejecutivo.html`
3. Enunciado → [`docs/Prueba tecnica/`](docs/Prueba%20tecnica/)
4. Diccionario de datos → [`docs/diccionario_datos.md`](docs/diccionario_datos.md)

Para **re-ejecutar** los pipelines (regenerar staging + figuras), ver [Reproducción completa](#reproducción-completa).

---

## Qué se entregó (mapa S01–S07)

| Sección | Objetivo | Resultado clave | Documento de cierre |
|---|---|---|---|
| **S01** | CRISP-DM, EDA, hipótesis, faltantes, baseline | Target Top 10%; NB + Lognormal; imputación > listwise | [`Insights_EDA.md`](sections/S01-Metodologia_EDA_Analisis/1_2_EDA/results/Insights_EDA.md) · [resumen](docs/summaries/S01_Resumen_Ejecutivo.md) |
| **S02** | Fuentes DANE, VAR, nowcast, RAG | VAR(1) en diferencias; **DFM** MAPE≈6.6%; asistente Streamlit | [`nowcast.md`](sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/results/nowcast.md) · [resumen](docs/summaries/S02_Resumen_Ejecutivo.md) |
| **S03** | Pure premium y proyección de portafolio | Holdout costo pred/obs≈0.99; CR base≈80% / adverso≈102% | [`proyeccion_portafolio.md`](sections/S03-Reto_de_Negocio/3_3_Proyeccion%20de%20portafolio/results/proyeccion_portafolio.md) · [resumen](docs/summaries/S03_Resumen_Ejecutivo.md) |
| **S04** | Efecto causal del programa de prevención | ATT frecuencia **−0.428** (≈−11.7%); valor ~1.26B COP/año | [`estimacion_efecto.md`](sections/S04-Impacto_Inferencia_Causal/4_2_Implementacion%20y%20estamacion%20de%20efecto/results/estimacion_efecto.md) · [resumen](docs/summaries/S04_Resumen_Ejecutivo.md) |
| **S05** | Recomendador warm/cold | **Diseño C** híbrido, α\*=0.70 | [`prototipo_recomendador.md`](sections/S05-Sistema_Recomendador/5_2_Implementacion%20de%20prototipo/results/prototipo_recomendador.md) · [resumen](docs/summaries/S05_Resumen_Ejecutivo.md) |
| **S06** | Arquitectura y operación en Azure | Nowcast batch on-demand + RAG web service | [`arquitectura_producto.md`](sections/S06-Modelo_a_Producto/6_1_Arquitectura%20de%20produccion/results/arquitectura_producto.md) · [resumen](docs/summaries/S06_Resumen_Ejecutivo.md) |
| **S07** | Comunicación a junta / stakeholders | Brief ejecutivo + HTML one-pager | [`resumen_manual_stakeholder.md`](sections/S07-Comunicacion/7_1_Resumen%20ejecutivo/resources/resumen_manual_stakeholder.md) |

---

## Estructura del repositorio

```
.
├── apps/Asistente_RAG/          # App Streamlit + ADK + Chroma (S02-2.4)
├── data/
│   ├── raw/                     # CSV sintéticos — INMUTABLES
│   └── staging/S01…S05/         # Parquet intermedios (versionados)
├── design_system/assets/        # Logo SURA (fuente de verdad visual)
├── docs/
│   ├── Prueba tecnica/          # Enunciado PDF + LEEME
│   ├── diccionario_datos.md
│   ├── staging_data.md          # Catálogo de datasets de staging
│   └── summaries/               # Resúmenes ejecutivos S01–S06
├── logs/uso_de_ia/S0X/<id>/     # prompt.md + output.md por tarea con IA
├── packages/sura_brand/         # Manual de marca programático (pip -e)
├── sections/S01…S07/            # code/ + results/ (+ resources/ cuando aplica)
└── requirements.txt
```

Cada subsección analítica sigue:

```
sections/<S0X>/<subsección>/
├── code/       # Scripts .py ejecutables desde la raíz del repo
├── results/    # Markdown, PNG, tablas
└── resources/  # (opcional) insumos manuales / drafts
```

---

## Requisitos del entorno

| Requisito | Detalle |
|---|---|
| SO | macOS / Linux (rutas tipo POSIX; Windows vía Git Bash o WSL) |
| Python | ≥ 3.9; **recomendado 3.12** |
| Memoria | ≥ 8 GB RAM para pipelines S03–S05 |
| Red | Solo necesaria para `pip install` y para el asistente RAG (API Gemini) |
| API key | Opcional: `GOOGLE_API_KEY` en `apps/Asistente_RAG/.env` (solo S02-2.4) |

Dependencias principales: `pandas`, `numpy`, `scipy`, `scikit-learn`, `statsmodels`, `matplotlib`, `seaborn`, `pyarrow`, `csdid`, más el stack RAG (`streamlit`, `chromadb`, `google-adk`, `google-genai`).

El paquete editable `sura_brand` se instala vía `requirements.txt` (`-e ./packages/sura_brand`). Es **obligatorio** para regenerar figuras con el estilo corporativo.

---

## Datos

### Raw (entrada)

| Archivo | Contenido |
|---|---|
| `data/raw/empresas.csv` | ~5 000 empresas afiliadas |
| `data/raw/siniestros.csv` | ~40 000 eventos |
| `data/raw/uso_servicios.csv` | Uso de servicios de prevención |
| `data/raw/programas_prevencion.csv` | Adopción de programas |
| `data/raw/catalogo_servicios.csv` | Catálogo (~40 servicios) |
| `data/raw/macro_sectorial.csv` | Macro por sector / trimestre |

Ver campos en [`docs/diccionario_datos.md`](docs/diccionario_datos.md). **No modificar** `data/raw/`.

### Staging (intermedios)

Generados por los scripts de cada sección y versionados en `data/staging/S0X/`. Catálogo completo: [`docs/staging_data.md`](docs/staging_data.md).

Fuentes preferidas para modelado aguas abajo (post-imputación S01-1.4):

- `data/staging/S01/empresas_imputadas.parquet`
- `data/staging/S01/siniestros_imputados.parquet`

---

## Reproducción completa

Ejecutar **siempre desde la raíz del repositorio** con el intérprete del venv:

```bash
.venv/bin/python path/al/script.py
```

Los scripts usan rutas relativas vía `pathlib` y escriben en `data/staging/` y `sections/**/results/`. El orden importa: cada sección consume staging de la anterior.

### S01 — Metodología, EDA y baseline

```bash
# 1.2 EDA
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/01-analisis_univariado/analisis_univariado.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/02-analisis_bivariado/analisis_bivariado.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/03-analisis_temporal/analisis_temporal.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/04-analisis_outliers/analisis_outliers.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/05-analisis_correlaciones/analisis_correlaciones.py"

# 1.3 Pruebas de hipótesis
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/code/01-hip_arquitectura_modelo/hip_arquitectura_modelo.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/code/02-hip_features/hip_features.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/code/03-hip_confirmaciones/hip_confirmaciones.py"

# 1.4 Datos faltantes
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/01-cuantificacion/cuantificacion_faltantes.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/02-mecanismos/mecanismos_faltantes.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/03-estrategia_imputacion/estrategia_imputacion.py"
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/04_impacto/impacto_imputacion.py"

# 1.5 Baseline
.venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_5_Definición de baseline/code/01-cuantificacion_baseline/cuantificacion_baseline.py"
```

Documentos: `1_1_CRISP-DM/results/crisp-dm.md`, `Insights_EDA.md`, `Insights_pruebas_hipotesis.md`, `Insights_datos_faltantes.md`, `Baseline.md`.

### S02 — Modelación económica y sectorial

```bash
# 2.1 EDA de fuentes (CEED / ELIC / IPOC / EC)
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/code/03-EDA_fuentes/eda_fuentes.py"

# 2.2 VAR + robustez
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/code/01-modelamiento/modelamiento_relaciones.py"
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/code/02-estacionariedad/estacionariedad_robustez.py"

# 2.3 Nowcast (RF → BSTS → DFM → comparativo)
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/01_random_forest.py"
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/02_bsts.py"
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/03_dfm.py"
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/04_comparativo.py"
```

#### Asistente RAG (S02-2.4)

```bash
cp apps/Asistente_RAG/.env.example apps/Asistente_RAG/.env
# Editar .env y cargar GOOGLE_API_KEY (Google AI Studio)

.venv/bin/python apps/Asistente_RAG/scripts/seed_corpus.py
.venv/bin/streamlit run apps/Asistente_RAG/app.py

# Evaluación smoke (traces)
.venv/bin/python apps/Asistente_RAG/eval/run_eval.py
```

Detalle: [`apps/Asistente_RAG/README.md`](apps/Asistente_RAG/README.md). Chroma y uploads locales están en `.gitignore`.

### S03 — Reto de negocio (frecuencia × severidad)

```bash
.venv/bin/python "sections/S03-Reto_de_Negocio/3_1_Pregunta de negocio/code/01-supuestos/01-supuestos.py"
.venv/bin/python "sections/S03-Reto_de_Negocio/3_2_Modelado frecuencia_severidad/code/01-modelo/01-modelo.py"
.venv/bin/python "sections/S03-Reto_de_Negocio/3_3_Proyeccion de portafolio/code/01-proyeccion/01-proyeccion.py"
```

### S04 — Inferencia causal

```bash
.venv/bin/python "sections/S04-Impacto_Inferencia_Causal/4_2_Implementacion y estamacion de efecto/code/01-estimacion/01-estimacion.py"
.venv/bin/python "sections/S04-Impacto_Inferencia_Causal/4_3_Efecto a valor economico/code/01-val_economico/01-val_economico.py"
```

La estrategia de identificación (4.1) es documental: `estrategia_identificacion_causal.md`.

### S05 — Sistema recomendador

```bash
.venv/bin/python "sections/S05-Sistema_Recomendador/5_1_Diseño de recomendador/code/01-diseños/01-diseños.py"
.venv/bin/python "sections/S05-Sistema_Recomendador/5_2_Implementacion de prototipo/code/01-prototipo/01-prototipo.py"
```

La propuesta de paso a producción (5.3) es documental: `paso_produccion.md`.

### S06 / S07 — Producto y comunicación

Sin pipelines numéricos adicionales: arquitectura/operación en Azure (`arquitectura_producto.md`, `operacion_modelo.md`) y brief de junta (`resumen_manual_stakeholder.md` + `resumen_ejecutivo.html`).

---

## Decisiones de modelado (contrato analítico)

Resumen operativo; el detalle condicionante está en los insights de S01–S02 (ver `.agents/AGENTS.md`).

| Decisión | Elección |
|---|---|
| Target clasificación | Top 10% `n_siniestros` año T |
| Validación | Temporal T−1 → T (anti-leakage) |
| Frecuencia | **Binomial Negativa** (+ offset exposición) |
| Severidad | **Lognormal** separada AT / EL |
| Nowcast operativo | **DFM** 1 factor + puente OLS (no RF en prod) |
| Causal | DiD escalonado **Callaway–Sant’Anna** |
| Recomendador | Diseño **C** híbrido adopción × riesgo, α\*=0.70 |
| Productos a Azure | Nowcast + RAG (no el recomendador en el primer release) |

---

## Visualizaciones y marca

```python
import sura_brand as sb

sb.apply_sura_style()                 # tema claro
# sb.apply_sura_style("dark")         # tema oscuro
```

Colores primarios: `#0033A0` (azul), `#00AEC7` (aqua), `#001E60` (profundo), `#E3E829` (amarillo, uso moderado). Guía del paquete: [`packages/sura_brand/README.md`](packages/sura_brand/README.md).

---

## Uso de IA

Toda asistencia con IA queda registrada en:

```
logs/uso_de_ia/S0X/<id>/
├── prompt.md    # prompt verbatim
└── output.md    # modelo, justificación, qué se tomó / descartó
```

Ejemplo: `logs/uso_de_ia/S04/4.2.1/`. Cumple el requisito del enunciado de documentar dónde, por qué y qué se usó de herramientas de IA.

---

## Cómo navegar la entrega (recomendado para evaluadores)

| Orden | Qué abrir | Para qué |
|---:|---|---|
| 1 | Este `README.md` | Setup y mapa |
| 2 | [`docs/summaries/`](docs/summaries/) | Lectura ejecutiva S01–S06 |
| 3 | `sections/**/results/*.md` | Evidencia técnica y figuras |
| 4 | `data/staging/` + scripts `code/` | Auditoría de reproducibilidad |
| 5 | `apps/Asistente_RAG/` | Prototipo de producto conversacional |
| 6 | `logs/uso_de_ia/` | Transparencia de uso de IA |
| 7 | `git log --oneline` | Historia de trabajo por sección |

---

## Verificación rápida post-instalación

```bash
# Paquetes críticos
.venv/bin/python -c "import pandas, sklearn, statsmodels, csdid, sura_brand; print('OK')"

# Staging presente
ls data/staging/S01 data/staging/S02 data/staging/S03 data/staging/S04 data/staging/S05

# Smoke de un script liviano (opcional; regenera artefactos S02-2.1)
.venv/bin/python "sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/code/03-EDA_fuentes/eda_fuentes.py"
```

Si un script falla por dependencia faltante, reinstalar con `pip install -r requirements.txt` desde la raíz (con el venv activo).

---

## Limitaciones conocidas

- Los datos son **sintéticos**; las magnitudes en COP y los ATT no representan cartera real.
- El asistente RAG requiere API key de Google; sin ella, la UI puede operar en modo degradado / extractivo según la configuración del prototipo.
- S06 documenta arquitectura Azure corporativa; el prototipo local del RAG usa Gemini + Chroma (no Azure AI Foundry).
- `requirements.txt` fija versiones de ciencia de datos; el stack RAG usa cotas mínimas (`>=`) y puede variar levemente según la fecha de instalación.

---

## Licencia y confidencialidad

Prueba técnica individual. Datos sintéticos sin información real de empresas ni personas. El paquete `sura_brand` se declara de uso interno según su `pyproject.toml`.
