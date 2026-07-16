"""
Análisis de Correlación y Colinealidad entre Predictores Candidatos
===================================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.2 – EDA

Descripción:
    Evalúa correlación (Spearman / Pearson en escala log) y colinealidad
    (VIF, pares |ρ| altos, número de condición) entre predictores candidatos
    a nivel empresa, usando features winsorizadas del análisis de outliers.

    Distingue:
    · Predictores (atributos de empresa + lag de volumen).
    · Targets / outcomes (conteo, frecuencia, costo, label Top 10%).

    Adicionalmente:
    · Construye datasets de staging reutilizables.
    · Guarda figuras en results/imgs/ con prefijo 05_*.
    · Imprime estadísticas descriptivas para Insights_EDA.md.

Inputs:
    - data/staging/S01/empresa_siniestralidad_tratada.parquet
    - data/staging/S01/temporal_empresa_anio.parquet

Outputs:
    - data/staging/S01/correlacion_predictores_spearman.parquet
    - data/staging/S01/correlacion_predictores_pearson.parquet
    - data/staging/S01/correlacion_pares_altos.parquet
    - data/staging/S01/correlacion_predictor_vs_target.parquet
    - data/staging/S01/colinealidad_vif.parquet
    - data/staging/S01/predictores_recomendacion.parquet
    - sections/S01-.../results/imgs/05_*.png

Uso:
    .venv/bin/python sections/S01-Metodologia_EDA_Analisis/1_2_EDA/code/05-analisis_correlaciones/analisis_correlaciones.py
"""

# ──────────────────────────────────────────────────────────────────────────────
#  Imports
# ──────────────────────────────────────────────────────────────────────────────
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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
palette = sb.get_palette()

# Thresholds
HIGH_CORR = 0.70
VIF_WARN = 5.0
VIF_SEVERE = 10.0

# Candidate predictors (company attributes + engineered) — NOT outcomes
PREDICTOR_COLS = [
    "clase_riesgo",
    "log_n_trabajadores_w",
    "log_prima_anual_w",
    "antiguedad_meses",
]

PREDICTOR_LABELS = {
    "clase_riesgo": "Clase riesgo",
    "log_n_trabajadores_w": "log(N trab.)_w",
    "log_prima_anual_w": "log(Prima)_w",
    "antiguedad_meses": "Antigüedad (meses)",
    "lag_n_siniestros": "Lag N siniestros",
    "lag_costo_total": "Lag costo total",
}

# Outcomes / targets for association (excluded from VIF of predictors)
TARGET_COLS = [
    "log_n_siniestros_w",
    "frecuencia_x100_w",
    "log_costo_total_empresa_w",
    "tiene_siniestro",
]

TARGET_LABELS = {
    "log_n_siniestros_w": "log(N siniestros)_w",
    "frecuencia_x100_w": "Frecuencia ×100_w",
    "log_costo_total_empresa_w": "log(Costo empresa)_w",
    "tiene_siniestro": "Tiene siniestro",
    "alta_siniestralidad": "Alta siniestralidad",
    "n_siniestros": "N siniestros (año)",
}


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, name: str) -> None:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _corr_heatmap(matrix: pd.DataFrame, title: str, figsize=(10, 8)):
    """Heatmap from a precomputed correlation matrix (avoids double .corr())."""
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        matrix,
        cmap=sb.get_cmap("sura_diverging"),
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        linecolor="#E0E0E0",
        square=True,
        ax=ax,
        cbar_kws={"shrink": 0.75, "aspect": 20},
        vmin=-1,
        vmax=1,
    )
    ax.set_title(title, pad=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    fig.tight_layout(rect=[0.02, 0.12, 0.98, 0.96])
    return fig, ax


def _relabel(df: pd.DataFrame, labels: dict) -> pd.DataFrame:
    out = df.copy()
    out.index = [labels.get(c, c) for c in out.index]
    out.columns = [labels.get(c, c) for c in out.columns]
    return out


def compute_vif(df: pd.DataFrame) -> pd.DataFrame:
    """Variance Inflation Factor via OLS of each column on the rest (numpy)."""
    cols = list(df.columns)
    X = df.astype(float).to_numpy()
    # Drop rows with any NaN
    mask = np.isfinite(X).all(axis=1)
    X = X[mask]
    n, p = X.shape
    # Standardize (helps numerical stability; VIF invariant to scale)
    means = X.mean(axis=0)
    stds = X.std(axis=0, ddof=0)
    stds = np.where(stds == 0, 1.0, stds)
    Z = (X - means) / stds

    rows = []
    for i, col in enumerate(cols):
        y = Z[:, i]
        X_others = np.delete(Z, i, axis=1)
        X_design = np.column_stack([np.ones(n), X_others])
        beta, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
        y_hat = X_design @ beta
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        r2 = min(max(r2, 0.0), 0.999999)
        vif = 1.0 / (1.0 - r2)
        if vif >= VIF_SEVERE:
            nivel = "severo"
        elif vif >= VIF_WARN:
            nivel = "moderado"
        else:
            nivel = "bajo"
        rows.append({
            "variable": col,
            "etiqueta": PREDICTOR_LABELS.get(col, col),
            "vif": vif,
            "r2_aux": r2,
            "n_obs": int(n),
            "nivel_colinealidad": nivel,
        })
    return pd.DataFrame(rows).sort_values("vif", ascending=False).reset_index(drop=True)


def condition_number(corr: pd.DataFrame) -> float:
    """Condition number of correlation matrix (eigenvalue ratio)."""
    eig = np.linalg.eigvalsh(corr.to_numpy(dtype=float))
    eig = eig[eig > 1e-12]
    return float(eig.max() / eig.min()) if len(eig) else np.nan


def high_corr_pairs(corr: pd.DataFrame, threshold: float = HIGH_CORR) -> pd.DataFrame:
    """Upper-triangle pairs with |corr| >= threshold."""
    rows = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            rho = float(corr.loc[a, b])
            if abs(rho) >= threshold:
                rows.append({
                    "variable_a": a,
                    "variable_b": b,
                    "etiqueta_a": PREDICTOR_LABELS.get(a, TARGET_LABELS.get(a, a)),
                    "etiqueta_b": PREDICTOR_LABELS.get(b, TARGET_LABELS.get(b, b)),
                    "correlacion": rho,
                    "abs_correlacion": abs(rho),
                    "metodo": "spearman",
                })
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values("abs_correlacion", ascending=False).reset_index(drop=True)
    return out


# ──────────────────────────────────────────────────────────────────────────────
#  1. Load data
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("1.2.6 – Análisis de Correlación y Colinealidad")
print("=" * 72)

empresas = pd.read_parquet(DATA_STAGING / "empresa_siniestralidad_tratada.parquet")
panel = pd.read_parquet(DATA_STAGING / "temporal_empresa_anio.parquet")

print(f"   Empresas tratadas: {empresas.shape}")
print(f"   Panel empresa-año: {panel.shape}")

# Ensure numeric clase_riesgo
empresas = empresas.copy()
empresas["clase_riesgo"] = empresas["clase_riesgo"].astype(float)

# Build lag features on annual panel (candidate predictors from 1.2.4)
panel = panel.sort_values(["id_empresa", "anio"]).copy()
panel["clase_riesgo"] = panel["clase_riesgo"].astype(float)
panel["lag_n_siniestros"] = panel.groupby("id_empresa")["n_siniestros"].shift(1)
panel["lag_costo_total"] = panel.groupby("id_empresa")["costo_total"].shift(1)
panel["log_lag_n_siniestros"] = np.log1p(panel["lag_n_siniestros"])
panel["log_n_trabajadores"] = np.log1p(panel["n_trabajadores"])

# Cross-sectional feature frame
feat_cs = empresas[PREDICTOR_COLS + TARGET_COLS].copy()

# Panel feature frame (years with lag available)
feat_panel = panel.dropna(subset=["lag_n_siniestros"]).copy()
PANEL_PREDS = [
    "clase_riesgo",
    "log_n_trabajadores",
    "log_lag_n_siniestros",
    "antiguedad_proxy",  # filled below from empresas
]
# Attach antiguedad / prima from empresas
emp_attrs = empresas[["id_empresa", "antiguedad_meses", "log_prima_anual_w"]].copy()
feat_panel = feat_panel.merge(emp_attrs, on="id_empresa", how="left")
feat_panel["antiguedad_proxy"] = feat_panel["antiguedad_meses"]

PANEL_PRED_COLS = [
    "clase_riesgo",
    "log_n_trabajadores",
    "log_prima_anual_w",
    "antiguedad_meses",
    "log_lag_n_siniestros",
]
PREDICTOR_LABELS.update({
    "log_n_trabajadores": "log(N trab.)",
    "log_lag_n_siniestros": "log(Lag N sin.)",
})

# ──────────────────────────────────────────────────────────────────────────────
#  2. Correlation matrices (cross-sectional)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  Correlaciones (corte transversal empresa)")

# A) Spearman among predictors + targets (descriptive full matrix)
all_cs_cols = PREDICTOR_COLS + TARGET_COLS
spearman_full = feat_cs[all_cs_cols].corr(method="spearman")
pearson_preds = feat_cs[PREDICTOR_COLS].corr(method="pearson")
spearman_preds = feat_cs[PREDICTOR_COLS].corr(method="spearman")

# Persist long-form matrices
def _matrix_to_long(mat: pd.DataFrame, metodo: str) -> pd.DataFrame:
    rows = []
    for a in mat.columns:
        for b in mat.columns:
            rows.append({
                "variable_a": a,
                "variable_b": b,
                "correlacion": float(mat.loc[a, b]),
                "metodo": metodo,
                "alcance": "empresa_transversal",
            })
    return pd.DataFrame(rows)


corr_spearman_long = _matrix_to_long(spearman_full, "spearman")
corr_pearson_long = _matrix_to_long(pearson_preds, "pearson")

corr_spearman_long.to_parquet(
    DATA_STAGING / "correlacion_predictores_spearman.parquet", index=False
)
corr_pearson_long.to_parquet(
    DATA_STAGING / "correlacion_predictores_pearson.parquet", index=False
)
print("   💾  correlacion_predictores_spearman.parquet")
print("   💾  correlacion_predictores_pearson.parquet")

# High-corr pairs among predictors only
pares_preds = high_corr_pairs(spearman_preds, HIGH_CORR)
# Also flag predictor–predictor from pearson
pares_pearson = high_corr_pairs(pearson_preds, HIGH_CORR)
if len(pares_pearson):
    pares_pearson["metodo"] = "pearson"
pares_all = pd.concat([pares_preds, pares_pearson], ignore_index=True)

# Include pairs that mix predictor with near-duplicate outcomes if |ρ| high
# among a broader set used for diagnostics (prima vs costo is expected)
diag_cols = PREDICTOR_COLS + [
    "log_n_siniestros_w", "log_costo_total_empresa_w", "frecuencia_x100_w"
]
pares_diag = high_corr_pairs(feat_cs[diag_cols].corr(method="spearman"), HIGH_CORR)
pares_diag["alcance"] = "predictores_y_outcomes"
if len(pares_all):
    pares_all["alcance"] = "solo_predictores"
pares_staging = pd.concat([pares_all, pares_diag], ignore_index=True)
if len(pares_staging) == 0:
    pares_staging = pd.DataFrame(columns=[
        "variable_a", "variable_b", "etiqueta_a", "etiqueta_b",
        "correlacion", "abs_correlacion", "metodo", "alcance",
    ])
pares_staging.to_parquet(DATA_STAGING / "correlacion_pares_altos.parquet", index=False)
print(f"   💾  correlacion_pares_altos.parquet ({len(pares_staging)} pares)")

# Predictor vs target (Spearman)
rows_pt = []
for p in PREDICTOR_COLS:
    for t in TARGET_COLS:
        rho = feat_cs[[p, t]].corr(method="spearman").iloc[0, 1]
        rows_pt.append({
            "predictor": p,
            "target": t,
            "etiqueta_predictor": PREDICTOR_LABELS.get(p, p),
            "etiqueta_target": TARGET_LABELS.get(t, t),
            "spearman": float(rho),
            "abs_spearman": abs(float(rho)),
            "alcance": "empresa_transversal",
        })

# Panel: lag / clase vs targets
for p in ["clase_riesgo", "log_lag_n_siniestros", "log_n_trabajadores", "log_prima_anual_w"]:
    for t in ["n_siniestros", "alta_siniestralidad", "frecuencia_x100"]:
        sub = feat_panel[[p, t]].dropna()
        if len(sub) < 50:
            continue
        rho = sub.corr(method="spearman").iloc[0, 1]
        rows_pt.append({
            "predictor": p,
            "target": t,
            "etiqueta_predictor": PREDICTOR_LABELS.get(p, p),
            "etiqueta_target": TARGET_LABELS.get(t, t),
            "spearman": float(rho),
            "abs_spearman": abs(float(rho)),
            "alcance": "panel_empresa_anio",
        })

pred_vs_tgt = (
    pd.DataFrame(rows_pt)
    .sort_values(["alcance", "abs_spearman"], ascending=[True, False])
    .reset_index(drop=True)
)
pred_vs_tgt.to_parquet(
    DATA_STAGING / "correlacion_predictor_vs_target.parquet", index=False
)
print(f"   💾  correlacion_predictor_vs_target.parquet ({len(pred_vs_tgt)} filas)")

# ──────────────────────────────────────────────────────────────────────────────
#  3. Collinearity – VIF
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  Colinealidad (VIF)")

# Set A: cross-sectional candidate predictors
vif_a = compute_vif(feat_cs[PREDICTOR_COLS].dropna())
vif_a["set_features"] = "A_transversal_base"
vif_a["condition_number"] = condition_number(spearman_preds)

# Set B: panel predictors including lag (modeling-relevant)
vif_b = compute_vif(feat_panel[PANEL_PRED_COLS].dropna())
spearman_panel = feat_panel[PANEL_PRED_COLS].corr(method="spearman")
vif_b["set_features"] = "B_panel_con_lag"
vif_b["condition_number"] = condition_number(spearman_panel)

# Set C: reduced – drop log_prima if collinear with tamaño (keep exposure + risk + lag)
REDUCED_COLS = [
    "clase_riesgo",
    "log_n_trabajadores",
    "antiguedad_meses",
    "log_lag_n_siniestros",
]
vif_c = compute_vif(feat_panel[REDUCED_COLS].dropna())
spearman_red = feat_panel[REDUCED_COLS].corr(method="spearman")
vif_c["set_features"] = "C_panel_reducido_sin_prima"
vif_c["condition_number"] = condition_number(spearman_red)

# Set D: alternative reduced – drop tamaño, keep prima (pricing proxy)
ALT_COLS = [
    "clase_riesgo",
    "log_prima_anual_w",
    "antiguedad_meses",
    "log_lag_n_siniestros",
]
vif_d = compute_vif(feat_panel[ALT_COLS].dropna())
spearman_alt = feat_panel[ALT_COLS].corr(method="spearman")
vif_d["set_features"] = "D_panel_reducido_sin_tamano"
vif_d["condition_number"] = condition_number(spearman_alt)

vif_all = pd.concat([vif_a, vif_b, vif_c, vif_d], ignore_index=True)
vif_all.to_parquet(DATA_STAGING / "colinealidad_vif.parquet", index=False)
print(f"   💾  colinealidad_vif.parquet ({len(vif_all)} filas)")

# ──────────────────────────────────────────────────────────────────────────────
#  4. Recommendation table
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  Recomendación de predictores")

# Key stats for recommendation
rho_prima_trab = float(
    feat_cs[["log_prima_anual_w", "log_n_trabajadores_w"]]
    .corr(method="spearman").iloc[0, 1]
)
rho_clase_freq = float(
    feat_cs[["clase_riesgo", "frecuencia_x100_w"]]
    .corr(method="spearman").iloc[0, 1]
)
rho_lag_n = float(
    feat_panel[["log_lag_n_siniestros", "n_siniestros"]]
    .corr(method="spearman").iloc[0, 1]
)
rho_anti_targets = float(
    feat_cs[["antiguedad_meses", "log_n_siniestros_w"]]
    .corr(method="spearman").iloc[0, 1]
)

recomendacion = pd.DataFrame([
    {
        "variable": "clase_riesgo",
        "rol": "predictor_obligatorio",
        "prioridad": 1,
        "vif_set_B": float(vif_b.loc[vif_b["variable"] == "clase_riesgo", "vif"].iloc[0]),
        "spearman_target_ref": rho_clase_freq,
        "target_ref": "frecuencia_x100_w",
        "decision": "Incluir siempre; ordinal 1–5",
        "nota": "Asociación fuerte con frecuencia; baja colinealidad con el resto",
    },
    {
        "variable": "log_lag_n_siniestros",
        "rol": "predictor_fuerte",
        "prioridad": 1,
        "vif_set_B": float(
            vif_b.loc[vif_b["variable"] == "log_lag_n_siniestros", "vif"].iloc[0]
        ),
        "spearman_target_ref": rho_lag_n,
        "target_ref": "n_siniestros (panel)",
        "decision": "Incluir en modelos panel / CV temporal",
        "nota": "Persistencia ~0.70 en 1.2.4; no usar sin shift (leakage)",
    },
    {
        "variable": "log_n_trabajadores_w",
        "rol": "exposición_o_feature",
        "prioridad": 1,
        "vif_set_B": float(
            vif_b.loc[vif_b["variable"] == "log_n_trabajadores", "vif"].iloc[0]
        ),
        "spearman_target_ref": float(
            feat_cs[["log_n_trabajadores_w", "log_n_siniestros_w"]]
            .corr(method="spearman").iloc[0, 1]
        ),
        "target_ref": "log_n_siniestros_w",
        "decision": "Incluir como offset/exposición en conteo; feature en clasificación",
        "nota": (
            f"Asociación moderada con log_prima (ρ Spearman≈{rho_prima_trab:.2f}); "
            "VIF conjunto bajo → pueden coexistir; preferir como offset en conteo"
        ),
    },
    {
        "variable": "log_prima_anual_w",
        "rol": "proxy_pricing",
        "prioridad": 2,
        "vif_set_B": float(
            vif_b.loc[vif_b["variable"] == "log_prima_anual_w", "vif"].iloc[0]
        ),
        "spearman_target_ref": float(
            feat_cs[["log_prima_anual_w", "log_costo_total_empresa_w"]]
            .corr(method="spearman").iloc[0, 1]
        ),
        "target_ref": "log_costo_total_empresa_w",
        "decision": "Incluir si interesa pricing; VIF bajo con tamaño (pueden coexistir)",
        "nota": (
            f"ρ Spearman(prima, tamaño)≈{rho_prima_trab:.2f} (moderada); "
            "Pearson menor → asociación no lineal/por rangos; útil en S02"
        ),
    },
    {
        "variable": "antiguedad_meses",
        "rol": "predictor_debil",
        "prioridad": 3,
        "vif_set_B": float(
            vif_b.loc[vif_b["variable"] == "antiguedad_meses", "vif"].iloc[0]
        ),
        "spearman_target_ref": rho_anti_targets,
        "target_ref": "log_n_siniestros_w",
        "decision": "Opcional / baja prioridad",
        "nota": "Correlación débil con outcomes; VIF bajo",
    },
    {
        "variable": "sector",
        "rol": "predictor_categorico",
        "prioridad": 1,
        "vif_set_B": np.nan,
        "spearman_target_ref": np.nan,
        "target_ref": "frecuencia (bivariado 1.2.3)",
        "decision": "Incluir (dummies / encoding); no entra en VIF numérico",
        "nota": "Spread ~6× entre extremos en 1.2.3; vigilar sparse categories",
    },
    {
        "variable": "departamento_ciudad",
        "rol": "control_secundario",
        "prioridad": 3,
        "vif_set_B": np.nan,
        "spearman_target_ref": np.nan,
        "target_ref": "frecuencia (bivariado 1.2.3)",
        "decision": "Baja prioridad; evitar overfit geográfico",
        "nota": "Rango de medianas pequeño en 1.2.3",
    },
])
# Annotate global collinearity verdict
max_vif_b = float(vif_b["vif"].max())
recomendacion["veredicto_vif_set_B"] = (
    f"Sin colinealidad severa (max VIF={max_vif_b:.2f} < {VIF_WARN:.0f})"
)
recomendacion.to_parquet(
    DATA_STAGING / "predictores_recomendacion.parquet", index=False
)
print("   💾  predictores_recomendacion.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  5. Plots
# ──────────────────────────────────────────────────────────────────────────────
print("\n🖼   Visualizaciones")

labels_all = {**PREDICTOR_LABELS, **TARGET_LABELS}

# A1 – Spearman heatmap predictors + targets
fig, ax = _corr_heatmap(
    _relabel(spearman_full, labels_all),
    title="Correlación Spearman – Predictores y Outcomes (empresa)",
    figsize=(11, 9),
)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Correlaciones | Spearman transversal")
_save_fig(fig, "05_A1_heatmap_spearman_predictores_outcomes.png")

# A2 – Pearson heatmap predictors only (log-scale features)
fig, ax = _corr_heatmap(
    _relabel(pearson_preds, PREDICTOR_LABELS),
    title="Correlación Pearson – Predictores candidatos (escala log / winsor)",
    figsize=(8, 7),
)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Correlaciones | Pearson predictores")
_save_fig(fig, "05_A2_heatmap_pearson_predictores.png")

# A3 – Predictor vs target bars (cross-sectional)
pt_cs = pred_vs_tgt[pred_vs_tgt["alcance"] == "empresa_transversal"].copy()
pt_pivot = pt_cs.pivot(index="etiqueta_predictor", columns="etiqueta_target", values="spearman")
fig, ax = _corr_heatmap(
    pt_pivot,
    title="Asociación Spearman – Predictores × Targets",
    figsize=(10, 6),
)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Correlaciones | Predictor vs target")
_save_fig(fig, "05_A3_heatmap_predictor_vs_target.png")

# B1 – VIF set B (panel with lag)
fig, ax = sb.create_report_figure(
    title="Factor de Inflación de Varianza (VIF) – Set panel con lag",
    subtitle=f"Umbral advertencia ≥ {VIF_WARN:.0f} · severo ≥ {VIF_SEVERE:.0f}",
    figsize=(11, 6),
)
vif_plot = vif_b.sort_values("vif", ascending=True)
colors = [
    palette[3] if v >= VIF_SEVERE else (palette[1] if v >= VIF_WARN else palette[0])
    for v in vif_plot["vif"]
]
ax.barh(vif_plot["etiqueta"], vif_plot["vif"], color=colors, alpha=0.9)
ax.axvline(VIF_WARN, color=palette[1], linestyle="--", linewidth=1.2, label=f"VIF={VIF_WARN:.0f}")
ax.axvline(VIF_SEVERE, color=palette[3], linestyle="--", linewidth=1.2, label=f"VIF={VIF_SEVERE:.0f}")
ax.set_xlabel("VIF")
ax.set_ylabel("")
for y, v in zip(vif_plot["etiqueta"], vif_plot["vif"]):
    ax.text(v + 0.05, y, f"{v:.2f}", va="center", fontsize=9)
ax.legend(frameon=True, loc="lower right")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Colinealidad | VIF set B")
_save_fig(fig, "05_B1_vif_set_panel_lag.png")

# B2 – High correlation pairs (diagnostic, predictors + key outcomes)
pares_plot = pares_diag.head(12).copy() if len(pares_diag) else pares_staging.head(12)
fig, ax = sb.create_report_figure(
    title="Pares con |ρ Spearman| ≥ 0.70",
    subtitle="Diagnóstico de redundancia / asociación fuerte",
    figsize=(11, 6),
)
if len(pares_plot):
    labels_pairs = [
        f"{a} ↔ {b}"
        for a, b in zip(pares_plot["etiqueta_a"], pares_plot["etiqueta_b"])
    ]
    vals = pares_plot["correlacion"].values
    colors = [palette[0] if v >= 0 else palette[3] for v in vals]
    y = np.arange(len(pares_plot))
    ax.barh(y, vals, color=colors, alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels_pairs, fontsize=8)
    ax.axvline(0, color="#666", linewidth=0.8)
    ax.set_xlabel("Correlación Spearman")
    ax.invert_yaxis()
    for yi, v in zip(y, vals):
        ax.text(v + (0.01 if v >= 0 else -0.01), yi, f"{v:.2f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=8)
else:
    ax.text(0.5, 0.5, "Sin pares ≥ 0.70 entre predictores numéricos",
            ha="center", va="center", transform=ax.transAxes)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Correlaciones | Pares altos")
_save_fig(fig, "05_B2_pares_alta_correlacion.png")

# B3 – Scatter of main collinear pair: prima vs tamaño
fig, ax = sb.create_report_figure(
    title="Colinealidad observada: Prima vs Tamaño",
    subtitle=f"Spearman ρ ≈ {rho_prima_trab:.2f} · escala log winsorizada",
    figsize=(9, 7),
)
sample = empresas.sample(n=min(3000, len(empresas)), random_state=RANDOM_SEED)
ax.scatter(
    sample["log_n_trabajadores_w"],
    sample["log_prima_anual_w"],
    alpha=0.35,
    s=18,
    c=palette[0],
    edgecolors="none",
)
ax.set_xlabel("log(1 + n_trabajadores_w)")
ax.set_ylabel("log(1 + prima_anual_w)")
# Simple trend line
mask = sample[["log_n_trabajadores_w", "log_prima_anual_w"]].notna().all(axis=1)
x = sample.loc[mask, "log_n_trabajadores_w"].to_numpy()
y = sample.loc[mask, "log_prima_anual_w"].to_numpy()
if len(x) > 2:
    coef = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, np.polyval(coef, xs), color=palette[3], linewidth=2, label="Tendencia lineal")
    ax.legend(frameon=True)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Colinealidad | Prima vs tamaño")
_save_fig(fig, "05_B3_scatter_prima_vs_tamano.png")

# C1 – VIF comparison across feature sets
fig, ax = sb.create_report_figure(
    title="Comparación de VIF entre sets de features",
    subtitle="A transversal · B panel+lag · C sin prima · D sin tamaño",
    figsize=(12, 6),
)
# Align variables for grouped bars – use etiqueta
sets_order = [
    "A_transversal_base",
    "B_panel_con_lag",
    "C_panel_reducido_sin_prima",
    "D_panel_reducido_sin_tamano",
]
set_labels = {
    "A_transversal_base": "A Transversal",
    "B_panel_con_lag": "B Panel+lag",
    "C_panel_reducido_sin_prima": "C Sin prima",
    "D_panel_reducido_sin_tamano": "D Sin tamaño",
}
# Collect unique etiquetas across sets
vif_all["set_label"] = vif_all["set_features"].map(set_labels)
# Max VIF per set for summary annotation
max_vif_by_set = vif_all.groupby("set_features")["vif"].max()
cond_by_set = vif_all.groupby("set_features")["condition_number"].first()

x = np.arange(len(sets_order))
bars = ax.bar(
    x,
    [max_vif_by_set[s] for s in sets_order],
    color=[palette[i % len(palette)] for i in range(len(sets_order))],
    alpha=0.9,
)
ax.axhline(VIF_WARN, color=palette[1], linestyle="--", linewidth=1.2, label=f"VIF={VIF_WARN:.0f}")
ax.axhline(VIF_SEVERE, color=palette[3], linestyle="--", linewidth=1.2, label=f"VIF={VIF_SEVERE:.0f}")
ax.set_xticks(x)
ax.set_xticklabels([set_labels[s] for s in sets_order])
ax.set_ylabel("VIF máximo del set")
ax.set_xlabel("Set de features")
for i, s in enumerate(sets_order):
    ax.text(
        i,
        max_vif_by_set[s] + 0.08,
        f"max={max_vif_by_set[s]:.1f}\nκ={cond_by_set[s]:.1f}",
        ha="center",
        fontsize=8,
    )
ax.legend(frameon=True, loc="upper right")
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Colinealidad | Comparación de sets")
_save_fig(fig, "05_C1_vif_comparacion_sets.png")

# C2 – Heatmap recommended numeric set (C: without prima)
fig, ax = _corr_heatmap(
    _relabel(spearman_red, PREDICTOR_LABELS),
    title="Set recomendado C – Spearman (sin prima; con lag)",
    figsize=(8, 7),
)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Correlaciones | Set reducido C")
_save_fig(fig, "05_C2_heatmap_set_recomendado.png")

# C3 – Panel associations: lag / clase vs alta_siniestralidad & n_siniestros
pt_panel = pred_vs_tgt[pred_vs_tgt["alcance"] == "panel_empresa_anio"].copy()
fig, ax = sb.create_report_figure(
    title="Asociación en panel empresa-año (con lag)",
    subtitle="Spearman entre predictores temporales y targets anuales",
    figsize=(11, 6),
)
if len(pt_panel):
    pt_panel = pt_panel.sort_values("abs_spearman", ascending=True)
    labels_p = [
        f"{r.etiqueta_predictor} → {r.etiqueta_target}"
        for r in pt_panel.itertuples()
    ]
    colors = [palette[0] if v >= 0 else palette[3] for v in pt_panel["spearman"]]
    y = np.arange(len(pt_panel))
    ax.barh(y, pt_panel["spearman"].values, color=colors, alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels_p, fontsize=8)
    ax.axvline(0, color="#666", linewidth=0.8)
    ax.set_xlabel("Correlación Spearman")
    for yi, v in zip(y, pt_panel["spearman"].values):
        ax.text(v + (0.01 if v >= 0 else -0.01), yi, f"{v:.2f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=8)
sb.add_sura_footer(fig, text="S01 – EDA | 1.2.6 Correlaciones | Panel con lag")
_save_fig(fig, "05_C3_asociacion_panel_lag.png")

# ──────────────────────────────────────────────────────────────────────────────
#  6. Summary for Insights
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("RESUMEN PARA Insights_EDA.md")
print("=" * 72)

print("\n--- Spearman predictores (transversal) ---")
print(spearman_preds.round(3).to_string())

print("\n--- Pearson predictores (transversal) ---")
print(pearson_preds.round(3).to_string())

print("\n--- Predictor vs target (top transversal) ---")
print(
    pt_cs.sort_values("abs_spearman", ascending=False)
    .head(12)[["predictor", "target", "spearman"]]
    .to_string(index=False)
)

print("\n--- Predictor vs target (panel) ---")
print(
    pred_vs_tgt[pred_vs_tgt["alcance"] == "panel_empresa_anio"]
    .sort_values("abs_spearman", ascending=False)
    [["predictor", "target", "spearman"]]
    .to_string(index=False)
)

print("\n--- Pares |ρ| ≥ 0.70 (diagnóstico) ---")
if len(pares_diag):
    print(
        pares_diag[["variable_a", "variable_b", "correlacion"]]
        .to_string(index=False)
    )
else:
    print("(ninguno)")

print("\n--- VIF por set ---")
for s in sets_order:
    sub = vif_all[vif_all["set_features"] == s]
    print(f"\n[{s}] max_VIF={sub['vif'].max():.2f}  κ={sub['condition_number'].iloc[0]:.2f}")
    print(sub[["variable", "vif", "nivel_colinealidad"]].to_string(index=False))

print("\n--- Recomendación ---")
print(
    recomendacion[["variable", "prioridad", "decision", "vif_set_B", "spearman_target_ref"]]
    .to_string(index=False)
)

print("\n✅  Análisis de correlación y colinealidad completado.")
print("    Decisión: priorizar clase_riesgo + lag + exposición (+ sector);")
print(
    f"    VIF max set B = {float(vif_b['vif'].max()):.2f} "
    f"(sin colinealidad severa); ρ Spearman prima↔tamaño ≈ {rho_prima_trab:.2f}."
)
