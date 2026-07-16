"""
sura_brand.layout
=================
Helpers para layout de figuras multi-panel con identidad SURA.
Facilita la creación de dashboards y reportes visuales consistentes.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch

from sura_brand.colors import AZUL_SURA, AQUA_SURA, NEGRO, GRIS_MEDIO, BLANCO
from sura_brand.charts import add_logo_watermark


# ─────────────────────────────────────────────
#  TAMAÑOS DE FIGURA ESTÁNDAR
# ─────────────────────────────────────────────

class FigureSizes:
    """Tamaños de figura estándar para distintos formatos de reporte."""
    SLIDE_WIDE: Tuple[int, int] = (16, 9)       # Presentación horizontal
    SLIDE_SQUARE: Tuple[int, int] = (12, 10)    # Presentación cuadrada
    REPORT_FULL: Tuple[int, int] = (14, 10)     # Reporte completo
    REPORT_HALF: Tuple[int, int] = (10, 6)      # Media página de reporte
    NOTEBOOK: Tuple[int, int] = (12, 7)         # Notebook por defecto
    THUMBNAIL: Tuple[int, int] = (6, 4)         # Miniatura


SIZES = FigureSizes()


# Margins in figure coordinates. Leave generous bands so ax titles
# (above) and tick/xlabels (below) never collide with fig-level chrome.
# Gaps sized for short/wide figures (fonts occupy more figure-fraction there).
_TOP = 0.78
_BOTTOM = 0.20
_TITLE_Y = 0.985
_SUBTITLE_Y = 0.920
_LINE_Y = 0.875


# ─────────────────────────────────────────────
#  LAYOUT HELPERS
# ─────────────────────────────────────────────

def create_dashboard(
    nrows: int = 2,
    ncols: int = 2,
    title: str = "",
    subtitle: str = "",
    figsize: Optional[Tuple[int, int]] = None,
    hspace: float = 0.45,
    wspace: float = 0.30,
    footer_text: str = "Análisis EDA | Grupo SURA",
) -> Tuple[Figure, List[Axes]]:
    """
    Crea un dashboard multi-panel con cabecera SURA.

    El footer/logo no se dibujan aquí: usar ``add_sura_footer`` después de
    poblar los ejes (evita solapamiento y footers duplicados).

    Parameters
    ----------
    nrows, ncols : int
        Número de filas y columnas del grid. Default: 2×2.
    title : str
        Título principal del dashboard.
    subtitle : str
        Subtítulo o descripción.
    figsize : tuple, optional
        Tamaño de la figura. Si None, se calcula automáticamente.
    hspace, wspace : float
        Espaciado vertical y horizontal entre paneles.
    footer_text : str
        Reservado por compatibilidad de API. No se dibuja; pasar el texto
        a ``add_sura_footer(fig, text=...)``.

    Returns
    -------
    Tuple[Figure, List[Axes]]
        La figura y una lista plana de todos los ejes.
    """
    del footer_text  # API compat — footer se aplica con add_sura_footer

    if figsize is None:
        # Extra vertical room so short/wide dashboards don't crowd header/footer
        figsize = (max(ncols * 5.5, 10.0), max(nrows * 4.2, 5.0) + 3.5)

    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("#FAFAFA")

    if title:
        # Figure-level header (never shares space with subplot axes)
        fig.text(
            0.5, _TITLE_Y, title,
            ha="center", va="top",
            fontsize=13, fontweight="bold",
            color=AZUL_SURA.hex,
            transform=fig.transFigure,
        )
        if subtitle:
            fig.text(
                0.5, _SUBTITLE_Y, subtitle,
                ha="center", va="top",
                fontsize=9, color=GRIS_MEDIO.hex, style="italic",
                transform=fig.transFigure,
            )
        line = fig.add_axes([0.08, _LINE_Y, 0.84, 0.004])
        line.set_facecolor(AQUA_SURA.hex)
        line.set_xticks([])
        line.set_yticks([])
        for spine in line.spines.values():
            spine.set_visible(False)

        gs = gridspec.GridSpec(
            nrows, ncols, figure=fig,
            hspace=hspace, wspace=wspace,
            top=_TOP, bottom=_BOTTOM, left=0.08, right=0.97,
        )
    else:
        gs = gridspec.GridSpec(
            nrows, ncols, figure=fig,
            hspace=hspace, wspace=wspace,
            top=0.94, bottom=_BOTTOM, left=0.08, right=0.97,
        )

    axes = [fig.add_subplot(gs[i, j]) for i in range(nrows) for j in range(ncols)]
    fig._sura_footer_ax = None  # type: ignore[attr-defined]
    return fig, axes


def create_report_figure(
    title: str,
    subtitle: str = "",
    figsize: Tuple[int, int] = FigureSizes.REPORT_FULL,
    footer_text: str = "Análisis EDA | Grupo SURA",
) -> Tuple[Figure, Axes]:
    """
    Crea una figura de reporte con un solo panel y cabecera SURA.

    El footer/logo no se dibujan aquí: usar ``add_sura_footer`` después.

    Parameters
    ----------
    title : str
        Título principal de la figura.
    subtitle : str
        Subtítulo opcional.
    figsize : tuple
        Tamaño de la figura. Default: REPORT_FULL (14×10).
    footer_text : str
        Reservado por compatibilidad de API. No se dibuja; pasar el texto
        a ``add_sura_footer(fig, text=...)``.

    Returns
    -------
    Tuple[Figure, Axes]
        La figura y el eje principal.
    """
    del footer_text  # API compat — footer se aplica con add_sura_footer

    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("#FAFAFA")

    top = 0.74 if subtitle else 0.80
    fig.subplots_adjust(top=top, bottom=_BOTTOM, left=0.10, right=0.95)

    # Top accent bar (thin strip, clear of title text)
    bar = fig.add_axes([0.0, 0.975, 1.0, 0.015])
    bar.set_facecolor(AZUL_SURA.hex)
    bar.set_xticks([])
    bar.set_yticks([])
    for spine in bar.spines.values():
        spine.set_visible(False)

    fig.text(
        0.05, 0.945, title,
        ha="left", va="top",
        fontsize=13, fontweight="bold",
        color=AZUL_SURA.hex,
        transform=fig.transFigure,
    )
    if subtitle:
        fig.text(
            0.05, 0.900, subtitle,
            ha="left", va="top",
            fontsize=9.5, color=GRIS_MEDIO.hex, style="italic",
            transform=fig.transFigure,
        )

    ax = fig.add_subplot(111)
    # Re-apply margins after add_subplot (can reset subplotpars)
    fig.subplots_adjust(top=top, bottom=_BOTTOM, left=0.10, right=0.95)
    fig._sura_footer_ax = None  # type: ignore[attr-defined]
    return fig, ax


def create_kpi_figure(
    kpis: Dict[str, Union[str, float, int]],
    title: str = "",
    colors: Optional[List[str]] = None,
    figsize: Optional[Tuple[int, int]] = None,
    footer_text: str = "Análisis EDA | Grupo SURA",
) -> Figure:
    """
    Crea una figura de KPIs / métricas destacadas con estilo SURA.
    """
    from sura_brand.palettes import CATEGORICAL_PRIMARY

    n = len(kpis)
    if figsize is None:
        figsize = (min(n * 3.5, 18), 3.8)

    colors = colors or (CATEGORICAL_PRIMARY * ((n // len(CATEGORICAL_PRIMARY)) + 1))[:n]
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]

    fig.patch.set_facecolor("#FAFAFA")

    if title:
        fig.suptitle(title, fontsize=14, fontweight="bold", color=AZUL_SURA.hex, y=0.98)

    for ax, (metric, value), color in zip(axes, kpis.items(), colors):
        ax.set_facecolor(color)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        val_str = f"{value:,}" if isinstance(value, (int, float)) else str(value)
        ax.text(
            0.5, 0.55, val_str,
            ha="center", va="center",
            fontsize=22, fontweight="bold",
            color=BLANCO.hex,
            transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.22, metric,
            ha="center", va="center",
            fontsize=10,
            color=BLANCO.hex,
            transform=ax.transAxes,
        )
        ax.add_patch(FancyBboxPatch(
            (0.02, 0.02), 0.96, 0.96,
            boxstyle="round,pad=0.02",
            transform=ax.transAxes,
            facecolor=color, edgecolor="white", linewidth=2,
            zorder=0,
        ))

    fig.subplots_adjust(wspace=0.08, left=0.02, right=0.98, bottom=0.16, top=0.88)
    fig.text(
        0.02, 0.04, footer_text,
        ha="left", va="center",
        fontsize=7.5, color=GRIS_MEDIO.hex, style="italic",
        transform=fig.transFigure,
    )
    add_logo_watermark(fig, position="bottom-right", alpha=0.4, scale=0.08)
    return fig
