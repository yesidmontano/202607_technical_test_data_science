"""
sura_brand.palettes
===================
Paletas de color para visualizaciones de datos basadas en la identidad
visual de SURA. Incluye paletas categóricas, secuenciales y divergentes
compatibles con Matplotlib y Seaborn.

Principios de diseño:
- El azul (#0033A0) y el aqua (#00AEC7) son los anclajes cromáticos.
- Las paletas aseguran contraste accesible (WCAG AA).
- Se incluyen variantes para fondo claro (default) y fondo oscuro.
"""

from __future__ import annotations

from typing import List, Optional, Union
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

from sura_brand.colors import (
    AZUL_SURA, AQUA_SURA, AZUL_PROFUNDO, AQUA_ALTERNO,
    AMARILLO_SURA, GRIS_CLARO, GRIS_MEDIO, BLANCO, NEGRO,
    POSITIVO, NEGATIVO, ADVERTENCIA, INFORMACION,
)


# ─────────────────────────────────────────────
#  PALETAS CATEGÓRICAS
# ─────────────────────────────────────────────

CATEGORICAL_PRIMARY: List[str] = [
    AZUL_SURA.hex,       # #0033A0 – Azul SURA
    AQUA_SURA.hex,       # #00AEC7 – Aqua SURA
    AZUL_PROFUNDO.hex,   # #001E60 – Azul Profundo
    AQUA_ALTERNO.hex,    # #05C3DE – Aqua Alterno
    AMARILLO_SURA.hex,   # #E3E829 – Amarillo SURA
    GRIS_MEDIO.hex,      # #6B6D6F – Gris Medio
]
"""Paleta categórica principal (6 colores). Ideal para series comparativas."""

CATEGORICAL_EXTENDED: List[str] = [
    "#0033A0",  # Azul SURA
    "#00AEC7",  # Aqua SURA
    "#001E60",  # Azul Profundo
    "#05C3DE",  # Aqua Alterno
    "#E3E829",  # Amarillo SURA
    "#6B6D6F",  # Gris Medio
    "#0065FF",  # Azul vibrante
    "#00875A",  # Verde positivo
    "#FF8B00",  # Naranja advertencia
    "#C7C9C7",  # Gris claro
]
"""Paleta categórica extendida (10 colores). Para visualizaciones con muchas categorías."""

CATEGORICAL_LIGHT: List[str] = [
    "#3366CC",  # Azul SURA suavizado
    "#33C9DE",  # Aqua suavizado
    "#3355A0",  # Azul profundo suavizado
    "#38D4E8",  # Aqua alterno suavizado
    "#ECF040",  # Amarillo suavizado
    "#9B9D9B",  # Gris suavizado
]
"""Paleta categórica para fondos oscuros (variantes más claras)."""

# ─────────────────────────────────────────────
#  PALETAS PARA GRÁFICAS ESPECÍFICAS
# ─────────────────────────────────────────────

BINARY: List[str] = [AZUL_SURA.hex, AQUA_SURA.hex]
"""Paleta binaria: dos categorías. Azul vs Aqua."""

POSITIVE_NEGATIVE: List[str] = [POSITIVO.hex, NEGATIVO.hex]
"""Paleta semántica: positivo (verde) vs negativo (rojo)."""

TRAFFIC_LIGHT: List[str] = [POSITIVO.hex, ADVERTENCIA.hex, NEGATIVO.hex]
"""Paleta semáforo: verde, naranja, rojo."""

STATUS_4: List[str] = [POSITIVO.hex, INFORMACION.hex, ADVERTENCIA.hex, NEGATIVO.hex]
"""Paleta de 4 estados: bueno, informativo, advertencia, crítico."""


# ─────────────────────────────────────────────
#  PALETAS SECUENCIALES (COLORMAPS)
# ─────────────────────────────────────────────

def _make_sequential_cmap(
    start_hex: str,
    end_hex: str,
    name: str,
    n: int = 256
) -> mcolors.LinearSegmentedColormap:
    """Crea un colormap secuencial entre dos colores."""
    start_rgb = mcolors.to_rgb(start_hex)
    end_rgb = mcolors.to_rgb(end_hex)
    colors_list = [
        tuple(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * t for i in range(3))
        for t in np.linspace(0, 1, n)
    ]
    return mcolors.LinearSegmentedColormap.from_list(name, colors_list, N=n)


def _make_diverging_cmap(
    low_hex: str,
    mid_hex: str,
    high_hex: str,
    name: str,
    n: int = 256
) -> mcolors.LinearSegmentedColormap:
    """Crea un colormap divergente con un color central."""
    low_rgb = mcolors.to_rgb(low_hex)
    mid_rgb = mcolors.to_rgb(mid_hex)
    high_rgb = mcolors.to_rgb(high_hex)
    half = n // 2
    colors_list = []
    for t in np.linspace(0, 1, half):
        c = tuple(low_rgb[i] + (mid_rgb[i] - low_rgb[i]) * t for i in range(3))
        colors_list.append(c)
    for t in np.linspace(0, 1, n - half):
        c = tuple(mid_rgb[i] + (high_rgb[i] - mid_rgb[i]) * t for i in range(3))
        colors_list.append(c)
    return mcolors.LinearSegmentedColormap.from_list(name, colors_list, N=n)


# Colormap secuencial: blanco → Azul SURA
SURA_BLUES = _make_sequential_cmap("#E8EDF7", AZUL_SURA.hex, "sura_blues")
"""Colormap secuencial: blanco/tenue → Azul SURA. Para heatmaps y densidades."""

# Colormap secuencial: blanco → Aqua SURA
SURA_AQUAS = _make_sequential_cmap("#E0F7FA", AQUA_SURA.hex, "sura_aquas")
"""Colormap secuencial: blanco/tenue → Aqua SURA. Alternativa fresca."""

# Colormap secuencial: Azul Profundo → Aqua Alterno
SURA_OCEAN = _make_sequential_cmap(AZUL_PROFUNDO.hex, AQUA_ALTERNO.hex, "sura_ocean")
"""Colormap secuencial: Azul Profundo → Aqua. Contraste profundo."""

# Colormap divergente: Negativo ← Neutro → Azul SURA
SURA_DIVERGING = _make_diverging_cmap(
    NEGATIVO.hex, "#F0F0F0", AZUL_SURA.hex, "sura_diverging"
)
"""Colormap divergente: rojo (bajo) ↔ neutro ↔ azul (alto). Para correlaciones."""

# Colormap divergente: Azul Profundo ← Neutro → Aqua
SURA_COOL = _make_diverging_cmap(
    AZUL_PROFUNDO.hex, "#D6EEF2", AQUA_ALTERNO.hex, "sura_cool"
)
"""Colormap divergente en tonos fríos: azul profundo ↔ aqua."""

# Registro de colormaps en matplotlib para uso con plt.get_cmap()
for _cmap in [SURA_BLUES, SURA_AQUAS, SURA_OCEAN, SURA_DIVERGING, SURA_COOL]:
    try:
        plt.colormaps.register(_cmap)
    except ValueError:
        pass  # Ya registrado


# ─────────────────────────────────────────────
#  INTERFAZ DE ACCESO
# ─────────────────────────────────────────────

_PALETTE_REGISTRY = {
    "categorical": CATEGORICAL_PRIMARY,
    "categorical_extended": CATEGORICAL_EXTENDED,
    "categorical_light": CATEGORICAL_LIGHT,
    "binary": BINARY,
    "positive_negative": POSITIVE_NEGATIVE,
    "traffic_light": TRAFFIC_LIGHT,
    "status_4": STATUS_4,
}

_CMAP_REGISTRY = {
    "sura_blues": SURA_BLUES,
    "sura_aquas": SURA_AQUAS,
    "sura_ocean": SURA_OCEAN,
    "sura_diverging": SURA_DIVERGING,
    "sura_cool": SURA_COOL,
}


def get_palette(name: str = "categorical") -> List[str]:
    """
    Retorna una paleta de colores por nombre.

    Parameters
    ----------
    name : str
        Nombre de la paleta. Opciones:
        'categorical', 'categorical_extended', 'categorical_light',
        'binary', 'positive_negative', 'traffic_light', 'status_4'

    Returns
    -------
    List[str]
        Lista de colores en formato HEX.

    Examples
    --------
    >>> from sura_brand.palettes import get_palette
    >>> colors = get_palette("categorical")
    >>> print(colors[0])  # '#0033A0'
    """
    if name not in _PALETTE_REGISTRY:
        raise KeyError(
            f"Paleta '{name}' no encontrada. "
            f"Disponibles: {list(_PALETTE_REGISTRY.keys())}"
        )
    return _PALETTE_REGISTRY[name]


def get_cmap(name: str = "sura_blues") -> mcolors.LinearSegmentedColormap:
    """
    Retorna un colormap de Matplotlib por nombre.

    Parameters
    ----------
    name : str
        Nombre del colormap. Opciones:
        'sura_blues', 'sura_aquas', 'sura_ocean',
        'sura_diverging', 'sura_cool'

    Returns
    -------
    LinearSegmentedColormap
        Colormap listo para usar en Matplotlib/Seaborn.

    Examples
    --------
    >>> from sura_brand.palettes import get_cmap
    >>> import matplotlib.pyplot as plt
    >>> cmap = get_cmap("sura_ocean")
    >>> plt.imshow([[0, 1]], cmap=cmap)
    """
    if name not in _CMAP_REGISTRY:
        raise KeyError(
            f"Colormap '{name}' no encontrado. "
            f"Disponibles: {list(_CMAP_REGISTRY.keys())}"
        )
    return _CMAP_REGISTRY[name]


def make_n_colors(n: int, palette: str = "categorical_extended") -> List[str]:
    """
    Genera exactamente N colores desde una paleta, interpolando si es necesario.

    Parameters
    ----------
    n : int
        Número de colores requeridos.
    palette : str
        Nombre de la paleta base.

    Returns
    -------
    List[str]
        Lista de N colores en formato HEX.

    Examples
    --------
    >>> from sura_brand.palettes import make_n_colors
    >>> colors = make_n_colors(3)
    >>> len(colors)
    3
    """
    base = get_palette(palette)
    if n <= len(base):
        return base[:n]
    # Interpolar usando el colormap secuencial
    cmap = SURA_OCEAN
    return [mcolors.to_hex(cmap(i / (n - 1))) for i in range(n)]


def list_palettes() -> None:
    """Imprime un resumen de todas las paletas disponibles."""
    print("\n{'═' * 50}")
    print("  PALETAS CATEGÓRICAS DISPONIBLES")
    print("{'═' * 50}")
    for name, palette in _PALETTE_REGISTRY.items():
        print(f"  [{name}]: {len(palette)} colores → {', '.join(palette)}")

    print("\n{'═' * 50}")
    print("  COLORMAPS DISPONIBLES")
    print("{'═' * 50}")
    for name in _CMAP_REGISTRY:
        print(f"  [{name}]")
