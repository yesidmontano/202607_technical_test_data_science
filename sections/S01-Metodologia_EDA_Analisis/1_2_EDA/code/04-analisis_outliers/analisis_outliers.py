"""
Análisis de Detección y Tratamiento de Valores Atípicos
=======================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.2 – EDA

Descripción:
    Detecta valores atípicos en variables clave de siniestros y empresas
    con tres métodos (IQR, MAD / z-modificado, percentiles P1–P99) y aplica
    tratamiento por winsorización (sin eliminar filas: en ARL los extremos
    son eventos reales de cola).

    Adicionalmente:
    · Construye datasets de staging reutilizables (flags + tratados).
    · Guarda figuras en results/imgs/ con prefijo 04_*.
    · Imprime estadísticas descriptivas para Insights_EDA.md.

Inputs:
    - data/staging/S01/siniestros_staging.parquet
    - data/staging/S01/empresa_siniestralidad_completa.parquet

Outputs:
    - data/staging/S01/outliers_deteccion_resumen.parquet
    - data/staging/S01/siniestros_con_flags_outliers.parquet
    - data/staging/S01/empresa_con_flags_outliers.parquet
    - data/staging/S01/siniestros_tratados.parquet
    - data/staging/S01/empresa_siniestralidad_tratada.parquet
    - data/staging/S01/outliers_tratamiento_impacto.parquet
    - sections/S01-.../results/imgs/04_*.png

Uso:
    .venv/bin/python sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/04-analisis_outliers/analisis_outliers.py
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

# Detection / treatment parameters
IQR_K = 1.5
MAD_THRESHOLD = 3.5
PCT_LOW, PCT_HIGH = 1.0, 99.0  # winsorization percentiles

# Claim-level and company-level variables under analysis
CLAIM_VARS = ["costo_total", "dias_incapacidad", "costo_asistencial",
              "costo_prestacion_economica"]
COMPANY_VARS = ["n_siniestros", "costo_total_empresa", "frecuencia_x100",
                "n_trabajadores", "prima_anual"]

CLAIM_LABELS = {
    "costo_total": "Costo total",
    "dias_incapacidad": "Días incapacidad",
    "costo_asistencial": "Costo asistencial",
    "costo_prestacion_economica": "Prestación económica",
}
COMPANY_LABELS = {
    "n_siniestros": "Nº siniestros",
    "costo_total_empresa": "Costo acum. empresa",
    "frecuencia_x100": "Frecuencia ×100",
    "n_trabajadores": "Nº trabajadores",
    "prima_anual": "Prima anual",
}


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, name: str) -> None:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _fmt_millones(x, _):
    if abs(x) >= 1e9:
        return f"${x / 1e9:.1f}B"
    if abs(x) >= 1e6:
        return f"${x / 1e6:.0f}M"
    return f"${x:,.0f}"


def _iqr_bounds(series: pd.Series, k: float = IQR_K):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr, q1, q3, iqr


def _mad_bounds(series: pd.Series, threshold: float = MAD_THRESHOLD):
    """Modified Z-score bounds using MAD (Iglewicz & Hoaglin)."""
    med = series.median()
    mad = np.median(np.abs(series - med))
    if mad == 0 or np.isnan(mad):
        return series.min(), series.max(), med, mad
    # Modified z = 0.6745 * (x - med) / MAD; invert for bounds
    half_width = threshold * mad / 0.6745
    return med - half_width, med + half_width, med, mad


def _pct_bounds(series: pd.Series, lo: float = PCT_LOW, hi: float = PCT_HIGH):
    return series.quantile(lo / 100), series.quantile(hi / 100)


def detect_outliers(series: pd.Series) -> dict:
    """Return masks and bounds for IQR, MAD and percentile methods."""
    s = series.dropna()
    iqr_lo, iqr_hi, q1, q3, iqr = _iqr_bounds(s)
    mad_lo, mad_hi, med, mad = _mad_bounds(s)
    pct_lo, pct_hi = _pct_bounds(s)

    mask_iqr = (series < iqr_lo) | (series > iqr_hi)
    mask_mad = (series < mad_lo) | (series > mad_hi)
    mask_pct = (series < pct_lo) | (series > pct_hi)

    n = series.notna().sum()
    return {
        "n_valid": int(n),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std()),
        "min": float(s.min()),
        "max": float(s.max()),
        "p1": float(pct_lo),
        "p99": float(pct_hi),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr),
        "iqr_lo": float(iqr_lo),
        "iqr_hi": float(iqr_hi),
        "mad": float(mad),
        "mad_lo": float(mad_lo),
        "mad_hi": float(mad_hi),
        "n_iqr": int(mask_iqr.fillna(False).sum()),
        "pct_iqr": float(mask_iqr.fillna(False).sum() / n * 100) if n else np.nan,
        "n_mad": int(mask_mad.fillna(False).sum()),
        "pct_mad": float(mask_mad.fillna(False).sum() / n * 100) if n else np.nan,
        "n_pct": int(mask_pct.fillna(False).sum()),
        "pct_pct": float(mask_pct.fillna(False).sum() / n * 100) if n else np.nan,
        "mask_iqr": mask_iqr.fillna(False),
        "mask_mad": mask_mad.fillna(False),
        "mask_pct": mask_pct.fillna(False),
    }


def winsorize(series: pd.Series, lo: float = PCT_LOW, hi: float = PCT_HIGH) -> pd.Series:
    """Clip series to [P_lo, P_hi] percentiles (keeps all rows)."""
    p_lo, p_hi = _pct_bounds(series.dropna(), lo, hi)
    return series.clip(lower=p_lo, upper=p_hi)


# ──────────────────────────────────────────────────────────────────────────────
#  1. Load staging
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Loading staging datasets...")

siniestros = pd.read_parquet(DATA_STAGING / "siniestros_staging.parquet")
empresas = pd.read_parquet(DATA_STAGING / "empresa_siniestralidad_completa.parquet")

print(f"   siniestros : {siniestros.shape}")
print(f"   empresas   : {empresas.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  2. Detection
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔍  Detecting outliers (IQR / MAD / P1–P99)...")

resumen_rows = []
claim_flags = siniestros[["id_siniestro", "id_empresa", "tipo", "gravedad",
                          "anio"]].copy()
company_flags = empresas[["id_empresa", "clase_riesgo", "sector",
                          "segmento"]].copy()

claim_detections = {}
for var in CLAIM_VARS:
    det = detect_outliers(siniestros[var])
    claim_detections[var] = det
    claim_flags[f"out_iqr_{var}"] = det["mask_iqr"].astype(int)
    claim_flags[f"out_mad_{var}"] = det["mask_mad"].astype(int)
    claim_flags[f"out_pct_{var}"] = det["mask_pct"].astype(int)
    resumen_rows.append({
        "nivel": "siniestro",
        "variable": var,
        "etiqueta": CLAIM_LABELS[var],
        **{k: det[k] for k in [
            "n_valid", "mean", "median", "std", "min", "max",
            "p1", "p99", "q1", "q3", "iqr", "iqr_lo", "iqr_hi",
            "mad", "mad_lo", "mad_hi",
            "n_iqr", "pct_iqr", "n_mad", "pct_mad", "n_pct", "pct_pct",
        ]},
    })
    print(
        f"   [siniestro] {var:30s}  IQR={det['pct_iqr']:5.2f}%  "
        f"MAD={det['pct_mad']:5.2f}%  P1-P99={det['pct_pct']:5.2f}%"
    )

company_detections = {}
for var in COMPANY_VARS:
    det = detect_outliers(empresas[var])
    company_detections[var] = det
    company_flags[f"out_iqr_{var}"] = det["mask_iqr"].astype(int)
    company_flags[f"out_mad_{var}"] = det["mask_mad"].astype(int)
    company_flags[f"out_pct_{var}"] = det["mask_pct"].astype(int)
    resumen_rows.append({
        "nivel": "empresa",
        "variable": var,
        "etiqueta": COMPANY_LABELS[var],
        **{k: det[k] for k in [
            "n_valid", "mean", "median", "std", "min", "max",
            "p1", "p99", "q1", "q3", "iqr", "iqr_lo", "iqr_hi",
            "mad", "mad_lo", "mad_hi",
            "n_iqr", "pct_iqr", "n_mad", "pct_mad", "n_pct", "pct_pct",
        ]},
    })
    print(
        f"   [empresa  ] {var:30s}  IQR={det['pct_iqr']:5.2f}%  "
        f"MAD={det['pct_mad']:5.2f}%  P1-P99={det['pct_pct']:5.2f}%"
    )

# Composite flags: outlier on any key cost/severity variable
claim_flags["out_iqr_any_key"] = (
    (claim_flags["out_iqr_costo_total"] == 1)
    | (claim_flags["out_iqr_dias_incapacidad"] == 1)
).astype(int)
claim_flags["out_pct_any_key"] = (
    (claim_flags["out_pct_costo_total"] == 1)
    | (claim_flags["out_pct_dias_incapacidad"] == 1)
).astype(int)

company_flags["out_iqr_any_key"] = (
    (company_flags["out_iqr_n_siniestros"] == 1)
    | (company_flags["out_iqr_costo_total_empresa"] == 1)
).astype(int)
company_flags["out_pct_any_key"] = (
    (company_flags["out_pct_n_siniestros"] == 1)
    | (company_flags["out_pct_costo_total_empresa"] == 1)
).astype(int)

resumen = pd.DataFrame(resumen_rows)

# ──────────────────────────────────────────────────────────────────────────────
#  3. Treatment (winsorization P1–P99; rows kept)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🛠️   Applying winsorization P1–P99 (rows retained)...")

siniestros_trat = siniestros.copy()
for var in CLAIM_VARS:
    siniestros_trat[f"{var}_w"] = winsorize(siniestros[var])
    siniestros_trat[f"log_{var}_w"] = np.log1p(siniestros_trat[f"{var}_w"])

empresas_trat = empresas.copy()
for var in COMPANY_VARS:
    empresas_trat[f"{var}_w"] = winsorize(empresas[var])
    # log of winsorized (for skewed monetary / count vars)
    if var in ("n_siniestros", "costo_total_empresa", "n_trabajadores", "prima_anual"):
        empresas_trat[f"log_{var}_w"] = np.log1p(empresas_trat[f"{var}_w"].fillna(0))

# Impact before / after
impacto_rows = []
for nivel, df_orig, df_trat, vars_ in [
    ("siniestro", siniestros, siniestros_trat, CLAIM_VARS),
    ("empresa", empresas, empresas_trat, COMPANY_VARS),
]:
    for var in vars_:
        o = df_orig[var].dropna()
        t = df_trat[f"{var}_w"].dropna()
        impacto_rows.append({
            "nivel": nivel,
            "variable": var,
            "etiqueta": (CLAIM_LABELS if nivel == "siniestro" else COMPANY_LABELS)[var],
            "n": int(o.shape[0]),
            "mean_antes": float(o.mean()),
            "mean_despues": float(t.mean()),
            "median_antes": float(o.median()),
            "median_despues": float(t.median()),
            "std_antes": float(o.std()),
            "std_despues": float(t.std()),
            "max_antes": float(o.max()),
            "max_despues": float(t.max()),
            "p99_antes": float(o.quantile(0.99)),
            "p99_despues": float(t.quantile(0.99)),
            "skew_antes": float(o.skew()),
            "skew_despues": float(t.skew()),
            "pct_clipados": float(((df_orig[var] != df_trat[f"{var}_w"])
                                   & df_orig[var].notna()).mean() * 100),
        })
impacto = pd.DataFrame(impacto_rows)

print("\n   Impacto winsorización (media / max / % clipados):")
for _, r in impacto.iterrows():
    print(
        f"   [{r['nivel']:9s}] {r['variable']:30s}  "
        f"mean {r['mean_antes']:.2f}→{r['mean_despues']:.2f}  "
        f"max {r['max_antes']:.2f}→{r['max_despues']:.2f}  "
        f"clip={r['pct_clipados']:.2f}%"
    )

# ──────────────────────────────────────────────────────────────────────────────
#  4. Persist staging
# ──────────────────────────────────────────────────────────────────────────────
print("\n💾  Saving staging datasets...")

# Attach original metrics to flag tables for reuse
claim_out = claim_flags.merge(
    siniestros[["id_siniestro"] + CLAIM_VARS], on="id_siniestro", how="left"
)
company_out = company_flags.merge(
    empresas[["id_empresa"] + COMPANY_VARS], on="id_empresa", how="left"
)

resumen.to_parquet(DATA_STAGING / "outliers_deteccion_resumen.parquet", index=False)
claim_out.to_parquet(DATA_STAGING / "siniestros_con_flags_outliers.parquet", index=False)
company_out.to_parquet(DATA_STAGING / "empresa_con_flags_outliers.parquet", index=False)
siniestros_trat.to_parquet(DATA_STAGING / "siniestros_tratados.parquet", index=False)
empresas_trat.to_parquet(
    DATA_STAGING / "empresa_siniestralidad_tratada.parquet", index=False
)
impacto.to_parquet(DATA_STAGING / "outliers_tratamiento_impacto.parquet", index=False)

print(f"   ✅  Staging saved to {DATA_STAGING}")
print(f"      - outliers_deteccion_resumen.parquet      : {resumen.shape}")
print(f"      - siniestros_con_flags_outliers.parquet   : {claim_out.shape}")
print(f"      - empresa_con_flags_outliers.parquet      : {company_out.shape}")
print(f"      - siniestros_tratados.parquet             : {siniestros_trat.shape}")
print(f"      - empresa_siniestralidad_tratada.parquet  : {empresas_trat.shape}")
print(f"      - outliers_tratamiento_impacto.parquet    : {impacto.shape}")

palette = sb.get_palette("categorical")
traffic = sb.get_palette("traffic_light")

# ──────────────────────────────────────────────────────────────────────────────
#  5. BLOCK A – Detección
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK A – Detección visual")

# A1. Boxplots claim-level (log1p scale for readability)
fig, axes = sb.create_dashboard(
    1, 4,
    title="Valores Atípicos a Nivel de Siniestro",
    subtitle="Boxplots en escala log(1+x); bigotes ≈ IQR × 1.5",
)
for ax, var in zip(axes, CLAIM_VARS):
    data = np.log1p(siniestros[var].dropna())
    bp = ax.boxplot(
        [data], tick_labels=[CLAIM_LABELS[var]],
        patch_artist=True, widths=0.55, showfliers=True,
        flierprops=dict(marker="o", markersize=2.5, alpha=0.25,
                        markerfacecolor=traffic[2], markeredgecolor="none"),
    )
    for box in bp["boxes"]:
        box.set_facecolor(palette[0])
        box.set_alpha(0.75)
    for med in bp["medians"]:
        med.set_color(sb.AZUL_PROFUNDO.hex)
        med.set_linewidth(2)
    ax.set_ylabel("log(1 + valor)")
    ax.set_title(CLAIM_LABELS[var], fontsize=10)
    pct = claim_detections[var]["pct_iqr"]
    ax.text(
        0.5, 0.97, f"IQR outliers: {pct:.1f}%",
        transform=ax.transAxes, ha="center", va="top", fontsize=8,
        color=sb.AZUL_PROFUNDO.hex,
    )
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Detección siniestros")
_save_fig(fig, "04_A1_boxplots_outliers_siniestros.png")

# A2. Boxplots company-level
fig, axes = sb.create_dashboard(
    1, 5,
    title="Valores Atípicos a Nivel de Empresa",
    subtitle="Boxplots en escala log(1+x); bigotes ≈ IQR × 1.5",
)
for ax, var in zip(axes, COMPANY_VARS):
    data = np.log1p(empresas[var].dropna())
    bp = ax.boxplot(
        [data], tick_labels=[COMPANY_LABELS[var]],
        patch_artist=True, widths=0.55, showfliers=True,
        flierprops=dict(marker="o", markersize=2.5, alpha=0.3,
                        markerfacecolor=traffic[2], markeredgecolor="none"),
    )
    for box in bp["boxes"]:
        box.set_facecolor(palette[1])
        box.set_alpha(0.75)
    for med in bp["medians"]:
        med.set_color(sb.AZUL_PROFUNDO.hex)
        med.set_linewidth(2)
    ax.set_ylabel("log(1 + valor)")
    ax.set_title(COMPANY_LABELS[var], fontsize=9)
    pct = company_detections[var]["pct_iqr"]
    ax.text(
        0.5, 0.97, f"IQR: {pct:.1f}%",
        transform=ax.transAxes, ha="center", va="top", fontsize=8,
        color=sb.AZUL_PROFUNDO.hex,
    )
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Detección empresas")
_save_fig(fig, "04_A2_boxplots_outliers_empresas.png")

# A3. % outliers by method (grouped bars)
fig, ax = sb.create_report_figure(
    title="Tasa de Valores Atípicos por Método de Detección",
    subtitle="Comparación IQR (1.5×), MAD (z-mod ≥ 3.5) y percentiles P1–P99",
    figsize=(14, 6.5),
)
plot_df = resumen.copy()
plot_df["label"] = plot_df["nivel"].str[0].str.upper() + " · " + plot_df["etiqueta"]
x = np.arange(len(plot_df))
w = 0.25
ax.bar(x - w, plot_df["pct_iqr"], width=w, color=palette[0], label="IQR 1.5×", alpha=0.9)
ax.bar(x, plot_df["pct_mad"], width=w, color=palette[1], label="MAD ≥ 3.5", alpha=0.9)
ax.bar(x + w, plot_df["pct_pct"], width=w, color=palette[2], label="Fuera P1–P99", alpha=0.9)
ax.set_xticks(x)
ax.set_xticklabels(plot_df["label"], rotation=35, ha="right", fontsize=8)
ax.set_ylabel("% de observaciones atípicas")
ax.set_xlabel("Variable")
ax.legend(frameon=True, loc="upper right")
ax.set_ylim(0, max(plot_df[["pct_iqr", "pct_mad", "pct_pct"]].max()) * 1.25)
ax.axhline(2.0, color="#AAAAAA", linestyle=":", linewidth=1, label="_nolegend_")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Comparación de métodos")
_save_fig(fig, "04_A3_tasa_outliers_por_metodo.png")

# ──────────────────────────────────────────────────────────────────────────────
#  6. BLOCK B – Tratamiento (antes / después)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK B – Tratamiento (winsorización)")


def _before_after_hist(var_orig, var_w, title, subtitle, fname, color_idx=0):
    fig, axes = sb.create_dashboard(1, 2, title=title, subtitle=subtitle)
    ax0, ax1 = axes[0], axes[1]
    o = var_orig.dropna()
    t = var_w.dropna()
    # log scale histograms for skewed vars
    bins = 60
    ax0.hist(np.log1p(o), bins=bins, color=palette[color_idx], alpha=0.85,
             edgecolor="white", linewidth=0.3)
    ax0.set_title("Antes (original)")
    ax0.set_xlabel("log(1 + valor)")
    ax0.set_ylabel("Frecuencia")
    ax0.axvline(np.log1p(o.quantile(0.99)), color=traffic[2], linestyle="--",
                linewidth=1.5, label=f"P99={o.quantile(0.99):,.0f}")
    ax0.legend(fontsize=8, frameon=True)

    ax1.hist(np.log1p(t), bins=bins, color=palette[color_idx + 1 if color_idx < 4 else 0],
             alpha=0.85, edgecolor="white", linewidth=0.3)
    ax1.set_title("Después (winsorizado P1–P99)")
    ax1.set_xlabel("log(1 + valor)")
    ax1.set_ylabel("Frecuencia")
    ax1.axvline(np.log1p(t.max()), color=sb.AZUL_SURA.hex, linestyle="--",
                linewidth=1.5, label=f"Máx={t.max():,.0f}")
    ax1.legend(fontsize=8, frameon=True)
    sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Winsorización")
    _save_fig(fig, fname)


_before_after_hist(
    siniestros["costo_total"], siniestros_trat["costo_total_w"],
    title="Tratamiento: Costo Total por Siniestro",
    subtitle="Winsorización P1–P99 · escala log para visualización",
    fname="04_B1_winsor_costo_total.png",
    color_idx=0,
)
_before_after_hist(
    siniestros["dias_incapacidad"], siniestros_trat["dias_incapacidad_w"],
    title="Tratamiento: Días de Incapacidad",
    subtitle="Winsorización P1–P99 · escala log para visualización",
    fname="04_B2_winsor_dias_incapacidad.png",
    color_idx=1,
)
_before_after_hist(
    empresas["costo_total_empresa"], empresas_trat["costo_total_empresa_w"],
    title="Tratamiento: Costo Acumulado por Empresa",
    subtitle="Winsorización P1–P99 · escala log para visualización",
    fname="04_B3_winsor_costo_empresa.png",
    color_idx=2,
)

# ──────────────────────────────────────────────────────────────────────────────
#  7. BLOCK C – Contexto y decisión de tratamiento
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  BLOCK C – Contexto de outliers y decisión")

# C1. Scatter costo vs días, highlight P99 outliers
fig, ax = sb.create_report_figure(
    title="Costo Total vs Días de Incapacidad",
    subtitle="Resaltados: outliers P1–P99 en costo o severidad",
    figsize=(11, 7),
)
mask_out = (
    (claim_flags["out_pct_costo_total"] == 1)
    | (claim_flags["out_pct_dias_incapacidad"] == 1)
)
ax.scatter(
    siniestros.loc[~mask_out, "dias_incapacidad"],
    siniestros.loc[~mask_out, "costo_total"],
    s=8, alpha=0.25, color=palette[0], label="Dentro P1–P99",
)
ax.scatter(
    siniestros.loc[mask_out, "dias_incapacidad"],
    siniestros.loc[mask_out, "costo_total"],
    s=14, alpha=0.55, color=traffic[2], label="Outlier P1–P99",
    edgecolors="none",
)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Días de incapacidad (log)")
ax.set_ylabel("Costo total COP (log)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millones))
ax.legend(frameon=True, loc="upper left")
n_out = int(mask_out.sum())
ax.text(
    0.98, 0.05,
    f"Outliers P1–P99: {n_out:,} ({n_out / len(siniestros) * 100:.1f}%)",
    transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
    color=sb.AZUL_PROFUNDO.hex,
)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Costo × severidad")
_save_fig(fig, "04_C1_scatter_costo_vs_dias_outliers.png")

# C2. Outlier rate (IQR on costo_total) by clase_riesgo
sin_cls = siniestros.merge(
    empresas[["id_empresa", "clase_riesgo"]], on="id_empresa", how="left"
)
sin_cls["out_iqr_costo"] = claim_flags["out_iqr_costo_total"].values
sin_cls["out_iqr_dias"] = claim_flags["out_iqr_dias_incapacidad"].values

by_clase = (
    sin_cls.groupby("clase_riesgo", observed=True)
    .agg(
        n=("id_siniestro", "count"),
        pct_out_costo=("out_iqr_costo", "mean"),
        pct_out_dias=("out_iqr_dias", "mean"),
    )
    .reset_index()
)
by_clase["pct_out_costo"] *= 100
by_clase["pct_out_dias"] *= 100

fig, ax = sb.create_report_figure(
    title="Tasa de Outliers IQR por Clase de Riesgo",
    subtitle="Proporción de siniestros fuera de IQR 1.5× en costo y severidad",
    figsize=(11, 6),
)
x = np.arange(len(by_clase))
w = 0.35
ax.bar(x - w / 2, by_clase["pct_out_costo"], width=w, color=palette[0],
       label="Costo total", alpha=0.9)
ax.bar(x + w / 2, by_clase["pct_out_dias"], width=w, color=palette[2],
       label="Días incapacidad", alpha=0.9)
ax.set_xticks(x)
ax.set_xticklabels([f"Clase {c}" for c in by_clase["clase_riesgo"]])
ax.set_ylabel("% outliers IQR")
ax.set_xlabel("Clase de riesgo ARL")
ax.legend(frameon=True, loc="upper left")
for i, row in by_clase.iterrows():
    ax.text(i - w / 2, row["pct_out_costo"] + 0.3, f"{row['pct_out_costo']:.1f}%",
            ha="center", fontsize=8)
    ax.text(i + w / 2, row["pct_out_dias"] + 0.3, f"{row['pct_out_dias']:.1f}%",
            ha="center", fontsize=8)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Por clase de riesgo")
_save_fig(fig, "04_C2_outliers_por_clase_riesgo.png")

# C3. Impact bars: % reduction in max / skew for key vars
fig, axes = sb.create_dashboard(
    1, 2,
    title="Impacto del Tratamiento (Winsorización P1–P99)",
    subtitle="Reducción del máximo y de la asimetría en variables clave",
)
key_impacto = impacto[impacto["variable"].isin(
    ["costo_total", "dias_incapacidad", "costo_total_empresa", "n_siniestros"]
)].copy()
key_impacto["pct_red_max"] = (
    (key_impacto["max_antes"] - key_impacto["max_despues"])
    / key_impacto["max_antes"] * 100
)
key_impacto["pct_red_skew"] = (
    (key_impacto["skew_antes"] - key_impacto["skew_despues"])
    / key_impacto["skew_antes"].abs().clip(lower=1e-9) * 100
)
labels = key_impacto["etiqueta"].tolist()
y = np.arange(len(key_impacto))

ax0, ax1 = axes[0], axes[1]
ax0.barh(y, key_impacto["pct_red_max"], color=palette[0], alpha=0.9)
ax0.set_yticks(y)
ax0.set_yticklabels(labels, fontsize=9)
ax0.set_xlabel("% reducción del máximo")
ax0.set_title("Contracción de la cola (máx)")
ax0.invert_yaxis()
for yi, v in zip(y, key_impacto["pct_red_max"]):
    ax0.text(v + 0.5, yi, f"{v:.1f}%", va="center", fontsize=8)

ax1.barh(y, key_impacto["pct_red_skew"], color=palette[1], alpha=0.9)
ax1.set_yticks(y)
ax1.set_yticklabels(labels, fontsize=9)
ax1.set_xlabel("% reducción de asimetría (skew)")
ax1.set_title("Estabilización de la distribución")
ax1.invert_yaxis()
for yi, v in zip(y, key_impacto["pct_red_skew"]):
    ax1.text(v + 0.5, yi, f"{v:.1f}%", va="center", fontsize=8)

sb.add_sura_footer(fig, text="S01 – EDA | 1.2 Outliers | Impacto del tratamiento")
_save_fig(fig, "04_C3_impacto_winsorizacion.png")

# ──────────────────────────────────────────────────────────────────────────────
#  8. Summary stats for Insights
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("RESUMEN PARA Insights_EDA.md")
print("=" * 72)

print("\n--- Detección (% outliers) ---")
print(
    resumen[
        ["nivel", "variable", "pct_iqr", "pct_mad", "pct_pct", "p99", "max"]
    ].to_string(index=False)
)

print("\n--- Outliers IQR costo_total por clase ---")
print(by_clase.to_string(index=False))

print("\n--- Impacto winsorización ---")
print(
    impacto[
        ["nivel", "variable", "mean_antes", "mean_despues", "max_antes",
         "max_despues", "skew_antes", "skew_despues", "pct_clipados"]
    ].to_string(index=False)
)

print("\n--- Flags compuestos ---")
print(
    f"Siniestros out_pct (costo|días): "
    f"{claim_flags['out_pct_any_key'].mean() * 100:.2f}%"
)
print(
    f"Empresas out_pct (n_sin|costo): "
    f"{company_flags['out_pct_any_key'].mean() * 100:.2f}%"
)
print(
    f"Siniestros out_iqr (costo|días): "
    f"{claim_flags['out_iqr_any_key'].mean() * 100:.2f}%"
)
print(
    f"Empresas out_iqr (n_sin|costo): "
    f"{company_flags['out_iqr_any_key'].mean() * 100:.2f}%"
)

print("\n✅  Análisis de outliers completado.")
print("    Decisión: winsorizar P1–P99 para features de modelado;")
print("    conservar originales para análisis de cola / resultado técnico.")
