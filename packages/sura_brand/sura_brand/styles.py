"""
sura_brand.styles
=================
Configuración global de estilos para Matplotlib y Seaborn bajo los
estándares de identidad visual de SURA.

Uso básico:
    >>> from sura_brand.styles import apply_sura_style
    >>> apply_sura_style()           # Estilo claro por defecto
    >>> apply_sura_style("dark")     # Estilo oscuro

Uso con contexto temporal:
    >>> from sura_brand.styles import sura_style
    >>> with sura_style("light"):
    ...     fig, ax = plt.subplots()
    ...     ax.plot(x, y)
"""

from __future__ import annotations

import contextlib
import warnings
from typing import Dict, Literal, Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

from sura_brand.colors import (
    AZUL_SURA, AQUA_SURA, AZUL_PROFUNDO, GRIS_CLARO,
    GRIS_MEDIO, BLANCO, NEGRO,
)
from sura_brand.palettes import CATEGORICAL_PRIMARY, CATEGORICAL_LIGHT
from sura_brand.typography import get_matplotlib_font_params, FONT_PRIMARY


StyleMode = Literal["light", "dark"]


# ─────────────────────────────────────────────
#  DEFINICIÓN DE ESTILOS
# ─────────────────────────────────────────────

def _build_light_style() -> Dict:
    """Construye el diccionario de parámetros para estilo claro."""
    font_params = get_matplotlib_font_params(FONT_PRIMARY)

    return {
        # ── Figura ──────────────────────────────
        "figure.facecolor": "#FAFAFA",
        "figure.edgecolor": "#FAFAFA",
        "figure.figsize": (12, 7),
        "figure.dpi": 100,

        # ── Ejes ────────────────────────────────
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#D0D0D0",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.titlepad": 8,
        "axes.titleweight": "bold",
        "axes.titlecolor": NEGRO.hex,
        "axes.labelcolor": GRIS_MEDIO.hex,
        "axes.labelpad": 4,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL_PRIMARY),

        # ── Grid ────────────────────────────────
        "grid.color": "#E5E5E5",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.8,
        "grid.linestyle": "--",

        # ── Ticks ───────────────────────────────
        "xtick.color": GRIS_MEDIO.hex,
        "ytick.color": GRIS_MEDIO.hex,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,

        # ── Leyenda ─────────────────────────────
        "legend.facecolor": "#FFFFFF",
        "legend.edgecolor": "#D0D0D0",
        "legend.framealpha": 0.9,
        "legend.frameon": True,
        "legend.borderpad": 0.6,
        "legend.loc": "best",

        # ── Texto ───────────────────────────────
        "text.color": NEGRO.hex,

        # ── Líneas ──────────────────────────────
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
        "lines.markeredgewidth": 0.5,

        # ── Barras ──────────────────────────────
        "patch.linewidth": 0.5,
        "patch.edgecolor": "#FFFFFF",
        "patch.force_edgecolor": True,

        # ── Scatter ─────────────────────────────
        "scatter.edgecolors": "none",

        # ── Histograma ──────────────────────────
        "hist.bins": 20,

        # ── Guardado ────────────────────────────
        # Do NOT use bbox='tight': it collapses header/footer margins reserved
        # by create_dashboard / create_report_figure and causes title/footer overlap.
        "savefig.facecolor": "#FAFAFA",
        "savefig.edgecolor": "none",
        "savefig.bbox": None,
        "savefig.dpi": 150,
        "savefig.transparent": False,

        **font_params,
    }


def _build_dark_style() -> Dict:
    """Construye el diccionario de parámetros para estilo oscuro."""
    font_params = get_matplotlib_font_params(FONT_PRIMARY)
    BG = "#0D1B2E"       # Fondo muy oscuro (azul-noche SURA)
    CARD = "#162035"     # Fondo de tarjeta
    BORDER = "#2A3A5C"   # Borde sutil
    TEXT = "#E8ECEF"     # Texto principal
    MUTED = "#8FA0BC"    # Texto secundario

    return {
        # ── Figura ──────────────────────────────
        "figure.facecolor": BG,
        "figure.edgecolor": BG,
        "figure.figsize": (12, 7),
        "figure.dpi": 100,

        # ── Ejes ────────────────────────────────
        "axes.facecolor": CARD,
        "axes.edgecolor": BORDER,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.titlepad": 8,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXT,
        "axes.labelcolor": MUTED,
        "axes.labelpad": 4,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL_LIGHT),

        # ── Grid ────────────────────────────────
        "grid.color": "#1E2E4A",
        "grid.linewidth": 0.6,
        "grid.alpha": 1.0,
        "grid.linestyle": "--",

        # ── Ticks ───────────────────────────────
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 4,
        "ytick.major.size": 4,

        # ── Leyenda ─────────────────────────────
        "legend.facecolor": CARD,
        "legend.edgecolor": BORDER,
        "legend.framealpha": 0.95,
        "legend.frameon": True,
        "legend.borderpad": 0.6,

        # ── Texto ───────────────────────────────
        "text.color": TEXT,

        # ── Líneas ──────────────────────────────
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
        "lines.markeredgewidth": 0.0,

        # ── Barras ──────────────────────────────
        "patch.linewidth": 0.0,
        "patch.edgecolor": "none",
        "patch.force_edgecolor": False,

        # ── Scatter ─────────────────────────────
        "scatter.edgecolors": "none",

        # ── Histograma ──────────────────────────
        "hist.bins": 20,

        # ── Guardado ────────────────────────────
        "savefig.facecolor": BG,
        "savefig.edgecolor": "none",
        "savefig.bbox": None,
        "savefig.dpi": 150,
        "savefig.transparent": False,

        **font_params,
    }


STYLES: Dict[StyleMode, Dict] = {
    "light": _build_light_style(),
    "dark": _build_dark_style(),
}


# ─────────────────────────────────────────────
#  FUNCIONES PRINCIPALES
# ─────────────────────────────────────────────

def apply_sura_style(
    mode: StyleMode = "light",
    seaborn_context: str = "notebook",
    seaborn_style: Optional[str] = None,
) -> None:
    """
    Aplica el estilo visual de SURA globalmente a Matplotlib y Seaborn.

    Este es el punto de entrada principal. Llámalo una vez al inicio de
    cada notebook o script de visualización.

    Parameters
    ----------
    mode : {'light', 'dark'}
        Tema de color. 'light' para fondos blancos/grises,
        'dark' para fondos oscuros. Por defecto 'light'.
    seaborn_context : str
        Contexto de Seaborn: 'paper', 'notebook', 'talk', 'poster'.
        Por defecto 'notebook'.
    seaborn_style : str, optional
        Estilo base de Seaborn a aplicar antes del estilo SURA.
        Si None, no se aplica estilo base de Seaborn.

    Examples
    --------
    >>> from sura_brand.styles import apply_sura_style
    >>> apply_sura_style()                    # Estilo claro
    >>> apply_sura_style("dark")              # Estilo oscuro
    >>> apply_sura_style("light", "talk")     # Para presentaciones
    """
    if mode not in STYLES:
        raise ValueError(f"Modo '{mode}' no válido. Use 'light' o 'dark'.")

    # Aplicar estilo Seaborn base si se especifica
    if seaborn_style:
        sns.set_style(seaborn_style)

    # Aplicar contexto Seaborn
    sns.set_context(seaborn_context)

    # Aplicar parámetros SURA sobre Matplotlib
    mpl.rcParams.update(STYLES[mode])

    # Configurar paleta por defecto en Seaborn
    from sura_brand.palettes import CATEGORICAL_PRIMARY, CATEGORICAL_LIGHT
    palette = CATEGORICAL_PRIMARY if mode == "light" else CATEGORICAL_LIGHT
    sns.set_palette(palette)


def reset_style() -> None:
    """
    Restaura los estilos de Matplotlib y Seaborn a sus valores por defecto.

    Examples
    --------
    >>> from sura_brand.styles import reset_style
    >>> reset_style()
    """
    mpl.rcdefaults()
    sns.reset_defaults()


@contextlib.contextmanager
def sura_style(mode: StyleMode = "light", **kwargs):
    """
    Context manager que aplica el estilo SURA temporalmente.

    Al salir del bloque `with`, restaura el estilo previo.

    Parameters
    ----------
    mode : {'light', 'dark'}
        Tema de color.
    **kwargs
        Parámetros adicionales pasados a `apply_sura_style`.

    Examples
    --------
    >>> from sura_brand.styles import sura_style
    >>> import matplotlib.pyplot as plt
    >>> with sura_style("dark"):
    ...     fig, ax = plt.subplots()
    ...     ax.plot([1, 2, 3], [1, 4, 9])
    ...     plt.show()
    """
    prev_params = dict(mpl.rcParams)
    try:
        apply_sura_style(mode, **kwargs)
        yield
    finally:
        mpl.rcParams.update(prev_params)


def get_style_params(mode: StyleMode = "light") -> Dict:
    """
    Retorna el diccionario de parámetros del estilo sin aplicarlo.

    Útil para inspeccionar o modificar la configuración antes de usarla.

    Parameters
    ----------
    mode : {'light', 'dark'}
        Tema de color.

    Returns
    -------
    Dict
        Diccionario de parámetros rcParams de Matplotlib.
    """
    return dict(STYLES[mode])
