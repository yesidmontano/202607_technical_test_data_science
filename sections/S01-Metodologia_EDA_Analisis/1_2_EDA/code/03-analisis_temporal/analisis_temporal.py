"""
Análisis Temporal y de Estacionalidad
=====================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.2 – EDA

Descripción:
    Explora la estructura temporal del portafolio de siniestros (2018–2024)
    y la estacionalidad intra-anual:
    · Series anuales y mensuales (volumen, costo, severidad)
    · Variación interanual (YoY) y media móvil
    · Composición AT/EL en el tiempo
    · Perfil estacional (índice por mes) y heatmap año × mes
    · Persistencia empresa-año (relevancia para validación temporal)

    Adicionalmente:
    · Construye datasets de staging reutilizables.
    · Guarda figuras en results/imgs/ con prefijo 03_*.
    · Imprime estadísticas descriptivas para Insights_EDA.md.

Inputs:
    - data/staging/S01/siniestros_staging.parquet
    - data/staging/S01/empresas_staging.parquet

Outputs:
    - data/staging/S01/temporal_mensual.parquet
    - data/staging/S01/temporal_anual.parquet
    - data/staging/S01/estacionalidad_mes.parquet
    - data/staging/S01/temporal_empresa_anio.parquet
    - sections/S01-.../results/imgs/03_*.png

Uso:
    .venv/bin/python sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/03-analisis_temporal/analisis_temporal.py
"""

# ──────────────────────────────────────────────────────────────────────────────
#  Imports
# ──────────────────────────────────────────────────────────────────────────────
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
#  Global config
# ──────────────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
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

sb.apply_sura_style()

MES_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
              "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, name: str) -> None:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _fmt_millones(x, _):
    return f"${x / 1e6:.0f}M"


def _fmt_miles_millones(x, _):
    return f"${x / 1e9:.1f}B"


# ──────────────────────────────────────────────────────────────────────────────
#  1. Load staging
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Loading staging datasets...")

siniestros = pd.read_parquet(DATA_STAGING / "siniestros_staging.parquet")
empresas = pd.read_parquet(DATA_STAGING / "empresas_staging.parquet")

siniestros["fecha_ocurrencia"] = pd.to_datetime(siniestros["fecha_ocurrencia"])
siniestros["anio_mes"] = siniestros["fecha_ocurrencia"].dt.to_period("M").astype(str)
siniestros["trimestre"] = siniestros["fecha_ocurrencia"].dt.quarter

print(f"   siniestros : {siniestros.shape}")
print(f"   empresas   : {empresas.shape}")
print(
    f"   periodo    : {siniestros['fecha_ocurrencia'].min().date()} → "
    f"{siniestros['fecha_ocurrencia'].max().date()}"
)

# ──────────────────────────────────────────────────────────────────────────────
#  2. Build temporal aggregates (staging)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔧  Building temporal aggregates...")

# --- Monthly (year × month) ------------------------------------------------
temporal_mensual = (
    siniestros.groupby(["anio", "mes", "anio_mes"], observed=True)
    .agg(
        n_siniestros=("id_siniestro", "count"),
        n_empresas=("id_empresa", "nunique"),
        costo_total=("costo_total", "sum"),
        costo_medio=("costo_total", "mean"),
        severidad_media=("dias_incapacidad", "mean"),
        severidad_mediana=("dias_incapacidad", "median"),
        n_at=("tipo", lambda s: (s == "AT").sum()),
        n_el=("tipo", lambda s: (s == "EL").sum()),
    )
    .reset_index()
    .sort_values(["anio", "mes"])
)
temporal_mensual["pct_at"] = (
    temporal_mensual["n_at"] / temporal_mensual["n_siniestros"] * 100
)
temporal_mensual["pct_el"] = (
    temporal_mensual["n_el"] / temporal_mensual["n_siniestros"] * 100
)
temporal_mensual["ma3_n_siniestros"] = (
    temporal_mensual["n_siniestros"].rolling(3, min_periods=1).mean()
)
temporal_mensual["ma3_costo_total"] = (
    temporal_mensual["costo_total"].rolling(3, min_periods=1).mean()
)

# --- Annual ----------------------------------------------------------------
temporal_anual = (
    siniestros.groupby("anio", observed=True)
    .agg(
        n_siniestros=("id_siniestro", "count"),
        n_empresas=("id_empresa", "nunique"),
        costo_total=("costo_total", "sum"),
        costo_medio=("costo_total", "mean"),
        severidad_media=("dias_incapacidad", "mean"),
        severidad_mediana=("dias_incapacidad", "median"),
        n_at=("tipo", lambda s: (s == "AT").sum()),
        n_el=("tipo", lambda s: (s == "EL").sum()),
    )
    .reset_index()
    .sort_values("anio")
)
temporal_anual["pct_at"] = temporal_anual["n_at"] / temporal_anual["n_siniestros"] * 100
temporal_anual["pct_el"] = temporal_anual["n_el"] / temporal_anual["n_siniestros"] * 100
temporal_anual["yoy_n_siniestros_pct"] = temporal_anual["n_siniestros"].pct_change() * 100
temporal_anual["yoy_costo_total_pct"] = temporal_anual["costo_total"].pct_change() * 100
temporal_anual["costo_por_siniestro"] = (
    temporal_anual["costo_total"] / temporal_anual["n_siniestros"]
)

# --- Seasonal profile (average across years) -------------------------------
overall_mean_n = temporal_mensual["n_siniestros"].mean()
overall_mean_cost = temporal_mensual["costo_total"].mean()
overall_mean_sev = temporal_mensual["severidad_media"].mean()

estacionalidad_mes = (
    temporal_mensual.groupby("mes", observed=True)
    .agg(
        n_siniestros_media=("n_siniestros", "mean"),
        n_siniestros_std=("n_siniestros", "std"),
        n_siniestros_min=("n_siniestros", "min"),
        n_siniestros_max=("n_siniestros", "max"),
        costo_total_media=("costo_total", "mean"),
        costo_total_std=("costo_total", "std"),
        severidad_media=("severidad_media", "mean"),
        severidad_std=("severidad_media", "std"),
        n_anios=("anio", "nunique"),
    )
    .reset_index()
    .sort_values("mes")
)
estacionalidad_mes["indice_estacional_n"] = (
    estacionalidad_mes["n_siniestros_media"] / overall_mean_n
)
estacionalidad_mes["indice_estacional_costo"] = (
    estacionalidad_mes["costo_total_media"] / overall_mean_cost
)
estacionalidad_mes["indice_estacional_sev"] = (
    estacionalidad_mes["severidad_media"] / overall_mean_sev
)
estacionalidad_mes["mes_label"] = estacionalidad_mes["mes"].map(
    dict(enumerate(MES_LABELS, start=1))
)
estacionalidad_mes["cv_n"] = (
    estacionalidad_mes["n_siniestros_std"] / estacionalidad_mes["n_siniestros_media"]
)

# --- Company × year panel (for temporal CV / persistence) ------------------
print("   Building company-year panel...")
sin_emp_anio = (
    siniestros.groupby(["id_empresa", "anio"], observed=True)
    .agg(
        n_siniestros=("id_siniestro", "count"),
        costo_total=("costo_total", "sum"),
        severidad_media=("dias_incapacidad", "mean"),
        n_at=("tipo", lambda s: (s == "AT").sum()),
        n_el=("tipo", lambda s: (s == "EL").sum()),
    )
    .reset_index()
)

# Full cartesian product of companies × years with zeros
anios = sorted(siniestros["anio"].unique())
emp_ids = empresas["id_empresa"].unique()
full_idx = pd.MultiIndex.from_product(
    [emp_ids, anios], names=["id_empresa", "anio"]
)
temporal_empresa_anio = (
    sin_emp_anio.set_index(["id_empresa", "anio"])
    .reindex(full_idx)
    .fillna({"n_siniestros": 0, "costo_total": 0, "n_at": 0, "n_el": 0})
    .reset_index()
)
temporal_empresa_anio = temporal_empresa_anio.merge(
    empresas[["id_empresa", "n_trabajadores", "clase_riesgo", "sector"]],
    on="id_empresa",
    how="left",
)
temporal_empresa_anio["frecuencia_x100"] = (
    temporal_empresa_anio["n_siniestros"]
    / temporal_empresa_anio["n_trabajadores"].clip(lower=1)
    * 100
)
temporal_empresa_anio["tiene_siniestro"] = (
    temporal_empresa_anio["n_siniestros"] > 0
).astype(int)
temporal_empresa_anio["alta_siniestralidad"] = (
    temporal_empresa_anio.groupby("anio")["n_siniestros"]
    .transform(lambda s: (s > s.mean()).astype(int))
)

# Persistence correlations (company-level n_siniestros year t vs t+1)
piv_n = temporal_empresa_anio.pivot(
    index="id_empresa", columns="anio", values="n_siniestros"
).fillna(0)
persist_rows = []
for y1, y2 in zip(anios[:-1], anios[1:]):
    persist_rows.append({
        "anio_t": y1,
        "anio_t1": y2,
        "corr_n_siniestros": piv_n[y1].corr(piv_n[y2]),
        "corr_frecuencia_x100": (
            temporal_empresa_anio.pivot(
                index="id_empresa", columns="anio", values="frecuencia_x100"
            )
            .fillna(0)[y1]
            .corr(
                temporal_empresa_anio.pivot(
                    index="id_empresa", columns="anio", values="frecuencia_x100"
                ).fillna(0)[y2]
            )
        ),
    })
persistencia = pd.DataFrame(persist_rows)

# Persist staging
temporal_mensual.to_parquet(DATA_STAGING / "temporal_mensual.parquet", index=False)
temporal_anual.to_parquet(DATA_STAGING / "temporal_anual.parquet", index=False)
estacionalidad_mes.to_parquet(DATA_STAGING / "estacionalidad_mes.parquet", index=False)
temporal_empresa_anio.to_parquet(
    DATA_STAGING / "temporal_empresa_anio.parquet", index=False
)
persistencia.to_parquet(DATA_STAGING / "temporal_persistencia_yoy.parquet", index=False)

print(f"   ✅  Staging saved to {DATA_STAGING}")
print(f"      - temporal_mensual.parquet         : {temporal_mensual.shape}")
print(f"      - temporal_anual.parquet           : {temporal_anual.shape}")
print(f"      - estacionalidad_mes.parquet       : {estacionalidad_mes.shape}")
print(f"      - temporal_empresa_anio.parquet    : {temporal_empresa_anio.shape}")
print(f"      - temporal_persistencia_yoy.parquet: {persistencia.shape}")

palette = sb.get_palette("categorical")

# ──────────────────────────────────────────────────────────────────────────────
#  3. BLOCK A – Estructura temporal
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK A – Estructura temporal")

# A1. Monthly volume + 3-month MA
fig, ax = sb.create_report_figure(
    title="Serie Mensual de Siniestros (2018–2024)",
    subtitle="Volumen mensual y media móvil de 3 meses",
    figsize=(14, 6.5),
)
x_labels = temporal_mensual["anio_mes"].tolist()
ax.plot(
    range(len(x_labels)),
    temporal_mensual["n_siniestros"],
    color=palette[0],
    alpha=0.45,
    linewidth=1.2,
    label="Mensual",
)
ax.plot(
    range(len(x_labels)),
    temporal_mensual["ma3_n_siniestros"],
    color=sb.AZUL_SURA.hex,
    linewidth=2.4,
    label="Media móvil 3m",
)
# Year separators
for i, row in temporal_mensual.iterrows():
    if row["mes"] == 1:
        ax.axvline(temporal_mensual.index.get_loc(i), color="#CCCCCC",
                   linewidth=0.8, linestyle="--", alpha=0.7)
tick_pos = list(range(0, len(x_labels), 6))
ax.set_xticks(tick_pos)
ax.set_xticklabels([x_labels[i] for i in tick_pos], rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Número de siniestros")
ax.set_xlabel("Año-mes")
ax.legend(frameon=True, loc="upper right")
ax.set_ylim(bottom=0)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Serie mensual")
_save_fig(fig, "03_A1_serie_mensual_siniestros.png")

# A2. Annual multipanel: volume / cost / severity
fig, axes = sb.create_dashboard(
    1, 3,
    title="Estructura Anual del Portafolio",
    subtitle="Volumen, costo total y severidad media por año",
)
ax1, ax2, ax3 = axes[0], axes[1], axes[2]
years_str = temporal_anual["anio"].astype(str).tolist()

ax1.bar(years_str, temporal_anual["n_siniestros"], color=palette[0], alpha=0.88)
ax1.set_title("Volumen de siniestros")
ax1.set_ylabel("Nº siniestros")
ax1.set_xlabel("Año")
for i, v in enumerate(temporal_anual["n_siniestros"]):
    ax1.text(i, v + 40, f"{v:,}", ha="center", va="bottom", fontsize=8)

ax2.bar(years_str, temporal_anual["costo_total"], color=palette[1], alpha=0.88)
ax2.set_title("Costo total del portafolio")
ax2.set_ylabel("Costo (COP)")
ax2.set_xlabel("Año")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_miles_millones))

ax3.plot(
    years_str, temporal_anual["severidad_media"],
    color=palette[2], marker="o", linewidth=2.2, markersize=6,
)
ax3.set_title("Severidad media")
ax3.set_ylabel("Días de incapacidad")
ax3.set_xlabel("Año")
ax3.set_ylim(bottom=0)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Estructura anual")
_save_fig(fig, "03_A2_estructura_anual.png")

# A3. AT/EL composition over years
fig, ax = sb.create_report_figure(
    title="Composición AT / EL por Año",
    subtitle="Participación relativa de Accidentes de Trabajo vs Enfermedades Laborales",
    figsize=(12, 6),
)
ax.bar(
    years_str, temporal_anual["pct_at"],
    color=palette[0], alpha=0.88, label="AT",
)
ax.bar(
    years_str, temporal_anual["pct_el"],
    bottom=temporal_anual["pct_at"],
    color=palette[2], alpha=0.88, label="EL",
)
ax.set_ylabel("% de siniestros")
ax.set_xlabel("Año")
ax.set_ylim(0, 100)
ax.axhline(90, color="#AAAAAA", linestyle=":", linewidth=0.8)
ax.legend(frameon=True, loc="lower right")
for i, (at, el) in enumerate(
    zip(temporal_anual["pct_at"], temporal_anual["pct_el"])
):
    ax.text(i, at / 2, f"{at:.1f}%", ha="center", va="center",
            fontsize=8, color="white", fontweight="bold")
    ax.text(i, at + el / 2, f"{el:.1f}%", ha="center", va="center",
            fontsize=8, color="white", fontweight="bold")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Mix AT/EL")
_save_fig(fig, "03_A3_composicion_at_el_anual.png")

# ──────────────────────────────────────────────────────────────────────────────
#  4. BLOCK B – Estacionalidad
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK B – Estacionalidad")

# B1. Seasonal index (volume)
fig, ax = sb.create_report_figure(
    title="Índice Estacional Mensual de Volumen",
    subtitle="Media mensual / media global (1.0 = sin estacionalidad)",
    figsize=(12, 6),
)
colors_idx = [
    sb.AQUA_SURA.hex if v >= 1.0 else sb.AZUL_SURA.hex
    for v in estacionalidad_mes["indice_estacional_n"]
]
bars = ax.bar(
    estacionalidad_mes["mes_label"],
    estacionalidad_mes["indice_estacional_n"],
    color=colors_idx, alpha=0.88, edgecolor="white",
)
ax.axhline(1.0, color=sb.AZUL_SURA.hex, linestyle="--", linewidth=1.5, label="Media = 1.0")
ax.set_ylabel("Índice estacional")
ax.set_xlabel("Mes")
ax.set_ylim(0.9, 1.1)
ax.legend(frameon=True, loc="upper right")
for bar, v in zip(bars, estacionalidad_mes["indice_estacional_n"]):
    ax.text(
        bar.get_x() + bar.get_width() / 2, v + 0.003,
        f"{v:.3f}", ha="center", va="bottom", fontsize=8,
    )
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Índice estacional")
_save_fig(fig, "03_B1_indice_estacional_mensual.png")

# B2. Heatmap year × month
fig, ax = sb.create_report_figure(
    title="Heatmap Año × Mes – Volumen de Siniestros",
    subtitle="Intensidad del conteo mensual por año calendario",
    figsize=(12, 6.5),
)
heat = temporal_mensual.pivot(index="anio", columns="mes", values="n_siniestros")
heat = heat.reindex(columns=range(1, 13))
sns.heatmap(
    heat,
    ax=ax,
    cmap=sb.get_cmap("sura_blues"),
    annot=True,
    fmt=".0f",
    linewidths=0.5,
    linecolor="white",
    cbar_kws={"label": "Nº siniestros"},
)
ax.set_xticklabels(MES_LABELS, rotation=0)
ax.set_ylabel("Año")
ax.set_xlabel("Mes")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Heatmap año×mes")
_save_fig(fig, "03_B2_heatmap_anio_mes.png")

# B3. Boxplots of monthly distribution across years
fig, ax = sb.create_report_figure(
    title="Distribución del Volumen Mensual entre Años",
    subtitle="Variabilidad interanual del conteo por mes calendario",
    figsize=(12, 6),
)
bp_data = [
    temporal_mensual.loc[temporal_mensual["mes"] == m, "n_siniestros"].values
    for m in range(1, 13)
]
bp = ax.boxplot(bp_data, tick_labels=MES_LABELS, patch_artist=True, showfliers=True)
for i, box in enumerate(bp["boxes"]):
    box.set_facecolor(palette[i % len(palette)])
    box.set_alpha(0.75)
ax.set_ylabel("Nº siniestros en el mes")
ax.set_xlabel("Mes")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Boxplot estacional")
_save_fig(fig, "03_B3_boxplot_volumen_por_mes.png")

# ──────────────────────────────────────────────────────────────────────────────
#  5. BLOCK C – YoY, estacionalidad de costo/severidad, persistencia
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK C – Variación YoY, costo/severidad y persistencia")

# C1. YoY changes
fig, axes = sb.create_dashboard(
    1, 2,
    title="Variación Interanual (YoY)",
    subtitle="Cambio porcentual año a año en volumen y costo total",
)
ax1, ax2 = axes[0], axes[1]
yoy = temporal_anual.dropna(subset=["yoy_n_siniestros_pct"])
yoy_years = yoy["anio"].astype(str).tolist()

colors_vol = [
    sb.AQUA_SURA.hex if v >= 0 else "#C0392B" for v in yoy["yoy_n_siniestros_pct"]
]
ax1.bar(yoy_years, yoy["yoy_n_siniestros_pct"], color=colors_vol, alpha=0.88)
ax1.axhline(0, color=sb.AZUL_SURA.hex, linewidth=1)
ax1.set_title("YoY volumen de siniestros")
ax1.set_ylabel("% cambio")
ax1.set_xlabel("Año")
for i, v in enumerate(yoy["yoy_n_siniestros_pct"]):
    ax1.text(i, v + (1.5 if v >= 0 else -2.5), f"{v:+.1f}%",
             ha="center", va="bottom" if v >= 0 else "top", fontsize=8)

colors_cost = [
    sb.AQUA_SURA.hex if v >= 0 else "#C0392B" for v in yoy["yoy_costo_total_pct"]
]
ax2.bar(yoy_years, yoy["yoy_costo_total_pct"], color=colors_cost, alpha=0.88)
ax2.axhline(0, color=sb.AZUL_SURA.hex, linewidth=1)
ax2.set_title("YoY costo total")
ax2.set_ylabel("% cambio")
ax2.set_xlabel("Año")
for i, v in enumerate(yoy["yoy_costo_total_pct"]):
    ax2.text(i, v + (1.5 if v >= 0 else -2.5), f"{v:+.1f}%",
             ha="center", va="bottom" if v >= 0 else "top", fontsize=8)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Variación YoY")
_save_fig(fig, "03_C1_variacion_yoy.png")

# C2. Seasonal indices for cost and severity
fig, axes = sb.create_dashboard(
    1, 2,
    title="Estacionalidad de Costo y Severidad",
    subtitle="Índices mensuales relativos a la media global",
)
ax1, ax2 = axes[0], axes[1]

ax1.plot(
    estacionalidad_mes["mes_label"],
    estacionalidad_mes["indice_estacional_costo"],
    color=palette[1], marker="o", linewidth=2.2, markersize=6, label="Costo",
)
ax1.axhline(1.0, color="#AAAAAA", linestyle="--", linewidth=1)
ax1.set_title("Índice estacional – costo")
ax1.set_ylabel("Índice")
ax1.set_xlabel("Mes")
ax1.set_ylim(0.85, 1.15)
ax1.tick_params(axis="x", rotation=45)

ax2.plot(
    estacionalidad_mes["mes_label"],
    estacionalidad_mes["indice_estacional_sev"],
    color=palette[2], marker="o", linewidth=2.2, markersize=6, label="Severidad",
)
ax2.axhline(1.0, color="#AAAAAA", linestyle="--", linewidth=1)
ax2.set_title("Índice estacional – severidad")
ax2.set_ylabel("Índice")
ax2.set_xlabel("Mes")
ax2.set_ylim(0.85, 1.15)
ax2.tick_params(axis="x", rotation=45)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Estacionalidad costo/sev")
_save_fig(fig, "03_C2_estacionalidad_costo_severidad.png")

# C3. Company-year persistence
fig, ax = sb.create_report_figure(
    title="Persistencia Empresa–Año de la Siniestralidad",
    subtitle="Correlación del conteo de siniestros entre años consecutivos (t vs t+1)",
    figsize=(12, 6),
)
pair_labels = [f"{int(r.anio_t)}→{int(r.anio_t1)}" for _, r in persistencia.iterrows()]
ax.bar(
    pair_labels, persistencia["corr_n_siniestros"],
    color=sb.AZUL_SURA.hex, alpha=0.88, label="n_siniestros",
)
ax.plot(
    pair_labels, persistencia["corr_frecuencia_x100"],
    color=sb.AQUA_SURA.hex, marker="D", linewidth=2, markersize=7,
    label="frecuencia_x100",
)
mean_corr = persistencia["corr_n_siniestros"].mean()
ax.axhline(
    mean_corr, color="#C0392B", linestyle="--", linewidth=1.5,
    label=f"Media n = {mean_corr:.2f}",
)
ax.set_ylabel("Correlación de Pearson")
ax.set_xlabel("Par de años")
ax.set_ylim(0, 1)
ax.legend(frameon=True, loc="lower right")
for i, v in enumerate(persistencia["corr_n_siniestros"]):
    ax.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Temporal | Persistencia YoY")
_save_fig(fig, "03_C3_persistencia_empresa_anio.png")

# ──────────────────────────────────────────────────────────────────────────────
#  6. Print key statistics for Insights
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("📈  KEY STATISTICS – Análisis Temporal y Estacionalidad")
print("=" * 72)

print("\n--- Serie anual ---")
print(
    temporal_anual[
        ["anio", "n_siniestros", "costo_total", "severidad_media",
         "pct_at", "yoy_n_siniestros_pct", "yoy_costo_total_pct"]
    ].to_string(index=False)
)

amp_n = (
    estacionalidad_mes["indice_estacional_n"].max()
    - estacionalidad_mes["indice_estacional_n"].min()
)
amp_cost = (
    estacionalidad_mes["indice_estacional_costo"].max()
    - estacionalidad_mes["indice_estacional_costo"].min()
)
amp_sev = (
    estacionalidad_mes["indice_estacional_sev"].max()
    - estacionalidad_mes["indice_estacional_sev"].min()
)
cv_interanual = (
    temporal_mensual.groupby("mes")["n_siniestros"].std()
    / temporal_mensual.groupby("mes")["n_siniestros"].mean()
).mean()

print("\n--- Estacionalidad ---")
print(f"Amplitud índice volumen  : {amp_n:.3f} ({amp_n * 100:.1f} pp)")
print(f"Amplitud índice costo    : {amp_cost:.3f}")
print(f"Amplitud índice severidad: {amp_sev:.3f}")
print(f"CV interanual medio/mes  : {cv_interanual:.3f}")
print(
    f"Mes pico volumen         : "
    f"{estacionalidad_mes.loc[estacionalidad_mes['indice_estacional_n'].idxmax(), 'mes_label']} "
    f"({estacionalidad_mes['indice_estacional_n'].max():.3f})"
)
print(
    f"Mes valle volumen        : "
    f"{estacionalidad_mes.loc[estacionalidad_mes['indice_estacional_n'].idxmin(), 'mes_label']} "
    f"({estacionalidad_mes['indice_estacional_n'].min():.3f})"
)

print("\n--- Persistencia empresa-año ---")
print(persistencia.to_string(index=False))
print(f"Media corr n_siniestros  : {persistencia['corr_n_siniestros'].mean():.3f}")
print(
    f"Media corr frecuencia_x100: "
    f"{persistencia['corr_frecuencia_x100'].mean():.3f}"
)

pct_alta = temporal_empresa_anio.groupby("anio")["alta_siniestralidad"].mean() * 100
print("\n--- % empresas con alta siniestralidad (n > media del año) ---")
print(pct_alta.round(1).to_string())

print("\n✅  Análisis temporal y de estacionalidad completado.")
print(f"   Figuras en: {RESULTS_IMGS}")
print(f"   Staging en: {DATA_STAGING}")
