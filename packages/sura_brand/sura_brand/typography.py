"""
sura_brand.typography
=====================
Definiciones tipográficas para el sistema de visualización SURA.

La tipografía exclusiva de SURA no está disponible públicamente, por lo que
se utilizan fuentes de sistema/Google Fonts que armonizan con la identidad:

- **Barlow** (primaria): usada en el descriptor "GRUPO" del logo oficial.
  Geométrica, moderna, excelente legibilidad en texto y gráficos.
- **Inter** (secundaria): alternativa de alta legibilidad para dashboards.
- **DIN Alternate** (mono/técnica): para valores numéricos y tablas.
- **Monospace fallback**: para código y datos.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FontSpec:
    """Especificación de una fuente tipográfica."""
    family: str
    fallbacks: List[str] = field(default_factory=list)
    role: str = "body"
    weights: List[int] = field(default_factory=lambda: [400, 500, 700])

    @property
    def full_family(self) -> str:
        """Retorna la familia con fallbacks para CSS / Matplotlib."""
        families = [self.family] + self.fallbacks
        return ", ".join(families)

    def __str__(self) -> str:
        return self.family


# ─────────────────────────────────────────────
#  ESPECIFICACIONES DE FUENTES
# ─────────────────────────────────────────────

FONT_PRIMARY = FontSpec(
    family="Barlow",
    fallbacks=["DIN OT", "Helvetica Neue", "Arial", "sans-serif"],
    role="primary",
    weights=[300, 400, 500, 600, 700],
)
"""Fuente primaria: Barlow (usada oficialmente en el descriptor GRUPO SURA)."""

FONT_SECONDARY = FontSpec(
    family="Inter",
    fallbacks=["Segoe UI", "Roboto", "Arial", "sans-serif"],
    role="secondary",
    weights=[400, 500, 600],
)
"""Fuente secundaria: Inter. Alta legibilidad en pantalla para dashboards."""

FONT_NUMERIC = FontSpec(
    family="DIN Alternate",
    fallbacks=["Barlow", "Roboto Condensed", "Arial Narrow", "sans-serif"],
    role="numeric",
    weights=[400, 700],
)
"""Fuente numérica: DIN Alternate. Para KPIs, métricas y valores destacados."""

FONT_MONO = FontSpec(
    family="JetBrains Mono",
    fallbacks=["Consolas", "Monaco", "Courier New", "monospace"],
    role="mono",
    weights=[400],
)
"""Fuente monoespaciada: para código, tablas de datos y etiquetas técnicas."""


# ─────────────────────────────────────────────
#  ESCALA TIPOGRÁFICA
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class TypeScale:
    """Escala de tamaños tipográficos para visualizaciones."""
    # Títulos de figuras
    figure_title: int = 16
    # Subtítulos / contexto
    figure_subtitle: int = 13
    # Título de ejes
    axis_title: int = 12
    # Etiquetas de datos (data labels)
    data_label: int = 10
    # Ticks y leyendas
    tick_label: int = 10
    legend_title: int = 11
    legend_label: int = 10
    # Anotaciones
    annotation: int = 9
    # Texto de tablas
    table_header: int = 11
    table_body: int = 10
    # Totales / KPIs prominentes
    kpi: int = 18


TYPE_SCALE = TypeScale()
"""Escala tipográfica estándar para todas las visualizaciones SURA."""


# ─────────────────────────────────────────────
#  CONFIGURACIÓN PARA MATPLOTLIB
# ─────────────────────────────────────────────

def get_matplotlib_font_params(font: FontSpec = FONT_PRIMARY) -> Dict:
    """
    Retorna parámetros de fuente compatibles con rcParams de Matplotlib.

    Parameters
    ----------
    font : FontSpec, optional
        Especificación de fuente. Por defecto FONT_PRIMARY (Barlow).

    Returns
    -------
    Dict
        Diccionario listo para usar en `matplotlib.rcParams.update()`.

    Examples
    --------
    >>> import matplotlib as mpl
    >>> from sura_brand.typography import get_matplotlib_font_params
    >>> mpl.rcParams.update(get_matplotlib_font_params())
    """
    scale = TYPE_SCALE
    families = [font.family] + font.fallbacks

    return {
        "font.family": "sans-serif",
        "font.sans-serif": families,
        "axes.titlesize": scale.figure_title,
        "axes.labelsize": scale.axis_title,
        "xtick.labelsize": scale.tick_label,
        "ytick.labelsize": scale.tick_label,
        "legend.fontsize": scale.legend_label,
        "legend.title_fontsize": scale.legend_title,
        "figure.titlesize": scale.figure_title + 2,
    }
