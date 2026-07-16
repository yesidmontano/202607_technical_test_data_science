# AGENTS.md – Reglas del Proyecto

---

## Ejes centrales

- **modelación económica y sectorial**
- **modelación para un reto de negocio**
- **medición causal de impacto**
- **diseño de un sistema de recomendación de servicios**.

### Contexto de Negocio

La ARL asegura a empresas afiliadas frente a accidentes de trabajo y enfermedades laborales. Cobra primas según la clase de riesgo y la actividad económica de cada empresa, y ofrece programas y servicios de prevención. La Dirección de Analítica quiere:

- Entender los **determinantes económicos y sectoriales** de la siniestralidad.
- **Proyectar el resultado técnico** del portafolio.
- **Medir el impacto real** de sus programas de prevención.
- **Recomendar a cada empresa** los servicios con mayor probabilidad de ser adoptados y de reducir su riesgo.

Para la prueba se entregan datos sintéticos que emulan estas fuentes.
 
**Restricción clave:** código ejecutable en `.py` (no notebooks), reproducible
con semilla fija, rutas relativas y entorno documentado.

---

## Estructura del Repositorio

```
.
├── apps/                          # Aplicaciones desplegables 
├── data/
│   ├── raw/                       # Datos originales — NUNCA modificar
│   │   ├── catalogo_servicios.csv
│   │   ├── empresas.csv
│   │   ├── macro_sectorial.csv
│   │   ├── programas_prevencion.csv
│   │   ├── siniestros.csv
│   │   └── uso_servicios.csv
│   └── staging/                   # Datos procesados / features
├── design_system/
│   └── assets/logo.png            # Logo oficial SURA (fuente de verdad)
├── docs/                          # Enunciado y documentación de referencia
├── logs/
│   └── uso_de_ia/
│       └── <id>/
│           ├── prompt.md          # Prompt exacto enviado a la IA
│           └── output.md          # Resumen de lo obtenido de la IA
├── packages/
│   └── sura_brand/                # Paquete de manual de marca (pip install -e)
│       └── sura_brand/            # Código fuente del paquete
├── sections/
│   ├── S01-Metodologia_EDA_Analisis/
│   │   ├── 1_1_CRISP-DM/
│   │   ├── 1_2_EDA/
│   │   ├── 1_3_Pruebas de hipotesis/
│   │   ├── 1_4_Diagnostico datos faltantes/
│   │   └── 1_5_Definición de baseline/
│   ├── S02-Modelacion_Economica_Sectorial/
│   │   ├── 2_1_Caracterizacion/
│   │   ├── 2_2_Modelamiento de relaciones/
│   │   ├── 2_3_Nowcast/
│   │   └── 2_4_Asistente RAG/
│   ├── S03-Reto_de_Negocio/
│   │   ├── 3_1_Pregunta de negocio/
│   │   ├── 3_2_Modelado frecuencia_severidad/
│   │   ├── 3_3_Proyeccion de portafolio/
│   │   └── 3_4_Documentación y recomendacion/
│   ├── S04-Impacto_Inferencia_Causal/
│   │   ├── 4_1_Estrategia de identificacion causal/
│   │   ├── 4_2_Implementacion y estamacion de efecto/
│   │   └── 4_3_Efecto a valor economico/
│   ├── S05-Sistema_Recomendador/
│   │   ├── 5_1_Diseño de recomendador/
│   │   ├── 5_2_Implementacion de prototipo/
│   │   └── 5_3_Propuesta paso a produccion/
│   ├── S06-Modelo_a_Producto/
│   │   ├── 6_1_Arquitectura de produccion/
│   │   └── 6_2_Definicion operacion de modelo/
│   └── S07-Comunicacion/
│       └── 7_1_Resumen ejecutivo/
└── .venv/                         # Entorno virtual Python (ignorado en git)
```

Cada sección tiene la sub-estructura:
```
<seccion>/<subseccion>/
├── code/        # Scripts .py ejecutables
└── results/     # Artefactos: .md, imágenes, tablas de resultados
```

---

## Reglas Generales

### Idioma
- Todo el **código** (variables, funciones, clases, comentarios inline) se escribe en **inglés**.
- Toda la **documentación** (docstrings, archivos `.md`, resultados, commits) se escribe en **español**.
- Los nombres de archivos siguen el patrón del repositorio: `snake_case` para scripts, `PascalCase` para clases.

### Código Python
- **No crear notebooks** (`.ipynb`). Todo el código va en scripts `.py`.
- Usar **rutas relativas** en todo momento; nunca rutas absolutas hardcodeadas.
- Establecer una **semilla fija** al inicio de cada script que involucre aleatoriedad:
  ```python
  RANDOM_SEED = 42
  ```
- Seguir **PEP 8**. Máximo 100 caracteres por línea.
- Todo script debe ser **importable y ejecutable** de forma independiente.
- El **entorno virtual** es `.venv/` en la raíz; usar siempre `.venv/bin/python` para ejecutar.

### Datos
- Los archivos en `data/raw/` son **inmutables**. Nunca modificarlos ni sobreescribirlos.
- Cualquier transformación produce archivos en `data/staging/`.
- Leer siempre con rutas relativas desde la raíz del proyecto:
  ```python
  from pathlib import Path
  ROOT = Path(__file__).resolve().parents[N]  # ajustar N según profundidad
  DATA_RAW = ROOT / "data" / "raw"
  ```

### Commits y Versionado
- El repositorio debe mantener **historia de commits legible**.
- Formato de mensaje de commit: `[sección] acción concisa en imperativo`
  - Ejemplo: `[S01-EDA] agregar análisis univariado de siniestros`
- No commitear archivos de datos, `.venv/`, ni caches (`__pycache__`, `.DS_Store`).

---

## Sistema de Marca SURA (`sura_brand`)

El paquete `packages/sura_brand` es el **manual de marca programático** del proyecto.
Es **obligatorio** usarlo en **todas las visualizaciones** a partir de la sección 1.2 EDA.

### Instalación (ya realizada en .venv)
```bash
pip install -e packages/sura_brand
```

### Uso obligatorio en cada script con visualizaciones
```python
import sura_brand as sb

# Primera línea antes de cualquier figura
sb.apply_sura_style()          # tema claro (presentaciones, reportes)
# o
sb.apply_sura_style("dark")    # tema oscuro (fondos oscuros)
```

### Colores de referencia
| Token | HEX | Uso |
|-------|-----|-----|
| `AZUL_SURA` | `#0033A0` | Color primario — ejes, títulos, barras principales |
| `AQUA_SURA` | `#00AEC7` | Color primario — acento, líneas KDE, símbolos |
| `AZUL_PROFUNDO` | `#001E60` | Énfasis tipográfico, fondos oscuros |
| `AQUA_ALTERNO` | `#05C3DE` | Secundario — elementos interactivos |
| `AMARILLO_SURA` | `#E3E829` | Alertas y contrastes (usar con moderación) |

### API disponible
```python
import sura_brand as sb

# Colores
sb.AZUL_SURA.hex          # '#0033A0'
sb.get_color("aqua_sura") # Objeto Color completo

# Paletas (para seaborn, matplotlib)
sb.get_palette("categorical")          # 6 colores principales
sb.get_palette("traffic_light")        # verde/naranja/rojo
sb.get_cmap("sura_diverging")          # Para heatmaps de correlación
sb.get_cmap("sura_blues")              # Para densidades / choropleth
sb.make_n_colors(n)                    # N colores interpolados exactos

# Gráficas listas (retornan fig, ax)
sb.bar_chart(x, y, title=..., horizontal=True)
sb.line_chart(x, y_dict, title=...)
sb.dist_chart(data, title=..., kde=True)
sb.correlation_heatmap(df, title=...)
sb.scatter_chart(x, y, hue=...)
sb.boxplot_chart(df, x=..., y=...)
sb.pie_chart(values, labels, donut=True)

# Decoradores
sb.add_logo_watermark(fig, position="bottom-right")
sb.add_sura_footer(fig, text="S01 EDA | Grupo SURA")

# Layout / dashboards
sb.create_dashboard(nrows, ncols, title=..., subtitle=...)
sb.create_report_figure(title=..., subtitle=...)
sb.create_kpi_figure({"Métrica": valor, ...})
```

---

## Registro de Uso de IA

**Toda interacción con herramientas de IA debe quedar registrada.**

### Estructura de un registro
Cada tarea asistida por IA crea dos archivos bajo `logs/uso_de_ia/<id>/`:

```
logs/uso_de_ia/
└── <sección>.<subsección>.<item>/    # Ej: 1.2.1, 3.2.1, 4.1.1
    ├── prompt.md                      # Prompt enviado (verbatim)
    └── output.md                      # Resumen: qué se usó, por qué, qué se tomó
```

### Formato de `output.md`
Cada `output.md` debe incluir:
1. **Modelo utilizado** (solo el modelo, p. ej. Grok 4.5, Claude Sonnet 4.5 — **sin** plataforma/IDE)
2. **Por qué se usó** (justificación de la decisión)
3. **Qué se tomó** (código, ideas, texto — con nivel de modificación)
4. **Qué se descartó** o requirió corrección manual
5. **Lecciones** o advertencias relevantes

### Identificación de registros
El `<id>` sigue el esquema `<S>.<sub>.<item>` donde `<S>` es el número de sección principal:
- `1.2.1` → Sección 1 (EDA), subsección 1.2 (EDA), ítem 1 (paquete sura_brand)
- `3.2.1` → Sección 3 (Reto de negocio), subsección 3.2 (modelado frecuencia/severidad), ítem 1

---

## Convenciones por Tipo de Archivo

### Scripts de análisis (`code/`)
```python
"""
<título del análisis>
========================
Sección: <S0X - nombre>
Subsección: <X.Y - nombre>

Descripción:
    <Qué hace este script y qué produce>

Inputs:
    - data/raw/<archivo>.csv

Outputs:
    - results/<artefacto>.<ext>

Uso:
    python sections/S0X-.../code/<script>.py
"""
import sura_brand as sb
# ... resto del código
```

### Archivos de resultados (`results/`)
- **Imágenes**: `<nombre_descriptivo>.png` guardadas con `savefig(dpi=150)` vía `sb` o Matplotlib.
- **Tablas**: `<nombre>.md` o `<nombre>.csv` con encabezados en español.
- **Markdown de insights**: `<Nombre_Resultado>.md` que comienza con `### Requerimiento` y luego documenta hallazgos.

### Tipografía de resultados en Markdown
- Usar **negritas** para conclusiones clave.
- Usar tablas Markdown para comparaciones numéricas.
- Cada hallazgo debe ir acompañado de la visualización que lo sustenta (referencia a imagen).

---

## Condicionantes del Modelado (EDA + Pruebas de Hipótesis → S02-S05)

> **Referencia autoritativa 1 (EDA):** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/results/Insights_EDA.md`
> Sección **"Síntesis Consolidada – Lo que Condiciona el Modelado"** (19 condicionantes).
>
> **Referencia autoritativa 2 (Pruebas de Hipótesis):** `sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/results/Insights_pruebas_hipotesis.md`
> Sección **"Síntesis Consolidada de Hallazgos – S01-1.3"** (12 pruebas; confirma, descarta y condiciona decisiones de S03–S05).
>
> Leer **ambos** documentos antes de iniciar cualquier tarea de modelado en S02, S03, S04 o S05.

### Feature Set Obligatorio (contrato EDA → S03)

| Feature | Transformación | Rol | Prioridad |
|---|---|---|---|
| `clase_riesgo` | Ordinal (1–5) | Predictor estructural | **Obligatorio** |
| `sector` | Target encoding / embeddings CIIU | Predictor estructural | **Obligatorio** |
| `log_n_trabajadores_w` | log + winsor P1–P99 | Offset de exposición | **Obligatorio** |
| `log_lag_n_siniestros` | log(1+lag_n), shift estricto t-1 | Baseline predictivo | **Obligatorio** |
| `log_prima_anual_w` | log + winsor P1–P99 | Proxy riesgo/tamaño | Opcional (vigilar VIF) |
| `antiguedad_meses` | Sin transformación | Control de cohorte | Opcional |
| `departamento` | Dummy nacional | Control geográfico | Baja prioridad |
| `mes` / `año` | Dummies o excluir | Control temporal | Baja prioridad |

### Decisiones de Diseño Derivadas del EDA y Confirmadas por Pruebas de Hipótesis

- **Modelo de frecuencia:** **Binomial Negativa** obligatoria (φ=17.4, ΔAIC=−34 151 vs Poisson — P1). **Nunca OLS directa ni Poisson.**
- **Componente Zero-Inflated:** **No** añadir ZIP/ZINB. La NB predice más ceros que los observados (7.5% obs < 12% NB — P2).
- **Modelo de severidad:** **Lognormal** como familia preferida para costo (ΔAIC=+11 257 vs Gamma — P12). Modelos **separados por tipo AT vs EL** (Cliff's δ=0.24, medianas 10 vs 6 días — P6).
- **Métrica principal:** Recall / Precisión / F1 en el **decil superior** de costo (no accuracy global). Gini ≈ 0.70; top 10% = 56.5% del costo.
- **Validación:** esquema temporal T-1 → T estricto. El año de holdout importa (oscilación YoY ≈ ±15%).
- **Anti-leakage:** `log_lag_n_siniestros` calculado con shift estricto año t-1. No usar variables del año de predicción.
- **Colinealidad:** VIF máx ≈ 1.7 — no hace falta eliminar predictores. Todos los candidatos son incluibles.
- **Geografía:** η²=0.002, 0/21 pares Dunn significativos tras Holm (P11) — feature de baja prioridad; usar solo como control descriptivo, **no** como predictor principal.
- **Estacionalidad mensual:** descartada — amplitud 3.8 pp, Kendall W=0.037 (P8). **No** incluir dummies de mes.
- **Clase de riesgo:** 5 niveles distinguibles (η²=0.53, δ≈0.40 en saltos adyacentes — P3). **No colapsar** clases.
- **Winsorización:** P1–P99 en variables numéricas de siniestro y empresa. Usar columnas `*_w` del staging. No borrar filas.
- **PyMEs dominan** (86.4% del portafolio): recomendaciones en S05 deben ser factibles para empresas con recursos limitados. Flag `es_micro` útil para estratificación (P7, δ=0.25).

### Datasets de Staging Listos para Modelado

| Archivo en `data/staging/` | Contenido |
|---|---|
| `empresa_siniestralidad_tratada` | Panel transversal + columnas `*_w` winsorizadas |
| `temporal_empresa_anio` | Panel empresa×año con lag y target `alta_siniestralidad` (Top 10%) |
| `siniestros_tratados` | Siniestros con columnas `*_w` + flags de outliers |
| `predictores_recomendacion` | Feature set listo para S03 / S05 |

---

## Dominio del Negocio

### Datasets disponibles (todos sintéticos)
| Archivo | Contenido clave |
|---------|-----------------|
| `empresas.csv` | Empresas aseguradas: sector, tamaño, clase de riesgo, geografía |
| `siniestros.csv` | Eventos de siniestro: fecha, costo, tipo, empresa |
| `uso_servicios.csv` | Uso de servicios SURA por empresa |
| `programas_prevencion.csv` | Participación en programas de prevención |
| `macro_sectorial.csv` | Variables macroeconómicas sectoriales |
| `catalogo_servicios.csv` | Catálogo de servicios disponibles |

### Variable objetivo
- **Clasificación binaria**: 1 si la empresa tendrá alta siniestralidad el próximo año, 0 si no.
- **Definición operativa de "alta siniestralidad"**: Top 10% de las empresas con mayor número de siniestros en el año (definición fijada en CRISP-DM / EDA).
- **Unidad de análisis**: `id_empresa`.

### Esquema de validación temporal
- Entrenar con datos hasta año **T-1**, validar con año **T**.
- **No usar datos futuros** en features de entrenamiento (riesgo de data leakage).
- La principal fuente de leakage son los datos de siniestros del año de predicción.

### Métricas de éxito
- **Técnicas**: AUC-ROC, Recall, Precisión, F1-Score.
- **Negocio**: Costo evitado por reducción de siniestralidad, % de mejora vs. baseline.
- **Baseline**: Modelo que predice alta siniestralidad para todas las empresas.

---

## Buenas Prácticas de Reproducibilidad

1. **Semilla fija** en todo proceso estocástico: `RANDOM_SEED = 42`.
2. **Entorno documentado**: mantener `requirements.txt` o `pyproject.toml` actualizado.
3. **Rutas relativas** siempre; usar `pathlib.Path`.
4. **No hardcodear** parámetros del modelo en el script — usar constantes o configs.
5. **Loggear** pasos relevantes con `print()` o `logging`, especificando métricas finales.
6. Cada script debe poder ejecutarse limpiamente con:
   ```bash
   .venv/bin/python sections/<S>/<sub>/code/<script>.py
   ```

---

## Prohibiciones Explícitas

- ❌ Modificar archivos en `data/raw/`.
- ❌ Crear archivos `.ipynb` (notebooks de Jupyter).
- ❌ Usar rutas absolutas en el código.
- ❌ Crear visualizaciones sin aplicar el estilo `sura_brand`.
- ❌ Subir al repositorio: `.venv/`, `__pycache__/`, `.DS_Store`, archivos de datos masivos.
- ❌ Hacer data leakage: no usar variables del período de predicción como features.
- ❌ Dejar código de debug (`breakpoint()`, `pdb`, prints innecesarios) en scripts finales.
