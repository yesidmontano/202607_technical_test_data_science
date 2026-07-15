"""
sura_brand.charts
=================
Funciones de alto nivel para crear gráficas con identidad visual SURA.
Incluyen watermark con logo, configuración automática de estilos y
helpers para los tipos de gráficas más comunes en EDA.

Cada función retorna (fig, ax) listo para personalización adicional.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.image as mpimg
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np
import seaborn as sns

from sura_brand.colors import AZUL_SURA, AQUA_SURA, GRIS_MEDIO, NEGRO, BLANCO
from sura_brand.palettes import get_cmap, get_palette, make_n_colors


# ─────────────────────────────────────────────
#  RUTA DEL LOGO
# ─────────────────────────────────────────────

_PACKAGE_DIR = Path(__file__).parent
_LOGO_PATH = _PACKAGE_DIR / "assets" / "logo.png"


# ─────────────────────────────────────────────
#  WATERMARK Y DECORADORES
# ─────────────────────────────────────────────

def add_logo_watermark(
    fig: Figure,
    position: str = "bottom-right",
    alpha: float = 0.6,
    scale: float = 0.10,
    logo_path: Optional[Union[str, Path]] = None,
) -> Figure:
    """
    Agrega el logo de SURA como watermark a una figura de Matplotlib.

    Parameters
    ----------
    fig : Figure
        Figura de Matplotlib a la que se añadirá el logo.
    position : str
        Posición del logo: 'bottom-right', 'bottom-left', 'top-right', 'top-left'.
    alpha : float
        Transparencia del logo (0.0 = invisible, 1.0 = opaco). Default: 0.6.
    scale : float
        Escala del logo como fracción del ancho de la figura. Default: 0.10.
    logo_path : str or Path, optional
        Ruta personalizada al logo. Si None, usa el logo del paquete.

    Returns
    -------
    Figure
        La misma figura con el logo añadido.

    Examples
    --------
    >>> from sura_brand.charts import add_logo_watermark
    >>> fig, ax = plt.subplots()
    >>> ax.plot([1, 2, 3])
    >>> fig = add_logo_watermark(fig)
    """
    path = Path(logo_path) if logo_path else _LOGO_PATH

    if not path.exists():
        warnings.warn(f"Logo no encontrado en: {path}. Watermark omitido.")
        return fig

    # Cargar logo
    logo = mpimg.imread(str(path))
    fig_w, fig_h = fig.get_size_inches()

    # Calcular tamaño del logo
    logo_h, logo_w = logo.shape[:2]
    aspect = logo_w / logo_h
    logo_display_w = scale * fig_w / fig_w   # en fracción de figura
    logo_display_h = logo_display_w / aspect * (fig_w / fig_h)

    # Calcular posición
    padding = 0.01
    positions = {
        "bottom-right": [1.0 - logo_display_w - padding, padding, logo_display_w, logo_display_h],
        "bottom-left": [padding, padding, logo_display_w, logo_display_h],
        "top-right": [1.0 - logo_display_w - padding, 1.0 - logo_display_h - padding, logo_display_w, logo_display_h],
        "top-left": [padding, 1.0 - logo_display_h - padding, logo_display_w, logo_display_h],
    }

    if position not in positions:
        position = "bottom-right"

    ax_logo = fig.add_axes(positions[position])
    ax_logo.imshow(logo, alpha=alpha)
    ax_logo.axis("off")

    return fig


def add_sura_footer(
    fig: Figure,
    text: str = "Análisis EDA | Grupo SURA",
    include_logo: bool = True,
) -> Figure:
    """
    Agrega un footer con texto de fuente/contexto y logo SURA.

    Parameters
    ----------
    fig : Figure
        Figura de Matplotlib.
    text : str
        Texto del footer (ej. fuente de datos, fecha, área).
    include_logo : bool
        Si True, incluye el logo en la esquina inferior derecha.

    Returns
    -------
    Figure
        La figura con el footer añadido.
    """
    fig.text(
        0.01, 0.01, text,
        ha="left", va="bottom",
        fontsize=8,
        color=GRIS_MEDIO.hex,
        style="italic",
        transform=fig.transFigure,
    )
    if include_logo:
        add_logo_watermark(fig, position="bottom-right", alpha=0.5, scale=0.08)
    return fig


def style_axes(
    ax: Axes,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title_size: int = 14,
    remove_top_right: bool = True,
) -> Axes:
    """
    Aplica el estilo SURA a un eje existente.

    Parameters
    ----------
    ax : Axes
        Eje de Matplotlib.
    title : str, optional
        Título del gráfico.
    xlabel, ylabel : str, optional
        Etiquetas de ejes.
    title_size : int
        Tamaño de fuente del título. Default: 14.
    remove_top_right : bool
        Si True, elimina los spines superior y derecho. Default: True.

    Returns
    -------
    Axes
        El mismo eje configurado.
    """
    if remove_top_right:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    if title:
        ax.set_title(title, fontsize=title_size, fontweight="bold", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11, color=GRIS_MEDIO.hex)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11, color=GRIS_MEDIO.hex)

    ax.tick_params(colors=GRIS_MEDIO.hex, labelsize=10)
    ax.yaxis.grid(True, alpha=0.4, linestyle="--")
    ax.set_axisbelow(True)

    return ax


# ─────────────────────────────────────────────
#  GRÁFICAS COMUNES PARA EDA
# ─────────────────────────────────────────────

def bar_chart(
    x: Sequence,
    y: Sequence,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    color: str = AZUL_SURA.hex,
    horizontal: bool = False,
    show_values: bool = True,
    figsize: Tuple[int, int] = (10, 6),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Gráfica de barras con estilo SURA.

    Parameters
    ----------
    x : array-like
        Categorías.
    y : array-like
        Valores numéricos.
    title, xlabel, ylabel : str
        Texto de título y etiquetas de ejes.
    color : str
        Color de las barras (HEX). Default: Azul SURA.
    horizontal : bool
        Si True, genera gráfica horizontal (barh). Default: False.
    show_values : bool
        Si True, muestra el valor sobre cada barra. Default: True.
    figsize : tuple
        Tamaño de la figura. Default: (10, 6).
    **kwargs
        Parámetros adicionales para ax.bar / ax.barh.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    fig, ax = plt.subplots(figsize=figsize)

    if horizontal:
        bars = ax.barh(x, y, color=color, alpha=0.88, **kwargs)
        if show_values:
            for bar in bars:
                val = bar.get_width()
                ax.text(
                    val + max(y) * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:,.1f}", va="center", ha="left",
                    fontsize=9, color=NEGRO.hex,
                )
    else:
        bars = ax.bar(x, y, color=color, alpha=0.88, **kwargs)
        if show_values:
            for bar in bars:
                val = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2, val + max(y) * 0.01,
                    f"{val:,.1f}", ha="center", va="bottom",
                    fontsize=9, color=NEGRO.hex,
                )

    style_axes(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    add_sura_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig, ax


def line_chart(
    x: Sequence,
    y: Union[Sequence, Dict[str, Sequence]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    palette: str = "categorical",
    markers: bool = True,
    figsize: Tuple[int, int] = (12, 6),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Gráfica de líneas con estilo SURA. Soporta múltiples series.

    Parameters
    ----------
    x : array-like
        Valores del eje X.
    y : array-like or Dict[str, array-like]
        Valores del eje Y. Si es dict, las claves son los nombres de las series.
    title, xlabel, ylabel : str
        Texto de título y etiquetas.
    palette : str
        Nombre de paleta categórica para múltiples series.
    markers : bool
        Si True, agrega marcadores en los puntos. Default: True.
    figsize : tuple
        Tamaño de la figura.
    **kwargs
        Parámetros adicionales para ax.plot.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    fig, ax = plt.subplots(figsize=figsize)
    colors = get_palette(palette)
    marker = "o" if markers else None

    if isinstance(y, dict):
        for i, (label, values) in enumerate(y.items()):
            color = colors[i % len(colors)]
            ax.plot(x, values, label=label, color=color, marker=marker,
                    markersize=5, linewidth=2, **kwargs)
        ax.legend(frameon=True, loc="best")
    else:
        ax.plot(x, y, color=colors[0], marker=marker,
                markersize=5, linewidth=2.5, **kwargs)

    style_axes(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    add_sura_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig, ax


def dist_chart(
    data: Sequence,
    title: str = "",
    xlabel: str = "",
    color: str = AZUL_SURA.hex,
    kde: bool = True,
    bins: int = 30,
    figsize: Tuple[int, int] = (10, 6),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Histograma con curva KDE y estilo SURA.

    Parameters
    ----------
    data : array-like
        Datos a graficar.
    title, xlabel : str
        Texto de título y etiqueta del eje X.
    color : str
        Color de la distribución. Default: Azul SURA.
    kde : bool
        Si True, superpone la curva de densidad. Default: True.
    bins : int
        Número de bins del histograma. Default: 30.
    figsize : tuple
        Tamaño de la figura.
    **kwargs
        Parámetros adicionales para seaborn.histplot.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    fig, ax = plt.subplots(figsize=figsize)
    sns.histplot(
        data=data, color=color, kde=kde,
        bins=bins, alpha=0.75, ax=ax,
        line_kws={"linewidth": 2.5, "color": AQUA_SURA.hex},
        **kwargs,
    )
    style_axes(ax, title=title, xlabel=xlabel, ylabel="Frecuencia")
    add_sura_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig, ax


def correlation_heatmap(
    data,
    title: str = "Mapa de Correlación",
    cmap: str = "sura_diverging",
    annot: bool = True,
    figsize: Tuple[int, int] = (12, 10),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Mapa de calor de correlaciones con estilo SURA.

    Parameters
    ----------
    data : pd.DataFrame or array-like
        Matriz de correlación o DataFrame (se calculará la correlación automáticamente).
    title : str
        Título del gráfico.
    cmap : str
        Colormap a utilizar. Default: 'sura_diverging'.
    annot : bool
        Si True, muestra los valores. Default: True.
    figsize : tuple
        Tamaño de la figura.
    **kwargs
        Parámetros adicionales para seaborn.heatmap.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    import pandas as pd
    fig, ax = plt.subplots(figsize=figsize)

    # Si es un DataFrame, calcular correlación
    if hasattr(data, "corr"):
        corr_matrix = data.corr()
    else:
        corr_matrix = data

    colormap = get_cmap(cmap)
    sns.heatmap(
        corr_matrix,
        cmap=colormap,
        center=0,
        annot=annot,
        fmt=".2f" if annot else None,
        linewidths=0.5,
        linecolor="#E0E0E0",
        square=True,
        ax=ax,
        cbar_kws={"shrink": 0.75, "aspect": 20},
        **kwargs,
    )
    style_axes(ax, title=title, remove_top_right=False)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    add_sura_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig, ax


def scatter_chart(
    x: Sequence,
    y: Sequence,
    hue: Optional[Sequence] = None,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    color: str = AZUL_SURA.hex,
    alpha: float = 0.7,
    size: float = 40,
    figsize: Tuple[int, int] = (10, 7),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Gráfica de dispersión con estilo SURA.

    Parameters
    ----------
    x, y : array-like
        Coordenadas de los puntos.
    hue : array-like, optional
        Variable categórica para colorear los puntos.
    title, xlabel, ylabel : str
        Texto de título y etiquetas.
    color : str
        Color base (cuando no hay hue). Default: Azul SURA.
    alpha : float
        Transparencia de los puntos. Default: 0.7.
    size : float
        Tamaño de los puntos. Default: 40.
    figsize : tuple
        Tamaño de la figura.
    **kwargs
        Parámetros adicionales para seaborn.scatterplot.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    fig, ax = plt.subplots(figsize=figsize)
    palette = get_palette("categorical") if hue is not None else None
    sns.scatterplot(
        x=x, y=y, hue=hue,
        color=color if hue is None else None,
        palette=palette,
        alpha=alpha, s=size,
        ax=ax, **kwargs,
    )
    style_axes(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    add_sura_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig, ax


def boxplot_chart(
    data,
    x: Optional[str] = None,
    y: Optional[str] = None,
    hue: Optional[str] = None,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    palette: str = "categorical",
    figsize: Tuple[int, int] = (12, 7),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Boxplot / violinplot con estilo SURA.

    Parameters
    ----------
    data : pd.DataFrame
        Datos en formato tidy/long.
    x, y, hue : str, optional
        Columnas del DataFrame para cada dimensión.
    title, xlabel, ylabel : str
        Texto de título y etiquetas.
    palette : str
        Nombre de paleta categórica. Default: 'categorical'.
    figsize : tuple
        Tamaño de la figura.
    **kwargs
        Parámetros adicionales para seaborn.boxplot.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    fig, ax = plt.subplots(figsize=figsize)
    colors = get_palette(palette)
    sns.boxplot(
        data=data, x=x, y=y, hue=hue,
        palette=colors,
        linewidth=1.2,
        flierprops={"marker": "o", "markersize": 4, "alpha": 0.5},
        ax=ax, **kwargs,
    )
    style_axes(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    if hue:
        ax.legend(title=hue, frameon=True)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
    add_sura_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig, ax


def pie_chart(
    values: Sequence,
    labels: Sequence[str],
    title: str = "",
    palette: str = "categorical",
    donut: bool = True,
    figsize: Tuple[int, int] = (8, 8),
    **kwargs,
) -> Tuple[Figure, Axes]:
    """
    Gráfica de pastel / dona con estilo SURA.

    Parameters
    ----------
    values : array-like
        Valores numéricos (no necesitan sumar 100).
    labels : array-like of str
        Etiquetas de cada categoría.
    title : str
        Título del gráfico.
    palette : str
        Paleta categórica.
    donut : bool
        Si True, genera gráfica de dona. Default: True.
    figsize : tuple
        Tamaño de la figura.
    **kwargs
        Parámetros adicionales para ax.pie.

    Returns
    -------
    Tuple[Figure, Axes]
    """
    n = len(values)
    colors = make_n_colors(n, palette)
    fig, ax = plt.subplots(figsize=figsize)

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.75 if donut else 0.60,
        wedgeprops={"linewidth": 2, "edgecolor": "white"},
        **kwargs,
    )

    if donut:
        centre_circle = plt.Circle((0, 0), 0.55, fc="white")
        ax.add_patch(centre_circle)

    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight("bold")

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

    add_sura_footer(fig)
    return fig, ax
