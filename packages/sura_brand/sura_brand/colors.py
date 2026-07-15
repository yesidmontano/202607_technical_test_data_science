"""
sura_brand.colors
=================
Paleta de colores oficiales de SURA basada en los lineamientos corporativos
de identidad visual (manual de marca Grupo SURA).

Fuentes:
- Pantone 286 C  → Azul SURA      #0033A0  RGB(0, 51, 160)
- Pantone 3125 C → Aqua SURA      #00AEC7  RGB(0, 174, 199)
- Pantone 2757 C → Azul Profundo  #001E60  RGB(0, 30, 96)
- Pantone 311 C  → Aqua Alterno   #05C3DE  RGB(5, 195, 222)
- Pantone 809 C  → Amarillo SURA  #E3E829  RGB(227, 232, 41)
- Pantone 420 C  → Gris Claro     #C7C9C7  RGB(199, 201, 199)
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class Color:
    """Representa un color de marca con sus distintas representaciones."""
    name: str
    hex: str
    rgb: Tuple[int, int, int]
    pantone: str = ""
    role: str = ""

    @property
    def rgb_normalized(self) -> Tuple[float, float, float]:
        """Retorna valores RGB normalizados en el rango [0, 1] para Matplotlib."""
        return tuple(c / 255.0 for c in self.rgb)

    @property
    def rgba(self, alpha: float = 1.0) -> Tuple[float, float, float, float]:
        """Retorna RGBA normalizado."""
        r, g, b = self.rgb_normalized
        return (r, g, b, alpha)

    def with_alpha(self, alpha: float) -> Tuple[float, float, float, float]:
        """Retorna el color con transparencia especificada."""
        r, g, b = self.rgb_normalized
        return (r, g, b, alpha)

    def __str__(self) -> str:
        return self.hex


# ─────────────────────────────────────────────
#  COLORES PRIMARIOS
# ─────────────────────────────────────────────

AZUL_SURA = Color(
    name="Azul SURA",
    hex="#0033A0",
    rgb=(0, 51, 160),
    pantone="Pantone 286 C",
    role="primary",
)
"""Color primario principal: Azul SURA. Utilizado en tipografía del logo."""

AQUA_SURA = Color(
    name="Aqua SURA",
    hex="#00AEC7",
    rgb=(0, 174, 199),
    pantone="Pantone 3125 C",
    role="primary",
)
"""Color primario de acento: Aqua SURA. Utilizado en el símbolo del cóndor."""

# ─────────────────────────────────────────────
#  COLORES SECUNDARIOS
# ─────────────────────────────────────────────

AZUL_PROFUNDO = Color(
    name="Azul Profundo",
    hex="#001E60",
    rgb=(0, 30, 96),
    pantone="Pantone 2757 C",
    role="secondary",
)
"""Variante oscura del azul primario. Fondos oscuros y énfasis tipográfico."""

AQUA_ALTERNO = Color(
    name="Aqua Alterno",
    hex="#05C3DE",
    rgb=(5, 195, 222),
    pantone="Pantone 311 C",
    role="secondary",
)
"""Variante más brillante del aqua. Elementos interactivos y destacados."""

AMARILLO_SURA = Color(
    name="Amarillo SURA",
    hex="#E3E829",
    rgb=(227, 232, 41),
    pantone="Pantone 809 C",
    role="secondary",
)
"""Color de alerta y contraste. Usar con moderación como acento."""

# ─────────────────────────────────────────────
#  COLORES NEUTROS
# ─────────────────────────────────────────────

GRIS_CLARO = Color(
    name="Gris Claro",
    hex="#C7C9C7",
    rgb=(199, 201, 199),
    pantone="Pantone 420 C",
    role="neutral",
)

GRIS_MEDIO = Color(
    name="Gris Medio",
    hex="#6B6D6F",
    rgb=(107, 109, 111),
    pantone="",
    role="neutral",
)

BLANCO = Color(
    name="Blanco",
    hex="#FFFFFF",
    rgb=(255, 255, 255),
    role="neutral",
)

NEGRO = Color(
    name="Negro",
    hex="#1A1A1A",
    rgb=(26, 26, 26),
    role="neutral",
)

# ─────────────────────────────────────────────
#  COLORES SEMÁNTICOS (para visualizaciones)
# ─────────────────────────────────────────────

POSITIVO = Color(
    name="Positivo",
    hex="#00875A",
    rgb=(0, 135, 90),
    role="semantic",
)

NEGATIVO = Color(
    name="Negativo",
    hex="#DE350B",
    rgb=(222, 53, 11),
    role="semantic",
)

ADVERTENCIA = Color(
    name="Advertencia",
    hex="#FF8B00",
    rgb=(255, 139, 0),
    role="semantic",
)

INFORMACION = Color(
    name="Información",
    hex="#0065FF",
    rgb=(0, 101, 255),
    role="semantic",
)

# ─────────────────────────────────────────────
#  COLECCIONES
# ─────────────────────────────────────────────

PRIMARY: Dict[str, Color] = {
    "azul_sura": AZUL_SURA,
    "aqua_sura": AQUA_SURA,
}

SECONDARY: Dict[str, Color] = {
    "azul_profundo": AZUL_PROFUNDO,
    "aqua_alterno": AQUA_ALTERNO,
    "amarillo_sura": AMARILLO_SURA,
}

NEUTRAL: Dict[str, Color] = {
    "blanco": BLANCO,
    "gris_claro": GRIS_CLARO,
    "gris_medio": GRIS_MEDIO,
    "negro": NEGRO,
}

SEMANTIC: Dict[str, Color] = {
    "positivo": POSITIVO,
    "negativo": NEGATIVO,
    "advertencia": ADVERTENCIA,
    "informacion": INFORMACION,
}

ALL_COLORS: Dict[str, Color] = {
    **PRIMARY,
    **SECONDARY,
    **NEUTRAL,
    **SEMANTIC,
}


def get_color(name: str) -> Color:
    """
    Recupera un color por su nombre clave.

    Parameters
    ----------
    name : str
        Nombre clave del color (ej. 'azul_sura', 'aqua_sura').

    Returns
    -------
    Color
        Objeto Color con las propiedades del color solicitado.

    Raises
    ------
    KeyError
        Si el nombre no existe en el catálogo de colores.

    Examples
    --------
    >>> from sura_brand.colors import get_color
    >>> azul = get_color("azul_sura")
    >>> print(azul.hex)
    '#0033A0'
    """
    if name not in ALL_COLORS:
        available = list(ALL_COLORS.keys())
        raise KeyError(f"Color '{name}' no encontrado. Disponibles: {available}")
    return ALL_COLORS[name]


def list_colors() -> None:
    """Imprime un resumen de todos los colores disponibles."""
    groups = {
        "Primarios": PRIMARY,
        "Secundarios": SECONDARY,
        "Neutros": NEUTRAL,
        "Semánticos": SEMANTIC,
    }
    for group_name, group in groups.items():
        print(f"\n{'═' * 40}")
        print(f"  {group_name}")
        print(f"{'═' * 40}")
        for key, color in group.items():
            pantone_str = f" ({color.pantone})" if color.pantone else ""
            print(f"  [{key}]  {color.name}{pantone_str}")
            print(f"    HEX: {color.hex}  |  RGB: {color.rgb}")
