"""
Análisis Univariado – Distribuciones de Variables Clave
=========================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.2 – EDA

Descripción:
    Genera distribuciones univariadas de la frecuencia de siniestros,
    la severidad (días de incapacidad), los costos (asistencial y
    prestaciones económicas) y el tamaño de las empresas afiliadas.

    Adicionalmente:
    · Construye los datasets de staging para reutilización en S02-S05.
    · Guarda todas las figuras en results/imgs/.
    · Registra hallazgos clave para Insights_EDA.md.

Inputs:
    - data/raw/empresas.csv
    - data/raw/siniestros.csv

Outputs:
    - data/staging/S01/empresas_staging.parquet
    - data/staging/S01/siniestros_staging.parquet
    - data/staging/S01/siniestralidad_empresa.parquet
    - sections/S01-.../results/imgs/01_*.png

Uso:
    .venv/bin/python sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/01-analisis_univariado/analisis_univariado.py
"""

# ──────────────────────────────────────────────────────────────────────────────
#  Importaciones
# ──────────────────────────────────────────────────────────────────────────────
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import scipy.stats as stats
import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
#  Configuración global
# ──────────────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Rutas relativas al proyecto (ajustar N según profundidad del script)
ROOT = Path(__file__).resolve().parents[5]
DATA_RAW = ROOT / "data" / "raw"
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_IMGS = (
    ROOT / "sections"
    / "S01-Metodologia_EDA_Analisis"
    / "1_2_EDA"
    / "results"
    / "imgs"
)

DATA_STAGING.mkdir(parents=True, exist_ok=True)
RESULTS_IMGS.mkdir(parents=True, exist_ok=True)

# Aplicar estilo visual SURA
sb.apply_sura_style()

# ──────────────────────────────────────────────────────────────────────────────
#  1. Carga de datos raw
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Cargando datos raw...")

empresas = pd.read_csv(DATA_RAW / "empresas.csv", parse_dates=["fecha_afiliacion"])
siniestros = pd.read_csv(DATA_RAW / "siniestros.csv", parse_dates=["fecha_ocurrencia"])

print(f"   empresas   : {empresas.shape}")
print(f"   siniestros : {siniestros.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  2. Preprocesamiento y staging
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔧  Construyendo datasets de staging...")

# ---- 2.1  Empresas staging -----------------------------------------------
empresas_stg = empresas.copy()
empresas_stg["anio_afiliacion"] = empresas_stg["fecha_afiliacion"].dt.year
empresas_stg["log_n_trabajadores"] = np.log1p(empresas_stg["n_trabajadores"])
empresas_stg["log_prima_anual"] = np.log1p(empresas_stg["prima_anual"])
empresas_stg["clase_riesgo"] = empresas_stg["clase_riesgo"].astype("category")
empresas_stg["sector"] = empresas_stg["sector"].astype("category")

# ---- 2.2  Siniestros staging ---------------------------------------------
siniestros_stg = siniestros.copy()
siniestros_stg["anio"] = siniestros_stg["fecha_ocurrencia"].dt.year
siniestros_stg["mes"] = siniestros_stg["fecha_ocurrencia"].dt.month
siniestros_stg["costo_total"] = (
    siniestros_stg["costo_asistencial"] + siniestros_stg["costo_prestacion_economica"]
)
siniestros_stg["log_costo_total"] = np.log1p(siniestros_stg["costo_total"])
siniestros_stg["log_dias_incapacidad"] = np.log1p(siniestros_stg["dias_incapacidad"])
siniestros_stg["tipo"] = siniestros_stg["tipo"].astype("category")
siniestros_stg["gravedad"] = siniestros_stg["gravedad"].astype("category")

# ---- 2.3  Siniestralidad por empresa -------------------------------------
sin_empresa = (
    siniestros_stg.groupby("id_empresa")
    .agg(
        n_siniestros=("id_siniestro", "count"),
        total_dias_incapacidad=("dias_incapacidad", "sum"),
        costo_total_empresa=("costo_total", "sum"),
        costo_asistencial_total=("costo_asistencial", "sum"),
        costo_prestacion_total=("costo_prestacion_economica", "sum"),
        costo_medio_siniestro=("costo_total", "mean"),
        severidad_media=("dias_incapacidad", "mean"),
        anio_primero=("anio", "min"),
        anio_ultimo=("anio", "max"),
    )
    .reset_index()
)

sin_empresa = sin_empresa.merge(
    empresas_stg[["id_empresa", "n_trabajadores", "clase_riesgo", "sector",
                  "departamento", "ciudad", "prima_anual", "antiguedad_meses"]],
    on="id_empresa",
    how="left",
)

# Frecuencia por 100 trabajadores
sin_empresa["frecuencia_x100"] = (
    sin_empresa["n_siniestros"] / sin_empresa["n_trabajadores"].clip(lower=1) * 100
)
sin_empresa["log_frecuencia_x100"] = np.log1p(sin_empresa["frecuencia_x100"])

# ---- 2.4  Guardar staging ------------------------------------------------
empresas_stg.to_parquet(DATA_STAGING / "empresas_staging.parquet", index=False)
siniestros_stg.to_parquet(DATA_STAGING / "siniestros_staging.parquet", index=False)
sin_empresa.to_parquet(DATA_STAGING / "siniestralidad_empresa.parquet", index=False)

print(f"   ✅  Guardados en {DATA_STAGING}")
print(f"      - empresas_staging.parquet        : {empresas_stg.shape}")
print(f"      - siniestros_staging.parquet      : {siniestros_stg.shape}")
print(f"      - siniestralidad_empresa.parquet  : {sin_empresa.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _add_stats_box(ax: plt.Axes, data: pd.Series, prefix: str = "") -> None:
    """Inserta un textbox con estadísticas básicas dentro del eje."""
    clean = data.dropna()
    txt = (
        f"n = {len(clean):,}\n"
        f"Media  = {clean.mean():,.2f}\n"
        f"Mediana= {clean.median():,.2f}\n"
        f"σ      = {clean.std():,.2f}\n"
        f"Asim.  = {clean.skew():.2f}\n"
        f"Kurt.  = {clean.kurtosis():.2f}"
    )
    ax.text(
        0.97, 0.97, txt,
        transform=ax.transAxes,
        fontsize=8, verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                  edgecolor="#C7C9C7", alpha=0.85),
    )


def _save_fig(fig: plt.Figure, name: str) -> None:
    """Guarda figura en RESULTS_IMGS con DPI estándar."""
    path = RESULTS_IMGS / name
    # Avoid bbox_inches='tight' — it collapses carefully reserved header/footer margins
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _fmt_millones(x, _):
    """Formatea etiquetas en millones de pesos."""
    return f"${x / 1e6:.1f}M"


def _fmt_miles(x, _):
    """Formatea etiquetas en miles."""
    return f"{x / 1e3:.0f}K"


# ──────────────────────────────────────────────────────────────────────────────
#  3.  BLOQUE A – Frecuencia de siniestros
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOQUE A – Frecuencia de siniestros")

# ---- A1. Distribución de n° de siniestros por empresa (conteo) ------------
fig, axes = sb.create_dashboard(
    1, 2,
    title="Frecuencia de Siniestros por Empresa",
    subtitle="Distribución del número total de siniestros (2018-2024)",
)
ax_left, ax_right = axes[0], axes[1]

freq = sin_empresa["n_siniestros"]
ax_left.hist(freq, bins=50, color=sb.AZUL_SURA.hex, edgecolor="white", linewidth=0.4)
ax_left.set_xlabel("Número de siniestros por empresa")
ax_left.set_ylabel("Frecuencia (empresas)")
ax_left.set_title("Histograma – N° siniestros")
_add_stats_box(ax_left, freq)

# Q-Q plot contra Poisson
theoretical_quantiles = np.arange(1, len(freq) + 1) / (len(freq) + 1)
empirical_sorted = np.sort(freq)
poisson_quantiles = stats.poisson.ppf(theoretical_quantiles, mu=freq.mean())
ax_right.scatter(poisson_quantiles, empirical_sorted,
                 color=sb.AQUA_SURA.hex, s=8, alpha=0.5)
lim_max = max(poisson_quantiles.max(), empirical_sorted.max())
ax_right.plot([0, lim_max], [0, lim_max], "k--", linewidth=1, label="Referencia Poisson")
ax_right.set_xlabel("Cuantiles Poisson teóricos")
ax_right.set_ylabel("Cuantiles empíricos")
ax_right.set_title("Q-Q vs. Poisson")
ax_right.legend(fontsize=8)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Frecuencia")
_save_fig(fig, "01_A1_frecuencia_siniestros_empresa.png")

# ---- A2. Frecuencia por 100 trabajadores ----------------------------------
fig, axes = sb.create_dashboard(
    1, 2,
    title="Frecuencia Relativa por 100 Trabajadores",
    subtitle="Tasa de siniestros ajustada por tamaño de plantilla",
)
ax_left, ax_right = axes[0], axes[1]

freq_r = sin_empresa["frecuencia_x100"]
ax_left.hist(freq_r.clip(upper=freq_r.quantile(0.99)), bins=60,
             color=sb.AZUL_SURA.hex, edgecolor="white", linewidth=0.4)
ax_left.set_xlabel("Siniestros por 100 trabajadores")
ax_left.set_ylabel("Frecuencia (empresas)")
ax_left.set_title("Histograma – Frecuencia relativa")
_add_stats_box(ax_left, freq_r)

# Por clase de riesgo
palette = sb.get_palette("categorical")
for i, (cr, grp) in enumerate(sin_empresa.groupby("clase_riesgo")):
    ax_right.hist(
        grp["frecuencia_x100"].clip(upper=freq_r.quantile(0.99)),
        bins=30, alpha=0.55, label=f"Clase {cr}",
        color=palette[i % len(palette)], edgecolor="white", linewidth=0.3,
    )
ax_right.set_xlabel("Siniestros por 100 trabajadores")
ax_right.set_ylabel("Frecuencia (empresas)")
ax_right.set_title("Por clase de riesgo")
ax_right.legend(fontsize=8)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Frecuencia relativa")
_save_fig(fig, "01_A2_frecuencia_relativa_clase_riesgo.png")

# ---- A3. Frecuencia anual global (evolución temporal) --------------------
sin_anio = siniestros_stg.groupby("anio").size().reset_index(name="n_siniestros")
fig, ax = sb.line_chart(
    x=sin_anio["anio"].astype(str).tolist(),
    y={"Total siniestros": sin_anio["n_siniestros"].tolist()},
    title="Volumen Anual de Siniestros",
)
ax.set_xlabel("Año")
ax.set_ylabel("Número de siniestros")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Tendencia temporal")
_save_fig(fig, "01_A3_frecuencia_anual_temporal.png")

# ──────────────────────────────────────────────────────────────────────────────
#  4.  BLOQUE B – Severidad (días de incapacidad)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOQUE B – Severidad (días de incapacidad)")

# ---- B1. Distribución de días de incapacidad por siniestro ---------------
fig, axes = sb.create_dashboard(
    1, 3,
    title="Severidad – Días de Incapacidad por Siniestro",
    subtitle="Distribución de la variable de severidad (escala natural y logarítmica)",
)
ax1, ax2, ax3 = axes[0], axes[1], axes[2]

dias = siniestros_stg["dias_incapacidad"].dropna()
ax1.hist(dias.clip(upper=dias.quantile(0.99)), bins=60,
         color=sb.AQUA_SURA.hex, edgecolor="white", linewidth=0.4)
ax1.set_xlabel("Días de incapacidad")
ax1.set_ylabel("Frecuencia (siniestros)")
ax1.set_title("Histograma – Escala natural")
_add_stats_box(ax1, dias)

log_dias = siniestros_stg["log_dias_incapacidad"].dropna()
ax2.hist(log_dias, bins=60, color=sb.AQUA_SURA.hex, edgecolor="white", linewidth=0.4)
ax2.set_xlabel("log(1 + días de incapacidad)")
ax2.set_ylabel("Frecuencia")
ax2.set_title("Histograma – Escala log")

# CDF empírica
sorted_dias = np.sort(dias)
cdf_vals = np.arange(1, len(sorted_dias) + 1) / len(sorted_dias)
ax3.plot(sorted_dias, cdf_vals, color=sb.AZUL_SURA.hex, linewidth=1.5)
ax3.axvline(dias.median(), color=sb.AMARILLO_SURA.hex, linestyle="--",
            linewidth=1.5, label=f"Mediana = {dias.median():.0f} d")
ax3.axvline(dias.quantile(0.9), color="#E36928", linestyle=":",
            linewidth=1.5, label=f"P90 = {dias.quantile(0.9):.0f} d")
ax3.set_xlabel("Días de incapacidad")
ax3.set_ylabel("Probabilidad acumulada")
ax3.set_title("CDF empírica")
ax3.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Severidad")
_save_fig(fig, "01_B1_severidad_dias_incapacidad.png")

# ---- B2. Severidad media por empresa vs tipo de siniestro ----------------
fig, ax = sb.create_report_figure(
    title="Severidad Media por Tipo de Siniestro",
    subtitle="Comparación AT vs EL – días de incapacidad por evento",
)
for i, (tipo, grp) in enumerate(siniestros_stg.groupby("tipo")):
    ax.hist(
        grp["dias_incapacidad"].clip(upper=dias.quantile(0.99)),
        bins=50, alpha=0.65, label=tipo,
        color=palette[i % len(palette)], edgecolor="white", linewidth=0.3,
    )
ax.set_xlabel("Días de incapacidad")
ax.set_ylabel("Frecuencia")
ax.set_title("AT vs EL – Distribución de severidad")
ax.legend(fontsize=9)
_add_stats_box(ax, dias)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Severidad por tipo")
_save_fig(fig, "01_B2_severidad_por_tipo.png")

# ── Boxplot severidad por gravedad ─────────────────────────────────────────
orden_gravedad = ["leve", "moderado", "grave", "mortal"]
orden_gravedad = [g for g in orden_gravedad
                  if g in siniestros_stg["gravedad"].cat.categories.tolist()]

fig, ax = sb.boxplot_chart(
    data=siniestros_stg,
    x="gravedad",
    y="dias_incapacidad",
)
ax.set_title("Severidad por Nivel de Gravedad")
ax.set_xlabel("Gravedad del siniestro")
ax.set_ylabel("Días de incapacidad")
ax.set_ylim(0, siniestros_stg["dias_incapacidad"].quantile(0.97))
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Boxplot severidad")
_save_fig(fig, "01_B3_boxplot_severidad_gravedad.png")

# ──────────────────────────────────────────────────────────────────────────────
#  5.  BLOQUE C – Costos (asistencial + prestaciones económicas)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOQUE C – Costos")

# ---- C1. Distribución costo total por siniestro --------------------------
fig, axes = sb.create_dashboard(
    2, 2,
    title="Distribución de Costos por Siniestro",
    subtitle="Costo asistencial, prestaciones económicas y costo total (COP)",
)
ax_list = axes

cost_vars = [
    ("costo_asistencial", "Costo Asistencial", sb.AZUL_SURA.hex),
    ("costo_prestacion_economica", "Prestaciones Económicas", sb.AQUA_SURA.hex),
    ("costo_total", "Costo Total", sb.AZUL_PROFUNDO.hex),
    ("log_costo_total", "log(1 + Costo Total)", sb.AQUA_ALTERNO.hex),
]

for ax, (col, label, color) in zip(ax_list, cost_vars):
    data = siniestros_stg[col].dropna()
    cap = data.quantile(0.99) if "log" not in col else data.max()
    ax.hist(data.clip(upper=cap), bins=60, color=color,
            edgecolor="white", linewidth=0.3)
    ax.set_xlabel(label)
    ax.set_ylabel("Frecuencia")
    ax.set_title(label)
    if "log" not in col:
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
    _add_stats_box(ax, data)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Costos por siniestro")
_save_fig(fig, "01_C1_distribucion_costos_siniestro.png")

# ---- C2. Costo total acumulado por empresa --------------------------------
fig, axes = sb.create_dashboard(
    1, 2,
    title="Costo Total Acumulado por Empresa",
    subtitle="Suma de costos (2018-2024) por empresa asegurada",
)
ax_left, ax_right = axes[0], axes[1]

costo_emp = sin_empresa["costo_total_empresa"]
ax_left.hist(costo_emp.clip(upper=costo_emp.quantile(0.99)), bins=60,
             color=sb.AZUL_PROFUNDO.hex, edgecolor="white", linewidth=0.4)
ax_left.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax_left.set_xlabel("Costo total acumulado (COP)")
ax_left.set_ylabel("Frecuencia (empresas)")
ax_left.set_title("Histograma – Costo acumulado empresa")
_add_stats_box(ax_left, costo_emp)

log_costo = np.log1p(costo_emp)
ax_right.hist(log_costo, bins=60, color=sb.AQUA_ALTERNO.hex,
              edgecolor="white", linewidth=0.4)
ax_right.set_xlabel("log(1 + Costo acumulado)")
ax_right.set_ylabel("Frecuencia")
ax_right.set_title("Transformación logarítmica")
_add_stats_box(ax_right, log_costo)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Costo acumulado empresa")
_save_fig(fig, "01_C2_costo_acumulado_empresa.png")

# ---- C3. Concentración de costos (curva de Lorenz) ----------------------
fig, ax = sb.create_report_figure(
    title="Concentración de Costos – Curva de Lorenz",
    subtitle="¿Qué porcentaje de empresas concentra qué porcentaje del costo total?",
)

sorted_c = np.sort(costo_emp.fillna(0))
cum_c = np.cumsum(sorted_c) / sorted_c.sum()
pct_empresas = np.arange(1, len(sorted_c) + 1) / len(sorted_c)

ax.plot(pct_empresas, cum_c, color=sb.AZUL_SURA.hex, linewidth=2.5,
        label="Curva de Lorenz")
ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Igualdad perfecta")
# Anotar Gini aproximado
gini_approx = 1 - 2 * np.trapezoid(cum_c, pct_empresas)
ax.text(0.05, 0.90, f"Gini ≈ {gini_approx:.3f}",
        transform=ax.transAxes, fontsize=10, color=sb.AZUL_SURA.hex,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                  edgecolor=sb.AZUL_SURA.hex, alpha=0.85))
# Anotar concentración P80/P20
p20_idx = int(0.2 * len(sorted_c))
p80_pct_cost = 1 - cum_c[p20_idx]
ax.annotate(
    f"Top 20% empresas\n= {p80_pct_cost * 100:.1f}% del costo",
    xy=(0.8, cum_c[int(0.8 * len(sorted_c))]),
    xytext=(0.55, 0.4),
    arrowprops=dict(arrowstyle="->", color=sb.AQUA_SURA.hex),
    fontsize=9, color=sb.AZUL_PROFUNDO.hex,
)
ax.set_xlabel("Fracción acumulada de empresas (menor a mayor costo)")
ax.set_ylabel("Fracción acumulada del costo total")
ax.legend(fontsize=9)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Concentración de costos")
_save_fig(fig, "01_C3_lorenz_concentracion_costos.png")

# ──────────────────────────────────────────────────────────────────────────────
#  6.  BLOQUE D – Tamaño de las empresas
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOQUE D – Tamaño de las empresas")

# ---- D1. Distribución del número de trabajadores -------------------------
fig, axes = sb.create_dashboard(
    1, 3,
    title="Distribución del Tamaño de las Empresas",
    subtitle="N° de trabajadores afiliados por empresa",
)
ax1, ax2, ax3 = axes[0], axes[1], axes[2]

trab = empresas_stg["n_trabajadores"]
ax1.hist(trab.clip(upper=trab.quantile(0.99)), bins=60,
         color=sb.AZUL_SURA.hex, edgecolor="white", linewidth=0.4)
ax1.set_xlabel("N° de trabajadores")
ax1.set_ylabel("Empresas")
ax1.set_title("Histograma – Escala natural")
_add_stats_box(ax1, trab)

log_trab = empresas_stg["log_n_trabajadores"]
ax2.hist(log_trab, bins=60, color=sb.AQUA_SURA.hex, edgecolor="white", linewidth=0.4)
ax2.set_xlabel("log(1 + N° trabajadores)")
ax2.set_ylabel("Empresas")
ax2.set_title("Histograma – Escala log")
_add_stats_box(ax2, log_trab)

# Segmentación por tamaño
bins_size = [0, 10, 50, 200, np.inf]
labels_size = ["Micro (≤10)", "Pequeña (11-50)", "Mediana (51-200)", "Grande (>200)"]
empresas_stg["segmento"] = pd.cut(trab, bins=bins_size, labels=labels_size)
seg_counts = empresas_stg["segmento"].value_counts().reindex(labels_size)

bars = ax3.bar(seg_counts.index, seg_counts.values,
               color=sb.get_palette("categorical")[:4],
               edgecolor="white", linewidth=0.5)
ax3.bar_label(bars, labels=[f"{v:,}" for v in seg_counts.values],
              padding=3, fontsize=8)
ax3.set_ylabel("Empresas")
ax3.set_title("Por segmento de tamaño")
ax3.tick_params(axis="x", labelrotation=15)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Tamaño empresas")
_save_fig(fig, "01_D1_distribucion_n_trabajadores.png")

# ---- D2. Prima anual (proxy del volumen económico del cliente) -----------
fig, axes = sb.create_dashboard(
    1, 2,
    title="Prima Anual – Distribución por Empresa",
    subtitle="Proxy del volumen económico del portafolio asegurado",
)
ax_l, ax_r = axes[0], axes[1]

prima = empresas_stg["prima_anual"]
ax_l.hist(prima.clip(upper=prima.quantile(0.99)), bins=60,
          color=sb.AZUL_PROFUNDO.hex, edgecolor="white", linewidth=0.4)
ax_l.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax_l.set_xlabel("Prima anual (COP)")
ax_l.set_ylabel("Empresas")
ax_l.set_title("Histograma – Escala natural")
_add_stats_box(ax_l, prima)

log_prima = empresas_stg["log_prima_anual"]
ax_r.hist(log_prima, bins=60, color=sb.AQUA_ALTERNO.hex,
          edgecolor="white", linewidth=0.4)
ax_r.set_xlabel("log(1 + Prima anual)")
ax_r.set_ylabel("Empresas")
ax_r.set_title("Histograma – Escala log")
_add_stats_box(ax_r, log_prima)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Prima anual")
_save_fig(fig, "01_D2_prima_anual_empresa.png")

# ---- D3. Antigüedad vs clase de riesgo (distribución) -------------------
fig, ax = sb.create_report_figure(
    title="Antigüedad de Afiliación por Clase de Riesgo",
    subtitle="Distribución de meses de afiliación según clase de riesgo ARL",
)
for i, (cr, grp) in enumerate(empresas_stg.groupby("clase_riesgo")):
    ax.hist(
        grp["antiguedad_meses"].clip(upper=empresas_stg["antiguedad_meses"].quantile(0.99)),
        bins=30, alpha=0.55,
        label=f"Clase {cr}",
        color=palette[i % len(palette)],
        edgecolor="white", linewidth=0.3,
    )
ax.set_xlabel("Meses de afiliación")
ax.set_ylabel("Frecuencia (empresas)")
ax.legend(fontsize=9)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Antigüedad")
_save_fig(fig, "01_D3_antiguedad_clase_riesgo.png")

# ──────────────────────────────────────────────────────────────────────────────
#  7.  BLOQUE E – Resumen tipo de siniestro y gravedad (categóricas clave)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOQUE E – Variables categóricas clave")

# ---- E1. Tipo de siniestro -----------------------------------------------
tipo_counts = siniestros_stg["tipo"].value_counts()
fig, ax = sb.pie_chart(
    values=tipo_counts.values.tolist(),
    labels=tipo_counts.index.tolist(),
    donut=True,
)
ax.set_title("Distribución de Siniestros por Tipo")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Tipo de siniestro")
_save_fig(fig, "01_E1_tipo_siniestro.png")

# ---- E2. Gravedad del siniestro ------------------------------------------
grav_counts = siniestros_stg["gravedad"].value_counts()
fig, ax = sb.bar_chart(
    x=grav_counts.index.tolist(),
    y=grav_counts.values.tolist(),
    title="Distribución de Siniestros por Gravedad",
    horizontal=False,
)
ax.set_xlabel("Nivel de gravedad")
ax.set_ylabel("Número de siniestros")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Gravedad")
_save_fig(fig, "01_E2_gravedad_siniestro.png")

# ---- E3. Distribución por sector de las empresas -------------------------
sector_counts = empresas_stg["sector"].value_counts()
fig, ax = sb.bar_chart(
    x=sector_counts.index.tolist(),
    y=sector_counts.values.tolist(),
    title="Empresas por Sector Económico",
    horizontal=True,
)
ax.set_xlabel("Número de empresas")
ax.set_ylabel("Sector")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Univariado | Sector económico")
_save_fig(fig, "01_E3_empresas_por_sector.png")

# ──────────────────────────────────────────────────────────────────────────────
#  8.  Estadísticas resumen para insights
# ──────────────────────────────────────────────────────────────────────────────
print("\n📈  Estadísticas resumen:")

# Frecuencia
pct_sin_siniestros = (
    len(empresas_stg) - sin_empresa.shape[0]
) / len(empresas_stg) * 100

# Costos
median_costo = siniestros_stg["costo_total"].median()
p90_costo = siniestros_stg["costo_total"].quantile(0.90)
p10_costo_emp = sin_empresa["costo_total_empresa"].quantile(0.10)
top10_share = (
    sin_empresa.nlargest(int(len(sin_empresa) * 0.10), "costo_total_empresa")
    ["costo_total_empresa"].sum()
    / sin_empresa["costo_total_empresa"].sum() * 100
)

# Severidad
median_dias = siniestros_stg["dias_incapacidad"].median()
p90_dias = siniestros_stg["dias_incapacidad"].quantile(0.90)
skew_dias = siniestros_stg["dias_incapacidad"].skew()

# Tamaño
pct_micro = (empresas_stg["segmento"] == "Micro (≤10)").mean() * 100
pct_pyme = (empresas_stg["segmento"].isin(
    ["Pequeña (11-50)", "Mediana (51-200)"]
)).mean() * 100

print(f"   • % empresas sin siniestros             : {pct_sin_siniestros:.1f}%")
print(f"   • Mediana costo por siniestro (COP)      : {median_costo:,.0f}")
print(f"   • P90 costo por siniestro (COP)          : {p90_costo:,.0f}")
print(f"   • Top 10% empresas concentran            : {top10_share:.1f}% del costo")
print(f"   • Mediana días incapacidad               : {median_dias:.0f} días")
print(f"   • P90 días incapacidad                   : {p90_dias:.0f} días")
print(f"   • Asimetría días incapacidad             : {skew_dias:.2f}")
print(f"   • % empresas micro (≤10 trab.)           : {pct_micro:.1f}%")
print(f"   • % empresas PyME (11-200 trab.)         : {pct_pyme:.1f}%")
print(f"   • Gini costos empresa                    : {gini_approx:.3f}")

print(f"\n✅  Análisis univariado completado. Figuras en:\n   {RESULTS_IMGS}")
