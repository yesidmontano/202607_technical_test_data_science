# sura_brand

> Manual de marca para visualizaciones de datos · Grupo SURA

Paquete interno de Python que implementa el sistema de diseño visual de SURA
(colores oficiales, tipografía, paletas y estilos gráficos) para generar
visualizaciones consistentes con la identidad corporativa en proyectos de
análisis de datos y EDA.

---

## Instalación

```bash
# Desde el directorio raíz del proyecto
pip install -e packages/sura_brand
```

---

## Uso rápido

```python
import sura_brand as sb

# 1. Aplicar estilo globalmente (llamar una vez al inicio del notebook)
sb.apply_sura_style()          # Tema claro (por defecto)
sb.apply_sura_style("dark")    # Tema oscuro

# 2. Como context manager (estilo temporal)
with sb.sura_style("light"):
    fig, ax = plt.subplots()
    ax.plot(x, y)
```

---

## Módulos

| Módulo        | Descripción |
|---------------|-------------|
| `colors`      | Colores primarios, secundarios, neutros y semánticos SURA |
| `typography`  | Fuentes Barlow/Inter, escala de tamaños para Matplotlib |
| `palettes`    | Paletas categóricas, colormaps secuenciales y divergentes |
| `styles`      | Configuración global de Matplotlib y Seaborn |
| `charts`      | Gráficas listas (bar, line, dist, scatter, heatmap, boxplot, pie) |
| `layout`      | Dashboards multi-panel, figuras de reporte, tarjetas KPI |

---

## Colores de marca

| Color          | HEX       | Pantone      | Rol       |
|----------------|-----------|--------------|-----------|
| Azul SURA      | `#0033A0` | Pantone 286 C | Primario |
| Aqua SURA      | `#00AEC7` | Pantone 3125 C | Primario |
| Azul Profundo  | `#001E60` | Pantone 2757 C | Secundario |
| Aqua Alterno   | `#05C3DE` | Pantone 311 C | Secundario |
| Amarillo SURA  | `#E3E829` | Pantone 809 C | Secundario |
| Gris Claro     | `#C7C9C7` | Pantone 420 C | Neutro |

```python
from sura_brand.colors import AZUL_SURA, AQUA_SURA, get_color
print(AZUL_SURA.hex)          # '#0033A0'
print(AZUL_SURA.rgb)          # (0, 51, 160)
print(AZUL_SURA.rgb_normalized)  # (0.0, 0.2, 0.627...)
```

---

## Paletas

```python
from sura_brand.palettes import get_palette, get_cmap, make_n_colors

# Paletas categóricas
palette = get_palette("categorical")           # 6 colores
palette = get_palette("categorical_extended")  # 10 colores
palette = get_palette("binary")                # 2 colores
palette = get_palette("traffic_light")         # 3 colores (verde/naranja/rojo)

# Colormaps para heatmaps y densidades
cmap = get_cmap("sura_blues")       # Blanco → Azul SURA
cmap = get_cmap("sura_ocean")       # Azul Profundo → Aqua
cmap = get_cmap("sura_diverging")   # Rojo ↔ Neutro ↔ Azul

# N colores exactos
colors = make_n_colors(7)
```

---

## Gráficas

```python
import sura_brand as sb

# Barra
fig, ax = sb.bar_chart(categorias, valores, title="Distribución por Segmento")

# Línea (múltiples series)
fig, ax = sb.line_chart(meses, {"2023": v2023, "2024": v2024}, title="Tendencia")

# Distribución con KDE
fig, ax = sb.dist_chart(df["edad"], title="Distribución de Edad")

# Correlación
fig, ax = sb.correlation_heatmap(df, title="Correlación de Variables")

# Scatter
fig, ax = sb.scatter_chart(df["x"], df["y"], hue=df["segmento"])

# Boxplot
fig, ax = sb.boxplot_chart(df, x="categoria", y="valor")

# Dona
fig, ax = sb.pie_chart(valores, etiquetas, title="Participación de Mercado")
```

---

## Dashboards

```python
from sura_brand.layout import create_dashboard, create_kpi_figure

# Dashboard 2×2
fig, axes = create_dashboard(2, 2, title="EDA – Variables Numéricas")
axes[0].plot(x, y)
axes[1].hist(data)

# Figura de KPIs
fig = create_kpi_figure({
    "Registros": 125_430,
    "Variables": 23,
    "Nulos (%)": "2.4%",
    "Período": "2020–2024",
}, title="Resumen del Dataset")
```

---

## Logo SURA

```python
from sura_brand.charts import add_logo_watermark
fig = add_logo_watermark(fig, position="bottom-right", alpha=0.6)
```

---

## Versión

`0.1.0` — Versión inicial · Julio 2026
