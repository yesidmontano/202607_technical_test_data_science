# Output – Paquete de Manual de Marca SURA para Visualizaciones EDA

**Tarea:** 1.2.1 – Creación del paquete `sura_brand`  
**Modelo:** Claude Sonnet 4.6 (Thinking)

---

## Resumen Ejecutivo

Se investigó la identidad visual corporativa de **Grupo SURA** y se desarrolló el paquete Python `sura_brand`, instalable en el entorno del proyecto, que actúa como **manual de marca programático** para garantizar consistencia visual en todas las visualizaciones del EDA y análisis subsecuentes.

---

## Investigación de Marca SURA

### Fuentes consultadas
- Portal oficial ADN SURA (`adn.sura.com/manual-de-marca`)
- Documentación técnica de identidad visual de `sura.com`
- Guías Pantone y valores RGB oficiales de Grupo SURA

### Hallazgos clave

| Elemento | Descripción |
|----------|-------------|
| **Logotipo** | Símbolo (abstracción del cóndor) + tipografía exclusiva SURA |
| **Símbolo** | Evoca movimiento, flecha y letra "S"; representa el cóndor |
| **Tipografía oficial** | Exclusiva SURA + **Barlow Medium** para el descriptor "GRUPO" |
| **Color primario 1** | Azul SURA – Pantone 286 C – `#0033A0` – RGB(0, 51, 160) |
| **Color primario 2** | Aqua SURA – Pantone 3125 C – `#00AEC7` – RGB(0, 174, 199) |

---

## Paquete Implementado: `sura_brand`

### Ubicación
```
packages/sura_brand/
├── sura_brand/              ← Código fuente del paquete
│   ├── __init__.py          ← Punto de entrada y shortcuts
│   ├── colors.py            ← Definición de colores de marca
│   ├── typography.py        ← Tipografía y escala de texto
│   ├── palettes.py          ← Paletas categóricas y colormaps
│   ├── styles.py            ← Configuración global Matplotlib/Seaborn
│   ├── charts.py            ← Funciones de alto nivel para gráficas
│   ├── layout.py            ← Dashboards y figuras multi-panel
│   └── assets/logo.png      ← Logo oficial SURA
├── README.md
├── setup.py
└── pyproject.toml
```

### Instalación
```bash
pip install -e packages/sura_brand
```

---

## Componentes Implementados

### 1. `colors.py` – Colores de Marca

Define la clase `Color` (dataclass inmutable) con atributos `hex`, `rgb`, `rgb_normalized`, `pantone` y `role`. Incluye:

| Categoría | Colores |
|-----------|---------|
| **Primarios** | `AZUL_SURA` (#0033A0), `AQUA_SURA` (#00AEC7) |
| **Secundarios** | `AZUL_PROFUNDO` (#001E60), `AQUA_ALTERNO` (#05C3DE), `AMARILLO_SURA` (#E3E829) |
| **Neutros** | `GRIS_CLARO` (#C7C9C7), `GRIS_MEDIO` (#6B6D6F), `BLANCO`, `NEGRO` |
| **Semánticos** | `POSITIVO` (#00875A), `NEGATIVO` (#DE350B), `ADVERTENCIA` (#FF8B00), `INFORMACION` (#0065FF) |

```python
from sura_brand.colors import AZUL_SURA, get_color, list_colors
print(AZUL_SURA.hex)          # '#0033A0'
print(AZUL_SURA.rgb_normalized) # (0.0, 0.2, 0.627...)
```

---

### 2. `typography.py` – Tipografía

Define fuentes y escala tipográfica con `FontSpec` y `TypeScale`:

- **Barlow** (primaria): usada en el logo oficial de SURA
- **Inter** (secundaria): alta legibilidad para dashboards
- **DIN Alternate** (numérica): KPIs y métricas
- **JetBrains Mono** (código/técnica)

Escala de tamaños: figura (16pt), subtítulo (13pt), eje (12pt), tick/leyenda (10pt), anotaciones (9pt).

```python
from sura_brand.typography import get_matplotlib_font_params
import matplotlib as mpl
mpl.rcParams.update(get_matplotlib_font_params())
```

---

### 3. `palettes.py` – Paletas y Colormaps

#### Paletas categóricas
| Nombre | Colores | Uso |
|--------|---------|-----|
| `categorical` | 6 | Series comparativas generales |
| `categorical_extended` | 10 | Muchas categorías |
| `binary` | 2 | Comparación A vs B |
| `positive_negative` | 2 | Resultados buenos/malos |
| `traffic_light` | 3 | Semáforos de estado |
| `status_4` | 4 | Cuatro niveles de estado |

#### Colormaps para Matplotlib/Seaborn
| Nombre | Descripción | Uso ideal |
|--------|-------------|-----------|
| `sura_blues` | Blanco → Azul SURA | Heatmaps, densidades |
| `sura_aquas` | Blanco → Aqua SURA | Alternativa fría |
| `sura_ocean` | Azul Profundo → Aqua | Contraste máximo |
| `sura_diverging` | Rojo ↔ Neutro ↔ Azul | Correlaciones, delta |
| `sura_cool` | Azul profundo ↔ Aqua | Paleta fría divergente |

Todos los colormaps se **registran automáticamente** en Matplotlib al importar el módulo.

```python
from sura_brand.palettes import get_palette, get_cmap, make_n_colors
cmap = get_cmap("sura_diverging")   # Para heatmap de correlación
colors = make_n_colors(7)           # 7 colores interpolados
```

---

### 4. `styles.py` – Estilos Globales

Configura automáticamente Matplotlib (`rcParams`) y Seaborn con los estándares visuales SURA. Disponible en modo claro y oscuro.

```python
import sura_brand as sb

sb.apply_sura_style()         # Tema claro (fondos blancos/grises)
sb.apply_sura_style("dark")   # Tema oscuro (fondo #0D1B2E)

# Context manager temporal
with sb.sura_style("light"):
    fig, ax = plt.subplots()
    ax.plot(x, y)
```

**Parámetros configurados:** `figure.facecolor`, `axes.facecolor`, `axes.grid`, `axes.spines` (top/right ocultos), `axes.prop_cycle` (paleta SURA), `grid.linestyle`, `legend`, tipografía, `savefig.dpi=150`.

---

### 5. `charts.py` – Gráficas Listas con Branding

Funciones de alto nivel que producen figuras completas con watermark del logo SURA y footer:

| Función | Tipo de gráfica |
|---------|----------------|
| `bar_chart()` | Barras verticales u horizontales con valores |
| `line_chart()` | Líneas (serie única o múltiple) |
| `dist_chart()` | Histograma + KDE (seaborn.histplot) |
| `correlation_heatmap()` | Mapa de calor de correlaciones |
| `scatter_chart()` | Dispersión con hue opcional |
| `boxplot_chart()` | Boxplot por categorías |
| `pie_chart()` | Pastel o dona |
| `add_logo_watermark()` | Agrega logo SURA a cualquier figura |
| `add_sura_footer()` | Agrega footer con texto y logo |

```python
import sura_brand as sb

fig, ax = sb.dist_chart(df["prima_neta"], title="Distribución de Prima Neta")
fig, ax = sb.correlation_heatmap(df_numericas, title="Matriz de Correlación")
fig, ax = sb.bar_chart(categorias, valores, horizontal=True)
```

---

### 6. `layout.py` – Dashboards y Reportes

| Función | Descripción |
|---------|-------------|
| `create_dashboard(nrows, ncols)` | Grid de paneles con cabecera y footer SURA |
| `create_report_figure(title)` | Figura de reporte de un panel con barra de color |
| `create_kpi_figure(dict)` | Tarjetas de métricas/KPIs con colores SURA |
| `SIZES` | Constantes de tamaños: SLIDE_WIDE, REPORT_FULL, NOTEBOOK, etc. |

```python
from sura_brand.layout import create_dashboard, create_kpi_figure

fig, axes = create_dashboard(2, 3, title="EDA – Análisis Exploratorio SURA")

fig = create_kpi_figure({
    "Registros": 125_430,
    "Variables": 23,
    "Nulos (%)": "2.4%",
    "Período": "2020–2024",
})
```

---

## Uso en Notebooks EDA

```python
# ─── Inicio de cada notebook ───────────────────────
import sura_brand as sb

# Activar estilo global (una sola vez)
sb.apply_sura_style()   # o sb.apply_sura_style("dark") para modo oscuro

# Crear gráficas con branding automático
fig, ax = sb.dist_chart(df["edad"], title="Distribución de Edad del Asegurado")
plt.show()
# ───────────────────────────────────────────────────
```

---

## Decisiones de Diseño

- **Fuente Barlow**: seleccionada por ser la tipografía oficial del descriptor "GRUPO SURA" según el manual de marca, y por su disponibilidad pública (Google Fonts).
- **Spines top/right ocultos**: estándar moderno de visualización que reduce el ruido visual y mejora la legibilidad.
- **Watermark semi-transparente**: balance entre visibilidad de marca y claridad de los datos (alpha=0.5–0.6).
- **Colormaps registrados globalmente**: permite usar `"sura_blues"` directamente en `seaborn.heatmap(cmap=...)` sin importar el objeto.
- **Context manager `sura_style`**: facilita figuras aisladas sin afectar el estado global del notebook.
- **`make_n_colors(n)`**: garantiza siempre el número exacto de colores necesarios interpolando sobre `sura_ocean`.

---

## Modelos de IA Utilizados

| Modelo | Uso |
|--------|-----|
| Claude Sonnet 4.6 (Thinking) | Investigación de marca, arquitectura del paquete, implementación de todos los módulos, documentación |
