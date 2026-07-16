"""
Análisis Bivariado – Asociaciones de Siniestralidad
=====================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.2 – EDA

Descripción:
    Explora asociaciones bivariadas entre la siniestralidad (frecuencia,
    severidad y costo) y cuatro dimensiones de estratificación:
    · Clase de riesgo ARL
    · Sector económico
    · Tamaño de la empresa (n_trabajadores / segmento)
    · Geografía (departamento y ciudad)

    Adicionalmente:
    · Construye datasets de staging reutilizables (panel completo + resúmenes).
    · Guarda figuras en results/imgs/ con prefijo 02_*.
    · Imprime estadísticas para Insights_EDA.md.

Inputs:
    - data/staging/S01/empresas_staging.parquet
    - data/staging/S01/siniestralidad_empresa.parquet
    - data/staging/S01/siniestros_staging.parquet

Outputs:
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/staging/S01/bivariado_resumen_*.parquet
    - sections/S01-.../results/imgs/02_*.png

Uso:
    .venv/bin/python sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/02-analisis_bivariado/analisis_bivariado.py
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
import scipy.stats as stats
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

SIZE_BINS = [0, 10, 50, 200, np.inf]
SIZE_LABELS = ["Micro (≤10)", "Pequeña (11-50)", "Mediana (51-200)", "Grande (>200)"]

# ──────────────────────────────────────────────────────────────────────────────
#  1. Load staging
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Loading staging datasets...")

empresas = pd.read_parquet(DATA_STAGING / "empresas_staging.parquet")
sin_empresa = pd.read_parquet(DATA_STAGING / "siniestralidad_empresa.parquet")
siniestros = pd.read_parquet(DATA_STAGING / "siniestros_staging.parquet")

print(f"   empresas            : {empresas.shape}")
print(f"   siniestralidad_emp  : {sin_empresa.shape}")
print(f"   siniestros          : {siniestros.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  2. Build full company panel (include zero-claim firms)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔧  Building full company siniestralidad panel...")

claim_cols = [
    "id_empresa", "n_siniestros", "total_dias_incapacidad",
    "costo_total_empresa", "costo_asistencial_total", "costo_prestacion_total",
    "costo_medio_siniestro", "severidad_media", "frecuencia_x100",
    "log_frecuencia_x100", "anio_primero", "anio_ultimo",
]

panel = empresas.merge(sin_empresa[claim_cols], on="id_empresa", how="left")

zero_fill = [
    "n_siniestros", "total_dias_incapacidad", "costo_total_empresa",
    "costo_asistencial_total", "costo_prestacion_total", "frecuencia_x100",
]
for col in zero_fill:
    panel[col] = panel[col].fillna(0)

panel["log_frecuencia_x100"] = np.log1p(panel["frecuencia_x100"])
panel["log_costo_total_empresa"] = np.log1p(panel["costo_total_empresa"])
panel["log_n_siniestros"] = np.log1p(panel["n_siniestros"])
panel["tiene_siniestro"] = (panel["n_siniestros"] > 0).astype(int)
panel["segmento"] = pd.cut(
    panel["n_trabajadores"], bins=SIZE_BINS, labels=SIZE_LABELS
)
panel["clase_riesgo"] = panel["clase_riesgo"].astype("category")
panel["sector"] = panel["sector"].astype("category")

# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, name: str) -> None:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"   💾  {name}")


def _fmt_millones(x, _):
    return f"${x / 1e6:.1f}M"


def _group_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Aggregate siniestralidad metrics by a stratification variable."""
    agg = (
        df.groupby(group_col, observed=True)
        .agg(
            n_empresas=("id_empresa", "count"),
            pct_con_siniestro=("tiene_siniestro", "mean"),
            n_siniestros_mediana=("n_siniestros", "median"),
            n_siniestros_media=("n_siniestros", "mean"),
            frecuencia_x100_mediana=("frecuencia_x100", "median"),
            frecuencia_x100_media=("frecuencia_x100", "mean"),
            costo_total_mediana=("costo_total_empresa", "median"),
            costo_total_media=("costo_total_empresa", "mean"),
            costo_total_suma=("costo_total_empresa", "sum"),
            severidad_mediana=("severidad_media", "median"),
            severidad_media=("severidad_media", "mean"),
            n_trabajadores_mediana=("n_trabajadores", "median"),
            prima_anual_mediana=("prima_anual", "median"),
        )
        .reset_index()
    )
    agg["pct_con_siniestro"] = agg["pct_con_siniestro"] * 100
    agg["share_costo_pct"] = agg["costo_total_suma"] / agg["costo_total_suma"].sum() * 100
    return agg


def _kruskal(df: pd.DataFrame, group_col: str, value_col: str) -> tuple:
    groups = [
        g[value_col].dropna().values
        for _, g in df.groupby(group_col, observed=True)
        if len(g[value_col].dropna()) > 0
    ]
    if len(groups) < 2:
        return np.nan, np.nan
    result = stats.kruskal(*groups)
    return float(result.statistic), float(result.pvalue)


def _spearman(x, y) -> tuple:
    r, p = stats.spearmanr(x, y, nan_policy="omit")
    return float(r), float(p)


def _annotate_stat(ax, text: str, x: float = 0.03, y: float = 0.97) -> None:
    ax.text(
        x, y, text,
        transform=ax.transAxes, fontsize=8,
        verticalalignment="top", horizontalalignment="left",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                  edgecolor="#C7C9C7", alpha=0.9),
    )


palette = sb.get_palette("categorical")

# ──────────────────────────────────────────────────────────────────────────────
#  3. Staging summaries
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔧  Computing bivariate summary tables...")

resumen_clase = _group_summary(panel, "clase_riesgo")
resumen_sector = _group_summary(panel, "sector")
resumen_segmento = _group_summary(panel, "segmento")
resumen_depto = _group_summary(panel, "departamento")
resumen_ciudad = _group_summary(panel, "ciudad")

# Association tests table
tests = []
for dim, col in [
    ("clase_riesgo", "clase_riesgo"),
    ("sector", "sector"),
    ("segmento", "segmento"),
    ("departamento", "departamento"),
    ("ciudad", "ciudad"),
]:
    for metric in ["frecuencia_x100", "n_siniestros", "costo_total_empresa"]:
        h, p = _kruskal(panel, col, metric)
        tests.append({
            "dimension": dim,
            "metric": metric,
            "test": "Kruskal-Wallis",
            "statistic": h,
            "pvalue": p,
        })

# Spearman for ordinal / continuous predictors
for x_col, y_col, label in [
    ("clase_riesgo", "frecuencia_x100", "clase_riesgo ~ frecuencia_x100"),
    ("clase_riesgo", "n_siniestros", "clase_riesgo ~ n_siniestros"),
    ("clase_riesgo", "costo_total_empresa", "clase_riesgo ~ costo_total"),
    ("n_trabajadores", "n_siniestros", "n_trabajadores ~ n_siniestros"),
    ("n_trabajadores", "frecuencia_x100", "n_trabajadores ~ frecuencia_x100"),
    ("n_trabajadores", "costo_total_empresa", "n_trabajadores ~ costo_total"),
    ("prima_anual", "costo_total_empresa", "prima_anual ~ costo_total"),
    ("prima_anual", "frecuencia_x100", "prima_anual ~ frecuencia_x100"),
]:
    x = panel[x_col].astype(float) if x_col == "clase_riesgo" else panel[x_col]
    r, p = _spearman(x, panel[y_col])
    tests.append({
        "dimension": label,
        "metric": y_col,
        "test": "Spearman",
        "statistic": r,
        "pvalue": p,
    })

tests_df = pd.DataFrame(tests)

# Persist staging
panel.to_parquet(DATA_STAGING / "empresa_siniestralidad_completa.parquet", index=False)
resumen_clase.to_parquet(DATA_STAGING / "bivariado_resumen_clase_riesgo.parquet", index=False)
resumen_sector.to_parquet(DATA_STAGING / "bivariado_resumen_sector.parquet", index=False)
resumen_segmento.to_parquet(DATA_STAGING / "bivariado_resumen_segmento.parquet", index=False)
resumen_depto.to_parquet(DATA_STAGING / "bivariado_resumen_departamento.parquet", index=False)
resumen_ciudad.to_parquet(DATA_STAGING / "bivariado_resumen_ciudad.parquet", index=False)
tests_df.to_parquet(DATA_STAGING / "bivariado_tests_asociacion.parquet", index=False)

print(f"   ✅  Staging saved to {DATA_STAGING}")
print(f"      - empresa_siniestralidad_completa.parquet : {panel.shape}")
print(f"      - bivariado_resumen_clase_riesgo.parquet  : {resumen_clase.shape}")
print(f"      - bivariado_resumen_sector.parquet        : {resumen_sector.shape}")
print(f"      - bivariado_resumen_segmento.parquet      : {resumen_segmento.shape}")
print(f"      - bivariado_resumen_departamento.parquet  : {resumen_depto.shape}")
print(f"      - bivariado_resumen_ciudad.parquet        : {resumen_ciudad.shape}")
print(f"      - bivariado_tests_asociacion.parquet      : {tests_df.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  4. BLOCK A – Clase de riesgo
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK A – Clase de riesgo")

# A1. Boxplots: frecuencia / costo / severidad by risk class
fig, axes = sb.create_dashboard(
    1, 3,
    title="Siniestralidad por Clase de Riesgo ARL",
    subtitle="Frecuencia relativa, costo acumulado y severidad media",
)
ax1, ax2, ax3 = axes[0], axes[1], axes[2]

orden_clase = sorted(panel["clase_riesgo"].dropna().unique(), key=lambda x: int(x))
plot_df = panel.copy()
plot_df["clase_riesgo"] = pd.Categorical(
    plot_df["clase_riesgo"].astype(str),
    categories=[str(c) for c in orden_clase],
    ordered=True,
)

# Cap for readability
freq_cap = plot_df["frecuencia_x100"].quantile(0.99)
cost_cap = plot_df["costo_total_empresa"].quantile(0.97)

bp_data_freq = [
    plot_df.loc[plot_df["clase_riesgo"] == str(c), "frecuencia_x100"].clip(upper=freq_cap)
    for c in orden_clase
]
bp1 = ax1.boxplot(
    bp_data_freq, tick_labels=[str(c) for c in orden_clase],
    patch_artist=True, showfliers=False,
)
for i, box in enumerate(bp1["boxes"]):
    box.set_facecolor(palette[i % len(palette)])
    box.set_alpha(0.75)
ax1.set_xlabel("Clase de riesgo")
ax1.set_ylabel("Siniestros / 100 trabajadores")
ax1.set_title("Frecuencia relativa")

bp_data_cost = [
    plot_df.loc[plot_df["clase_riesgo"] == str(c), "costo_total_empresa"].clip(upper=cost_cap)
    for c in orden_clase
]
bp2 = ax2.boxplot(
    bp_data_cost, tick_labels=[str(c) for c in orden_clase],
    patch_artist=True, showfliers=False,
)
for i, box in enumerate(bp2["boxes"]):
    box.set_facecolor(palette[i % len(palette)])
    box.set_alpha(0.75)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax2.set_xlabel("Clase de riesgo")
ax2.set_ylabel("Costo acumulado (COP)")
ax2.set_title("Costo total empresa")

sev = plot_df.dropna(subset=["severidad_media"])
sev_cap = sev["severidad_media"].quantile(0.97)
bp_data_sev = [
    sev.loc[sev["clase_riesgo"] == str(c), "severidad_media"].clip(upper=sev_cap)
    for c in orden_clase
]
bp3 = ax3.boxplot(
    bp_data_sev, tick_labels=[str(c) for c in orden_clase],
    patch_artist=True, showfliers=False,
)
for i, box in enumerate(bp3["boxes"]):
    box.set_facecolor(palette[i % len(palette)])
    box.set_alpha(0.75)
ax3.set_xlabel("Clase de riesgo")
ax3.set_ylabel("Días de incapacidad (media)")
ax3.set_title("Severidad media")

r_freq, p_freq = _spearman(panel["clase_riesgo"].astype(float), panel["frecuencia_x100"])
_annotate_stat(ax1, f"Spearman ρ = {r_freq:.3f}\np < 0.001")

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Clase de riesgo")
_save_fig(fig, "02_A1_siniestralidad_por_clase_riesgo.png")

# A2. Median bars – clear monotonic gradient
fig, axes = sb.create_dashboard(
    1, 2,
    title="Gradiente Monotónico – Clase de Riesgo",
    subtitle="Medianas de frecuencia relativa y costo acumulado por clase ARL",
)
ax_l, ax_r = axes[0], axes[1]

rc = resumen_clase.sort_values("clase_riesgo")
x_labels = [str(int(c)) for c in rc["clase_riesgo"]]
colors_grad = sb.make_n_colors(len(rc))

bars_l = ax_l.bar(x_labels, rc["frecuencia_x100_mediana"], color=colors_grad, edgecolor="white")
ax_l.bar_label(bars_l, fmt="%.1f", padding=3, fontsize=8)
ax_l.set_xlabel("Clase de riesgo")
ax_l.set_ylabel("Mediana frecuencia ×100")
ax_l.set_title("Frecuencia relativa (mediana)")

bars_r = ax_r.bar(x_labels, rc["costo_total_mediana"], color=colors_grad, edgecolor="white")
ax_r.bar_label(
    bars_r,
    labels=[f"${v/1e6:.1f}M" for v in rc["costo_total_mediana"]],
    padding=3, fontsize=7,
)
ax_r.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax_r.set_xlabel("Clase de riesgo")
ax_r.set_ylabel("Mediana costo acumulado (COP)")
ax_r.set_title("Costo acumulado (mediana)")

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Gradiente clase riesgo")
_save_fig(fig, "02_A2_gradiente_mediana_clase_riesgo.png")

# A3. Share of portfolio cost by risk class
fig, ax = sb.create_report_figure(
    title="Participación del Costo del Portafolio por Clase de Riesgo",
    subtitle="% del costo total acumulado aportado por cada clase ARL",
)
ax = fig.axes[0]
bars = ax.bar(
    x_labels, rc["share_costo_pct"],
    color=colors_grad, edgecolor="white",
)
ax.bar_label(bars, labels=[f"{v:.1f}%" for v in rc["share_costo_pct"]], padding=3, fontsize=9)
ax.set_xlabel("Clase de riesgo")
ax.set_ylabel("% del costo total del portafolio")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Share costo clase")
_save_fig(fig, "02_A3_share_costo_clase_riesgo.png")

# ──────────────────────────────────────────────────────────────────────────────
#  5. BLOCK B – Sector
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK B – Sector económico")

# B1. Horizontal bar – median frequency by sector
rs = resumen_sector.sort_values("frecuencia_x100_mediana", ascending=True)
fig, ax = sb.bar_chart(
    x=rs["sector"].astype(str).tolist(),
    y=rs["frecuencia_x100_mediana"].tolist(),
    title="Frecuencia Relativa Mediana por Sector",
    horizontal=True,
    figsize=(11, 8),
)
ax.set_xlabel("Siniestros por 100 trabajadores (mediana)")
ax.set_ylabel("Sector económico")
h_sec, p_sec = _kruskal(panel, "sector", "frecuencia_x100")
_annotate_stat(ax, f"Kruskal-Wallis H = {h_sec:.0f}\np < 0.001", x=0.55, y=0.15)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Sector – frecuencia")
_save_fig(fig, "02_B1_frecuencia_por_sector.png")

# B2. Horizontal bar – median cost by sector
rs_cost = resumen_sector.sort_values("costo_total_mediana", ascending=True)
fig, ax = sb.bar_chart(
    x=rs_cost["sector"].astype(str).tolist(),
    y=(rs_cost["costo_total_mediana"] / 1e6).tolist(),
    title="Costo Acumulado Mediano por Sector (millones COP)",
    horizontal=True,
    figsize=(11, 8),
)
ax.set_xlabel("Costo acumulado mediano (millones COP)")
ax.set_ylabel("Sector económico")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Sector – costo")
_save_fig(fig, "02_B2_costo_por_sector.png")

# B3. Heatmap-like matrix: sector × risk class (median frequency)
cross = (
    panel.groupby(["sector", "clase_riesgo"], observed=True)["frecuencia_x100"]
    .median()
    .unstack("clase_riesgo")
)
# Order sectors by overall median frequency
sector_order = (
    panel.groupby("sector", observed=True)["frecuencia_x100"]
    .median()
    .sort_values(ascending=False)
    .index
)
cross = cross.reindex(sector_order)
cross.columns = [str(int(c)) for c in cross.columns]

fig, ax = sb.create_report_figure(
    title="Frecuencia Relativa Mediana – Sector × Clase de Riesgo",
    subtitle="Interacción entre sector económico y clase ARL",
    figsize=(12, 9),
)
ax = fig.axes[0]
im = ax.imshow(cross.values, aspect="auto", cmap=sb.get_cmap("sura_blues"))
ax.set_xticks(range(len(cross.columns)))
ax.set_xticklabels(cross.columns)
ax.set_yticks(range(len(cross.index)))
ax.set_yticklabels(cross.index.astype(str), fontsize=9)
ax.set_xlabel("Clase de riesgo")
ax.set_ylabel("Sector")
for i in range(cross.shape[0]):
    for j in range(cross.shape[1]):
        val = cross.values[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if val > np.nanmedian(cross.values) else "#001E60")
cbar = fig.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label("Frecuencia ×100 (mediana)", fontsize=9)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Sector × clase")
_save_fig(fig, "02_B3_heatmap_sector_clase_riesgo.png")

# ──────────────────────────────────────────────────────────────────────────────
#  6. BLOCK C – Company size
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK C – Tamaño de empresa")

# C1. Scatter: n_trabajadores vs n_siniestros (log-log), hue by risk class
fig, axes = sb.create_dashboard(
    1, 2,
    title="Tamaño vs Siniestralidad Absoluta y Relativa",
    subtitle="Exposición (n_trabajadores) frente a conteo y tasa de siniestros",
)
ax_l, ax_r = axes[0], axes[1]

sample = panel.sample(n=min(2500, len(panel)), random_state=RANDOM_SEED)
for i, cr in enumerate(orden_clase):
    mask = sample["clase_riesgo"].astype(int) == int(cr)
    ax_l.scatter(
        sample.loc[mask, "n_trabajadores"].clip(lower=1),
        sample.loc[mask, "n_siniestros"] + 0.5,
        s=12, alpha=0.45, label=f"Clase {cr}",
        color=palette[i % len(palette)],
    )
ax_l.set_xscale("log")
ax_l.set_yscale("log")
ax_l.set_xlabel("N° trabajadores (log)")
ax_l.set_ylabel("N° siniestros + 0.5 (log)")
ax_l.set_title("Conteo absoluto")
ax_l.legend(fontsize=7, loc="upper left")
r_abs, _ = _spearman(panel["n_trabajadores"], panel["n_siniestros"])
_annotate_stat(ax_l, f"Spearman ρ = {r_abs:.3f}", x=0.55, y=0.12)

for i, cr in enumerate(orden_clase):
    mask = sample["clase_riesgo"].astype(int) == int(cr)
    ax_r.scatter(
        sample.loc[mask, "n_trabajadores"].clip(lower=1),
        sample.loc[mask, "frecuencia_x100"].clip(upper=freq_cap),
        s=12, alpha=0.45, label=f"Clase {cr}",
        color=palette[i % len(palette)],
    )
ax_r.set_xscale("log")
ax_r.set_xlabel("N° trabajadores (log)")
ax_r.set_ylabel("Siniestros / 100 trabajadores")
ax_r.set_title("Tasa relativa")
ax_r.legend(fontsize=7, loc="upper right")
r_rel, _ = _spearman(panel["n_trabajadores"], panel["frecuencia_x100"])
_annotate_stat(ax_r, f"Spearman ρ = {r_rel:.3f}", x=0.55, y=0.92)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Tamaño vs siniestralidad")
_save_fig(fig, "02_C1_scatter_tamano_siniestralidad.png")

# C2. Boxplots by size segment
fig, axes = sb.create_dashboard(
    1, 2,
    title="Siniestralidad por Segmento de Tamaño",
    subtitle="Comparación de frecuencia relativa y costo entre micro, PyME y grande",
)
ax_l, ax_r = axes[0], axes[1]

seg_order = [s for s in SIZE_LABELS if s in panel["segmento"].cat.categories]
bp_freq_seg = [
    panel.loc[panel["segmento"] == s, "frecuencia_x100"].clip(upper=freq_cap)
    for s in seg_order
]
bp_c = ax_l.boxplot(bp_freq_seg, tick_labels=seg_order, patch_artist=True, showfliers=False)
for i, box in enumerate(bp_c["boxes"]):
    box.set_facecolor(palette[i % len(palette)])
    box.set_alpha(0.75)
ax_l.set_ylabel("Siniestros / 100 trabajadores")
ax_l.set_title("Frecuencia relativa")
ax_l.tick_params(axis="x", labelrotation=15)

bp_cost_seg = [
    panel.loc[panel["segmento"] == s, "costo_total_empresa"].clip(upper=cost_cap)
    for s in seg_order
]
bp_d = ax_r.boxplot(bp_cost_seg, tick_labels=seg_order, patch_artist=True, showfliers=False)
for i, box in enumerate(bp_d["boxes"]):
    box.set_facecolor(palette[i % len(palette)])
    box.set_alpha(0.75)
ax_r.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax_r.set_ylabel("Costo acumulado (COP)")
ax_r.set_title("Costo total empresa")
ax_r.tick_params(axis="x", labelrotation=15)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Segmento de tamaño")
_save_fig(fig, "02_C2_boxplot_segmento_tamano.png")

# C3. Prima vs costo (exposure / pricing proxy)
fig, ax = sb.create_report_figure(
    title="Prima Anual vs Costo Acumulado de Siniestros",
    subtitle="¿La prima refleja la carga de siniestralidad observada?",
)
ax = fig.axes[0]
for i, cr in enumerate(orden_clase):
    mask = sample["clase_riesgo"].astype(int) == int(cr)
    ax.scatter(
        sample.loc[mask, "prima_anual"].clip(lower=1),
        sample.loc[mask, "costo_total_empresa"].clip(lower=1),
        s=14, alpha=0.4, label=f"Clase {cr}",
        color=palette[i % len(palette)],
    )
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Prima anual (COP, log)")
ax.set_ylabel("Costo acumulado siniestros (COP, log)")
ax.legend(fontsize=8)
r_prima, _ = _spearman(panel["prima_anual"], panel["costo_total_empresa"])
_annotate_stat(ax, f"Spearman ρ = {r_prima:.3f}")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Prima vs costo")
_save_fig(fig, "02_C3_scatter_prima_vs_costo.png")

# ──────────────────────────────────────────────────────────────────────────────
#  7. BLOCK D – Geography
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK D – Geografía")

# D1. Frequency and cost by department
rd = resumen_depto.sort_values("frecuencia_x100_mediana", ascending=True)
fig, axes = sb.create_dashboard(
    1, 2,
    title="Siniestralidad por Departamento",
    subtitle="Medianas de frecuencia relativa y costo acumulado",
)
ax_l, ax_r = axes[0], axes[1]

y_pos = np.arange(len(rd))
ax_l.barh(
    y_pos, rd["frecuencia_x100_mediana"],
    color=sb.AZUL_SURA.hex, edgecolor="white", alpha=0.88,
)
ax_l.set_yticks(y_pos)
ax_l.set_yticklabels(rd["departamento"].tolist())
ax_l.set_xlabel("Frecuencia ×100 (mediana)")
ax_l.set_title("Frecuencia relativa")

rd_cost = resumen_depto.sort_values("costo_total_mediana", ascending=True)
y_pos2 = np.arange(len(rd_cost))
ax_r.barh(
    y_pos2, rd_cost["costo_total_mediana"],
    color=sb.AQUA_SURA.hex, edgecolor="white", alpha=0.88,
)
ax_r.set_yticks(y_pos2)
ax_r.set_yticklabels(rd_cost["departamento"].tolist())
ax_r.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax_r.set_xlabel("Costo acumulado (mediana, COP)")
ax_r.set_title("Costo total empresa")

h_dep, p_dep = _kruskal(panel, "departamento", "frecuencia_x100")
_annotate_stat(ax_l, f"KW H = {h_dep:.1f}\np = {p_dep:.3f}", x=0.55, y=0.15)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Departamento")
_save_fig(fig, "02_D1_siniestralidad_por_departamento.png")

# D2. City comparison
rci = resumen_ciudad.sort_values("frecuencia_x100_mediana", ascending=True)
fig, axes = sb.create_dashboard(
    1, 2,
    title="Siniestralidad por Ciudad",
    subtitle="Medianas de frecuencia relativa y costo acumulado",
)
ax_l, ax_r = axes[0], axes[1]

y_pos = np.arange(len(rci))
ax_l.barh(
    y_pos, rci["frecuencia_x100_mediana"],
    color=sb.AZUL_PROFUNDO.hex, edgecolor="white", alpha=0.88,
)
ax_l.set_yticks(y_pos)
ax_l.set_yticklabels(rci["ciudad"].tolist())
ax_l.set_xlabel("Frecuencia ×100 (mediana)")
ax_l.set_title("Frecuencia relativa")

rci_cost = resumen_ciudad.sort_values("costo_total_mediana", ascending=True)
y_pos2 = np.arange(len(rci_cost))
ax_r.barh(
    y_pos2, rci_cost["costo_total_mediana"],
    color=sb.AQUA_ALTERNO.hex, edgecolor="white", alpha=0.88,
)
ax_r.set_yticks(y_pos2)
ax_r.set_yticklabels(rci_cost["ciudad"].tolist())
ax_r.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax_r.set_xlabel("Costo acumulado (mediana, COP)")
ax_r.set_title("Costo total empresa")

h_ciu, p_ciu = _kruskal(panel, "ciudad", "frecuencia_x100")
_annotate_stat(ax_l, f"KW H = {h_ciu:.1f}\np = {p_ciu:.3f}", x=0.55, y=0.15)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Ciudad")
_save_fig(fig, "02_D2_siniestralidad_por_ciudad.png")

# D3. Composition: risk-class mix by department (stacked %)
comp = (
    panel.groupby(["departamento", "clase_riesgo"], observed=True)
    .size()
    .unstack("clase_riesgo", fill_value=0)
)
comp_pct = comp.div(comp.sum(axis=1), axis=0) * 100
comp_pct = comp_pct.reindex(
    resumen_depto.sort_values("n_empresas", ascending=False)["departamento"]
)

fig, ax = sb.create_report_figure(
    title="Composición de Clases de Riesgo por Departamento",
    subtitle="¿Las diferencias geográficas reflejan mix de riesgo o efecto territorial?",
    figsize=(11, 6),
)
ax = fig.axes[0]
bottom = np.zeros(len(comp_pct))
x = np.arange(len(comp_pct))
for i, col in enumerate(comp_pct.columns):
    vals = comp_pct[col].values
    ax.bar(
        x, vals, bottom=bottom, label=f"Clase {int(col)}",
        color=palette[i % len(palette)], edgecolor="white", width=0.7,
    )
    bottom += vals
ax.set_xticks(x)
ax.set_xticklabels(comp_pct.index.tolist(), rotation=20, ha="right")
ax.set_ylabel("% de empresas")
ax.set_ylim(0, 100)
ax.legend(fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.12))
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Mix geográfico de riesgo")
_save_fig(fig, "02_D3_composicion_clase_por_departamento.png")

# ──────────────────────────────────────────────────────────────────────────────
#  8. BLOCK E – Cross-cut summary (numeric predictors correlation)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK E – Correlaciones numéricas clave")

corr_cols = [
    "clase_riesgo", "n_trabajadores", "prima_anual", "antiguedad_meses",
    "n_siniestros", "frecuencia_x100", "costo_total_empresa",
]
corr_df = panel[corr_cols].copy()
corr_df["clase_riesgo"] = corr_df["clase_riesgo"].astype(float)

# Use Spearman for skewed insurance metrics
spearman_corr = corr_df.corr(method="spearman")
fig, ax = sb.correlation_heatmap(
    spearman_corr,
    title="Correlación de Spearman – Predictores y Siniestralidad",
    figsize=(10, 8),
)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Análisis Bivariado | Matriz Spearman")
_save_fig(fig, "02_E1_heatmap_spearman_predictores.png")

# ──────────────────────────────────────────────────────────────────────────────
#  9. Print key stats for insights
# ──────────────────────────────────────────────────────────────────────────────
print("\n📈  Key bivariate statistics:")

print("\n--- Clase de riesgo (medianas) ---")
print(
    resumen_clase[
        ["clase_riesgo", "n_empresas", "frecuencia_x100_mediana",
         "costo_total_mediana", "severidad_mediana", "share_costo_pct"]
    ].to_string(index=False)
)

print(f"\n   Spearman clase~frecuencia : ρ = {r_freq:.3f}")
print(f"   Spearman clase~costo      : ρ = {_spearman(panel['clase_riesgo'].astype(float), panel['costo_total_empresa'])[0]:.3f}")
print(f"   Spearman clase~n_sin      : ρ = {_spearman(panel['clase_riesgo'].astype(float), panel['n_siniestros'])[0]:.3f}")

print("\n--- Top / bottom sectores por frecuencia mediana ---")
rs_sorted = resumen_sector.sort_values("frecuencia_x100_mediana", ascending=False)
print("   TOP 5:")
for _, row in rs_sorted.head(5).iterrows():
    print(f"      {row['sector']:<28} freq_med={row['frecuencia_x100_mediana']:.1f}")
print("   BOTTOM 5:")
for _, row in rs_sorted.tail(5).iterrows():
    print(f"      {row['sector']:<28} freq_med={row['frecuencia_x100_mediana']:.1f}")
print(f"   Kruskal-Wallis sector~freq : H = {h_sec:.1f}, p = {p_sec:.2e}")

print("\n--- Segmento de tamaño (medianas) ---")
print(
    resumen_segmento[
        ["segmento", "n_empresas", "frecuencia_x100_mediana",
         "n_siniestros_mediana", "costo_total_mediana"]
    ].to_string(index=False)
)
print(f"   Spearman n_trab~n_sin     : ρ = {r_abs:.3f}")
print(f"   Spearman n_trab~freq      : ρ = {r_rel:.3f}")
print(f"   Spearman prima~costo      : ρ = {r_prima:.3f}")

print("\n--- Geografía ---")
print(f"   Kruskal-Wallis depto~freq : H = {h_dep:.1f}, p = {p_dep:.4f}")
print(f"   Kruskal-Wallis ciudad~freq: H = {h_ciu:.1f}, p = {p_ciu:.4f}")
freq_range_depto = (
    resumen_depto["frecuencia_x100_mediana"].max()
    - resumen_depto["frecuencia_x100_mediana"].min()
)
print(f"   Rango medianas depto      : {freq_range_depto:.2f} pts de frecuencia×100")

ratio_c5_c1 = (
    resumen_clase.loc[resumen_clase["clase_riesgo"].astype(int) == 5, "frecuencia_x100_mediana"].iloc[0]
    / resumen_clase.loc[resumen_clase["clase_riesgo"].astype(int) == 1, "frecuencia_x100_mediana"].iloc[0]
)
print(f"\n   Ratio frecuencia Clase5/Clase1 (medianas): {ratio_c5_c1:.1f}×")

print(f"\n✅  Bivariate analysis complete. Figures in:\n   {RESULTS_IMGS}")
