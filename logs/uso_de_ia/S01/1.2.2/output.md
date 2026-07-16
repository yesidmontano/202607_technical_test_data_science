# Output – Registro de Uso de IA

**ID:** `1.2.2`
**Tarea:** Análisis Univariado EDA – S01 / 1.2 EDA
**Sección del repositorio:** `sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/01-analisis_univariado/`

---

## 1. Modelo utilizado

- **Modelo:** Claude Sonnet 4.5 (Thinking)
- **Modo:** Conversación interactiva con ejecución de comandos en terminal

---

## 2. Por qué se usó

Se utilizó IA asistida para acelerar la escritura del script de análisis univariado completo (`analisis_univariado.py`) que cubre cuatro dimensiones analíticas (frecuencia, severidad, costos, tamaño) con 15 visualizaciones y 3 datasets de staging, respetando todas las convenciones del repositorio (rutas relativas, semilla fija, sura_brand, PEP 8). La complejidad y el volumen de código justifican el apoyo automatizado para el scaffolding y la iteración rápida.

---

## 3. Qué se tomó

### Scripts generados
| Archivo | Nivel de modificación |
|---|---|
| `analisis_univariado.py` | Generado íntegramente por IA, con depuración iterativa (6 ciclos de corrección) |

### Correcciones manuales requeridas (aplicadas por la IA en ciclos)
1. **Profundidad de ruta** (`parents[6]` → `parents[5]`): el cálculo inicial de la ruta raíz del proyecto era incorrecto.
2. **Dependencias faltantes**: `scipy` y `pyarrow` no estaban instaladas en `.venv`; se instalaron con `pip`.
3. **API `create_dashboard`**: retorna `List[Axes]`, no `ndarray`. Se eliminaron todos los usos de `.flat`.
4. **API `line_chart`**: el segundo argumento es `y=`, no `y_dict=`.
5. **API `boxplot_chart`**: el primer argumento posicional es `data=`, no `df=`.
6. **`np.trapz` eliminado en NumPy 2.0**: reemplazado por `np.trapezoid`.
7. **`bar_chart` horizontal**: el argumento `x` debe ser las etiquetas (strings), no los valores numéricos.

### Documentación generada
- `docs/staging_data.md`: íntegramente por IA, revisada.
- `sections/.../results/Insights_EDA.md`: hallazgos generados por IA con base en las estadísticas de salida del script.

---

## 4. Qué se descartó o requirió corrección manual

- El primer intento de cálculo de `parents[N]` requirió verificación manual contando los niveles del árbol de directorios.
- Se descartó el uso de `axes.flat` (patrón de numpy) a favor de indexación directa de lista (`axes[i]`).
- Se identificó y corrigió la incompatibilidad de la firma de `bar_chart` (x=labels, y=values) en el caso horizontal.

---

## 5. Artefactos producidos

### Datasets de staging
| Archivo | Filas | Columnas |
|---|---|---|
| `data/staging/S01/empresas_staging.parquet` | 5 000 | 13 |
| `data/staging/S01/siniestros_staging.parquet` | 39 894 | 14 |
| `data/staging/S01/siniestralidad_empresa.parquet` | 4 625 | 19 |

### Visualizaciones (15 figuras PNG a 150 DPI)
| Código | Figura |
|---|---|
| A1 | Histograma + Q-Q frecuencia de siniestros por empresa |
| A2 | Frecuencia relativa por clase de riesgo |
| A3 | Evolución anual de siniestros |
| B1 | Distribución severidad (natural + log + CDF) |
| B2 | Severidad AT vs EL |
| B3 | Boxplot severidad por gravedad |
| C1 | Distribución costos por componente (4 paneles) |
| C2 | Costo acumulado por empresa (natural + log) |
| C3 | Curva de Lorenz – concentración de costos |
| D1 | Distribución trabajadores (natural + log + segmentación) |
| D2 | Prima anual (natural + log) |
| D3 | Antigüedad por clase de riesgo |
| E1 | Donut tipo de siniestro (AT / EL) |
| E2 | Barras por nivel de gravedad |
| E3 | Barras horizontales por sector económico |

---

## 6. Estadísticas clave obtenidas

| Métrica | Valor |
|---|---|
| Empresas sin siniestros | 7.5% |
| Mediana costo total / siniestro | $1,271,940 COP |
| P90 costo total / siniestro | $7,232,311 COP |
| Top 10% empresas concentran | 56.5% del costo total |
| Mediana días incapacidad | 6 días |
| P90 días incapacidad | 37 días |
| Asimetría severidad | 10.42 |
| Empresas micro (≤10 trab.) | 12.0% |
| Empresas PyME (11–200 trab.) | 86.4% |
| Índice de Gini – costos empresa | 0.702 |

---

## 7. Lecciones y advertencias

- **Verificar siempre la API de `sura_brand`** antes de usar sus funciones en scripts nuevos: las firmas difieren de la documentación del `AGENTS.md` en algunos detalles (e.g., `y=` vs `y_dict=`).
- **NumPy 2.0** elimina varias funciones deprecadas (`np.trapz`, etc.); revisar compatibilidad al inicio de cada script.
- El patrón `.flat` de numpy no aplica sobre listas de Python; `create_dashboard` devuelve `List[Axes]`.
- `pyarrow` y `scipy` **no están en el entorno base** del proyecto; agregarlos a `requirements.txt`.

---

*Registro · S01-1.2.2 · Prueba Técnica Grupo SURA.*
