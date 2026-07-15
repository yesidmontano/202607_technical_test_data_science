"""
sura_brand
==========
Manual de marca para visualizaciones de datos – Grupo SURA.

Paquete de Python que implementa el sistema de diseño visual de SURA
(colores, tipografía, paletas, estilos y componentes gráficos) para
uso consistente en análisis exploratorios de datos (EDA) y reportes.

Módulos
-------
colors      : Colores primarios, secundarios, neutros y semánticos.
typography  : Fuentes, escalas tipográficas y parámetros para Matplotlib.
palettes    : Paletas categóricas, secuenciales y divergentes (colormaps).
styles      : Aplicación global de estilos a Matplotlib y Seaborn.
charts      : Funciones de alto nivel para gráficas con branding SURA.
layout      : Helpers para dashboards y figuras multi-panel.

Uso rápido
----------
    >>> import sura_brand as sb

    # Aplicar estilo globalmente
    >>> sb.apply_sura_style()                     # Tema claro (default)
    >>> sb.apply_sura_style("dark")               # Tema oscuro

    # Acceder a colores
    >>> sb.colors.AZUL_SURA.hex                   # '#0033A0'
    >>> sb.colors.AQUA_SURA.rgb                   # (0, 174, 199)

    # Obtener paleta
    >>> sb.palettes.get_palette("categorical")    # Lista de HEX

    # Crear gráficas rápidamente
    >>> fig, ax = sb.charts.bar_chart(x, y, title="Mi Gráfica")
    >>> fig, ax = sb.charts.dist_chart(data, title="Distribución")

    # Dashboard
    >>> fig, axes = sb.layout.create_dashboard(2, 2, title="EDA Report")

Referencia de colores
---------------------
    Azul SURA    : #0033A0  (Pantone 286 C)   — Primario
    Aqua SURA    : #00AEC7  (Pantone 3125 C)  — Primario
    Azul Profundo: #001E60  (Pantone 2757 C)  — Secundario
    Aqua Alterno : #05C3DE  (Pantone 311 C)   — Secundario
    Amarillo SURA: #E3E829  (Pantone 809 C)   — Secundario
    Gris Claro   : #C7C9C7  (Pantone 420 C)   — Neutro

Versión del paquete
-------------------
    0.1.0 — Versión inicial del sistema de marca SURA para EDA.
"""

__version__ = "0.1.0"
__author__ = "Equipo Data Science | Grupo SURA"

# ─────────────────────────────────────────────
#  Importaciones de módulos públicos
# ─────────────────────────────────────────────

from sura_brand import colors, typography, palettes, styles, charts, layout

# Shortcuts de primer nivel más usados
from sura_brand.styles import apply_sura_style, reset_style, sura_style
from sura_brand.colors import (
    AZUL_SURA, AQUA_SURA, AZUL_PROFUNDO, AQUA_ALTERNO,
    AMARILLO_SURA, GRIS_CLARO, GRIS_MEDIO, BLANCO, NEGRO,
    get_color, list_colors,
)
from sura_brand.palettes import get_palette, get_cmap, make_n_colors
from sura_brand.charts import (
    add_logo_watermark, add_sura_footer,
    bar_chart, line_chart, dist_chart,
    correlation_heatmap, scatter_chart,
    boxplot_chart, pie_chart,
)
from sura_brand.layout import (
    create_dashboard, create_report_figure, create_kpi_figure,
    SIZES,
)

__all__ = [
    # Módulos
    "colors", "typography", "palettes", "styles", "charts", "layout",
    # Estilos
    "apply_sura_style", "reset_style", "sura_style",
    # Colores
    "AZUL_SURA", "AQUA_SURA", "AZUL_PROFUNDO", "AQUA_ALTERNO",
    "AMARILLO_SURA", "GRIS_CLARO", "GRIS_MEDIO", "BLANCO", "NEGRO",
    "get_color", "list_colors",
    # Paletas
    "get_palette", "get_cmap", "make_n_colors",
    # Gráficas
    "add_logo_watermark", "add_sura_footer",
    "bar_chart", "line_chart", "dist_chart",
    "correlation_heatmap", "scatter_chart",
    "boxplot_chart", "pie_chart",
    # Layout
    "create_dashboard", "create_report_figure", "create_kpi_figure",
    "SIZES",
]
