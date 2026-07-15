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

from sura_brand.colors import AZUL_SURA, AQUA_SURA, NEGRO, GRIS_MEDIO, BLANCO
from sura_brand.charts import add_sura_footer, add_logo_watermark


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


# ─────────────────────────────────────────────
#  LAYOUT HELPERS
# ─────────────────────────────────────────────

def create_dashboard(
    nrows: int = 2,
    ncols: int = 2,
    title: str = "",
    subtitle: str = "",
    figsize: Optional[Tuple[int, int]] = None,
    hspace: float = 0.4,
    wspace: float = 0.3,
    footer_text: str = "Análisis EDA | Grupo SURA",
) -> Tuple[Figure, List[Axes]]:
    """
    Crea un dashboard multi-panel con cabecera y footer SURA.

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
        Texto del footer.

    Returns
    -------
    Tuple[Figure, List[Axes]]
        La figura y una lista plana de todos los ejes.

    Examples
    --------
    >>> from sura_brand.layout import create_dashboard
    >>> fig, axes = create_dashboard(2, 3, title="EDA - Variables Numéricas")
    >>> for i, ax in enumerate(axes):
    ...     ax.set_title(f"Panel {i+1}")
    """
    if figsize is None:
        figsize = (ncols * 6, nrows * 5 + (1.5 if title else 0))

    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("#FAFAFA")

    # Reservar espacio para cabecera si hay título
    if title:
        top_space = 0.92 if subtitle else 0.94
        gs = gridspec.GridSpec(
            nrows, ncols,
            figure=fig,
            hspace=hspace, wspace=wspace,
            top=top_space, bottom=0.08, left=0.06, right=0.97,
        )
        # Título principal
        fig.text(
            0.5, 0.97, title,
            ha="center", va="top",
            fontsize=16, fontweight="bold",
            color=AZUL_SURA.hex,
            transform=fig.transFigure,
        )
        # Subtítulo
        if subtitle:
            fig.text(
                0.5, 0.945, subtitle,
                ha="center", va="top",
                fontsize=11, color=GRIS_MEDIO.hex, style="italic",
                transform=fig.transFigure,
            )
        # Línea decorativa bajo el título
        ax_line = fig.add_axes([0.05, 0.935, 0.90, 0.002])
        ax_line.set_facecolor(AQUA_SURA.hex)
        ax_line.axis("off")
    else:
        gs = gridspec.GridSpec(
            nrows, ncols,
            figure=fig,
            hspace=hspace, wspace=wspace,
            top=0.94, bottom=0.08, left=0.06, right=0.97,
        )

    axes = [fig.add_subplot(gs[i, j]) for i in range(nrows) for j in range(ncols)]

    # Footer
    fig.text(
        0.01, 0.01, footer_text,
        ha="left", va="bottom",
        fontsize=8, color=GRIS_MEDIO.hex, style="italic",
        transform=fig.transFigure,
    )
    add_logo_watermark(fig, position="bottom-right", alpha=0.45, scale=0.08)

    return fig, axes


def create_report_figure(
    title: str,
    subtitle: str = "",
    figsize: Tuple[int, int] = FigureSizes.REPORT_FULL,
    footer_text: str = "Análisis EDA | Grupo SURA",
) -> Tuple[Figure, Axes]:
    """
    Crea una figura de reporte con un solo panel y cabecera SURA.

    Parameters
    ----------
    title : str
        Título principal de la figura.
    subtitle : str
        Subtítulo opcional.
    figsize : tuple
        Tamaño de la figura. Default: REPORT_FULL (14×10).
    footer_text : str
        Texto del footer.

    Returns
    -------
    Tuple[Figure, Axes]
        La figura y el eje principal.
    """
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#FAFAFA")
    fig.subplots_adjust(top=0.88, bottom=0.10)

    # Barra de color en la parte superior
    ax_bar = fig.add_axes([0.0, 0.94, 1.0, 0.025])
    ax_bar.set_facecolor(AZUL_SURA.hex)
    ax_bar.axis("off")

    # Título
    fig.text(
        0.05, 0.935, title,
        ha="left", va="top",
        fontsize=15, fontweight="bold",
        color=AZUL_SURA.hex,
        transform=fig.transFigure,
    )
    if subtitle:
        fig.text(
            0.05, 0.905, subtitle,
            ha="left", va="top",
            fontsize=10, color=GRIS_MEDIO.hex, style="italic",
            transform=fig.transFigure,
        )

    # Footer
    fig.text(
        0.01, 0.01, footer_text,
        ha="left", va="bottom",
        fontsize=8, color=GRIS_MEDIO.hex, style="italic",
        transform=fig.transFigure,
    )
    add_logo_watermark(fig, position="bottom-right", alpha=0.5, scale=0.09)

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

    Parameters
    ----------
    kpis : Dict[str, value]
        Diccionario con nombre de métrica y su valor.
        Ej: {'Total Registros': 12_450, 'Variables': 23, 'Nulos (%)': '3.2%'}
    title : str
        Título de la sección de KPIs.
    colors : List[str], optional
        Lista de colores para cada KPI. Si None, usa la paleta SURA.
    figsize : tuple, optional
        Tamaño de la figura.
    footer_text : str
        Texto del footer.

    Returns
    -------
    Figure
    """
    from sura_brand.palettes import CATEGORICAL_PRIMARY
    n = len(kpis)
    if figsize is None:
        figsize = (min(n * 3.5, 18), 3.5)

    colors = colors or (CATEGORICAL_PRIMARY * ((n // len(CATEGORICAL_PRIMARY)) + 1))[:n]
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]

    fig.patch.set_facecolor("#FAFAFA")

    if title:
        fig.suptitle(title, fontsize=14, fontweight="bold", color=AZUL_SURA.hex, y=1.02)

    for ax, (metric, value), color in zip(axes, kpis.items(), colors):
        ax.set_facecolor(color)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Valor grande
        val_str = f"{value:,}" if isinstance(value, (int, float)) else str(value)
        ax.text(
            0.5, 0.55, val_str,
            ha="center", va="center",
            fontsize=22, fontweight="bold",
            color=BLANCO.hex,
            transform=ax.transAxes,
        )
        # Nombre de la métrica
        ax.text(
            0.5, 0.22, metric,
            ha="center", va="center",
            fontsize=10,
            color="rgba(255,255,255,0.85)" if color != BLANCO.hex else NEGRO.hex,
            transform=ax.transAxes,
        )
        # Bordes redondeados simulados con patch
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.02, 0.02), 0.96, 0.96,
            boxstyle="round,pad=0.02",
            transform=ax.transAxes,
            facecolor=color, edgecolor="white", linewidth=2,
            zorder=0,
        ))

    import matplotlib.patches as mpatches  # noqa – import inside to avoid cycle

    fig.subplots_adjust(wspace=0.08, left=0.02, right=0.98, bottom=0.05)
    fig.text(
        0.01, -0.05, footer_text,
        ha="left", va="bottom",
        fontsize=7.5, color=GRIS_MEDIO.hex, style="italic",
        transform=fig.transFigure,
    )
    add_logo_watermark(fig, position="bottom-right", alpha=0.4, scale=0.08)
    return fig
