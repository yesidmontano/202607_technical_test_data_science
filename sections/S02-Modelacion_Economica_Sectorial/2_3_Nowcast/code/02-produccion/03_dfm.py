"""
Nowcast 2.3.2 — Dynamic Factor Model (DFM)
==========================================
Sección: S02 – Nowcast
Ítem: 2.3.2 (modelo econométrico #3)

DFM de 1 factor sobre indicadores líderes (ragged-edge: CEED/IPOC/EC/macro
en lag de publicación), puente a frecuencia AT vía regresión con AT parcial.
Incertidumbre: factor Kalman + residual bootstrap del puente.

Uso:
    .venv/bin/python \\
      "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/03_dfm.py"
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

import sura_brand as sb

from nowcast_common import (
    FEATURE_COLS,
    FORWARD_PERIOD,
    PALETTE,
    TARGET_COL,
    build_ragged_panel,
    metrics_frame,
    plot_pred_vs_actual,
    regression_metrics,
    save_fig,
    save_parquet,
)

warnings.filterwarnings("ignore")
sb.apply_sura_style()

MODEL_NAME = "DFM"
RANDOM_SEED = 42

# Indicators entering the factor (publication-lag aware, no contemporaneous CEED/IPOC)
FACTOR_COLS = [
    "log_ceed_lag1",
    "log_ceed_ma3_lag1",
    "log_ceed_lag4",
    "log_ipoc_lag1",
    "log_ec_parcial",
    "pib_lag1",
    "log_empleo_lag1",
]


def _zscore(X: pd.DataFrame, mu=None, sd=None):
    if mu is None:
        mu = X.mean()
        sd = X.std().replace(0, 1.0)
    return (X - mu) / sd, mu, sd


def extract_factor(Y: pd.DataFrame) -> tuple[np.ndarray, object]:
    """Fit 1-factor DFM; return smoothed factor and result."""
    mod = DynamicFactor(
        Y,
        k_factors=1,
        factor_order=1,
        error_order=0,
    )
    res = mod.fit(disp=False, maxiter=300)
    # factors shape (nobs, k_factors)
    fac = np.asarray(res.factors.smoothed).ravel()
    return fac, res


def bridge_predict(
    factor: np.ndarray,
    at_parcial: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    pred_idx: np.ndarray,
    rng: np.random.Generator,
    n_boot: int = 300,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, object]:
    """OLS bridge: y ~ const + factor + at_parcial; bootstrap intervals."""
    X_fit = add_constant(
        np.column_stack([factor[fit_idx], at_parcial[fit_idx]]), has_constant="add"
    )
    ols = OLS(y[fit_idx], X_fit).fit()

    X_pred = add_constant(
        np.column_stack([factor[pred_idx], at_parcial[pred_idx]]), has_constant="add"
    )
    point = ols.predict(X_pred)

    resid = ols.resid
    boots = []
    for _ in range(n_boot):
        y_star = ols.fittedvalues + rng.choice(resid, size=len(resid), replace=True)
        try:
            b = OLS(y_star, X_fit).fit()
            boots.append(b.predict(X_pred) + rng.choice(resid, size=len(pred_idx)))
        except Exception:
            continue
    B = np.asarray(boots)
    lo = np.quantile(B, 0.1, axis=0)
    hi = np.quantile(B, 0.9, axis=0)
    return np.asarray(point), lo, hi, ols


def main() -> None:
    print("=" * 70)
    print("📊  Nowcast 2.3.2 — Dynamic Factor Model")
    print("=" * 70)

    rng = np.random.default_rng(RANDOM_SEED)
    panel = build_ragged_panel(force=False)

    mod = panel.loc[panel["modelable"]].sort_values(["anio", "q"]).reset_index(drop=True)
    med = mod.loc[mod["split"] == "train", FACTOR_COLS + ["freq_at_parcial_x100"]].median()
    for c in FACTOR_COLS + ["freq_at_parcial_x100"]:
        mod[c] = mod[c].fillna(med[c])

    Y_raw = mod[FACTOR_COLS]
    Y_z, mu, sd = _zscore(Y_raw)

    # Fit DFM on train+val indicators (full history available of lags)
    # Use all modelable rows for factor extraction (indicators known under ragged edge)
    factor_all, res_dfm = extract_factor(Y_z)
    mod["factor1"] = factor_all

    y = mod[TARGET_COL].values.astype(float)
    at_p = mod["freq_at_parcial_x100"].values.astype(float)

    idx_tr = np.where(mod["split"].values == "train")[0]
    idx_va = np.where(mod["split"].values == "val")[0]
    idx_te = np.where(mod["split"].values == "test")[0]
    idx_tv = np.concatenate([idx_tr, idx_va])

    rows_m, preds_rows = [], []

    # Train metrics (bridge fit on train)
    pt, lo, hi, ols_tr = bridge_predict(factor_all, at_p, y, idx_tr, idx_tr, rng)
    m = regression_metrics(y[idx_tr], pt)
    rows_m.append({"split": "train", **m})
    for k, i in enumerate(idx_tr):
        preds_rows.append(_row(mod, i, "train", y[i], pt[k], lo[k], hi[k]))
    print(f"   train  n={m['n']:2d}  MAE={m['mae']:.4f}  RMSE={m['rmse']:.4f}  MAPE={m['mape']:.1f}%")

    # Val
    pt, lo, hi, _ = bridge_predict(factor_all, at_p, y, idx_tr, idx_va, rng)
    m = regression_metrics(y[idx_va], pt)
    rows_m.append({"split": "val", **m})
    for k, i in enumerate(idx_va):
        preds_rows.append(_row(mod, i, "val", y[i], pt[k], lo[k], hi[k]))
    print(f"   val    n={m['n']:2d}  MAE={m['mae']:.4f}  RMSE={m['rmse']:.4f}  MAPE={m['mape']:.1f}%")

    # Test — bridge refit on train+val
    pt, lo, hi, ols_tv = bridge_predict(factor_all, at_p, y, idx_tv, idx_te, rng)
    m = regression_metrics(y[idx_te], pt)
    rows_m.append({"split": "test", **m})
    for k, i in enumerate(idx_te):
        preds_rows.append(_row(mod, i, "test", y[i], pt[k], lo[k], hi[k]))
    print(f"   test   n={m['n']:2d}  MAE={m['mae']:.4f}  RMSE={m['rmse']:.4f}  MAPE={m['mape']:.1f}%")
    print(f"   Bridge (train+val): {ols_tv.summary().tables[1]}")

    # Forward 2025-T1: extend factor with available indicators
    fa, fq = FORWARD_PERIOD
    fwd = panel.loc[(panel["anio"] == fa) & (panel["q"] == fq)].copy()
    for c in FACTOR_COLS + ["freq_at_parcial_x100"]:
        if c not in fwd.columns or fwd[c].isna().all():
            fwd[c] = med.get(c, np.nan)
        else:
            fwd[c] = fwd[c].fillna(med.get(c, fwd[c].median()))

    # Append forward indicators, re-estimate factor on extended panel
    Y_ext = pd.concat(
        [Y_raw, (fwd[FACTOR_COLS] - mu) / sd],
        ignore_index=True,
    )
    # Y_ext last row already z-scored incorrectly above — fix:
    Y_ext = pd.concat([Y_raw, fwd[FACTOR_COLS]], ignore_index=True)
    Y_ext_z = (Y_ext - mu) / sd
    factor_ext, _ = extract_factor(Y_ext_z)
    f_fwd = factor_ext[-1]
    at_fwd = float(fwd["freq_at_parcial_x100"].iloc[0])

    X_fwd = add_constant(np.array([[f_fwd, at_fwd]]), has_constant="add")
    point = float(ols_tv.predict(X_fwd)[0])
    resid = ols_tv.resid
    boots = []
    X_tv = add_constant(
        np.column_stack([factor_all[idx_tv], at_p[idx_tv]]), has_constant="add"
    )
    for _ in range(300):
        y_star = ols_tv.fittedvalues + rng.choice(resid, size=len(resid), replace=True)
        b = OLS(y_star, X_tv).fit()
        boots.append(float(b.predict(X_fwd)[0] + rng.choice(resid)))
    lo_f, hi_f = np.quantile(boots, [0.1, 0.9])

    fwd_row = {
        "modelo": MODEL_NAME,
        "split": "forward",
        "periodo": fwd["periodo"].iloc[0],
        "anio": fa,
        "q": fq,
        "y_true": np.nan,
        "y_pred": point,
        "y_lo80": float(lo_f),
        "y_hi80": float(hi_f),
        "factor1": float(f_fwd),
    }
    preds_rows.append(fwd_row)
    print(
        f"\n   🔮 Nowcast {fwd_row['periodo']}: "
        f"{fwd_row['y_pred']:.4f}  [{fwd_row['y_lo80']:.4f}, {fwd_row['y_hi80']:.4f}]  "
        f"(factor={f_fwd:.3f})"
    )

    metrics_df = metrics_frame(rows_m, MODEL_NAME)
    preds_df = pd.DataFrame(preds_rows)

    # Factor loadings
    loadings = pd.DataFrame(
        {
            "indicator": FACTOR_COLS,
            "loading": np.asarray(res_dfm.params.filter(like="loading")).ravel()[: len(FACTOR_COLS)]
            if hasattr(res_dfm.params, "filter")
            else list(res_dfm.params)[: len(FACTOR_COLS)],
        }
    )
    # Safer extraction of loadings from results
    try:
        lam = np.asarray(res_dfm.factors.filtered)  # noqa: just ensure factors exist
        # params names
        load_vals = []
        for name in res_dfm.param_names:
            if "loading" in name.lower() or name.startswith("loading"):
                load_vals.append(float(res_dfm.params[name]))
        if len(load_vals) >= len(FACTOR_COLS):
            loadings = pd.DataFrame(
                {"indicator": FACTOR_COLS, "loading": load_vals[: len(FACTOR_COLS)]}
            )
        else:
            # approximate via correlation with factor
            loadings = pd.DataFrame(
                {
                    "indicator": FACTOR_COLS,
                    "loading": [
                        float(np.corrcoef(Y_z[c].values, factor_all)[0, 1])
                        for c in FACTOR_COLS
                    ],
                }
            )
    except Exception:
        loadings = pd.DataFrame(
            {
                "indicator": FACTOR_COLS,
                "loading": [
                    float(np.corrcoef(Y_z[c].values, factor_all)[0, 1])
                    for c in FACTOR_COLS
                ],
            }
        )

    factor_df = mod[["periodo", "anio", "q", "split", "factor1", TARGET_COL]].copy()
    factor_df["modelo"] = MODEL_NAME

    save_parquet(metrics_df, "nowcast_dfm_metricas.parquet")
    save_parquet(preds_df, "nowcast_dfm_predicciones.parquet")
    save_parquet(loadings, "nowcast_dfm_loadings.parquet")
    save_parquet(factor_df, "nowcast_dfm_factor.parquet")

    hist = preds_df.loc[preds_df["split"] != "forward"].sort_values(["anio", "q"])
    plot_pred_vs_actual(
        hist["periodo"].tolist(),
        hist["y_true"].values,
        hist["y_pred"].values,
        title="DFM — nowcast vs observado (factor + AT parcial)",
        fname="02_dfm_pred_vs_actual.png",
        y_lo=hist["y_lo80"].values,
        y_hi=hist["y_hi80"].values,
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(mod["periodo"], mod["factor1"], color=PALETTE[0], lw=2, label="Factor 1 (suavizado)")
    ax2 = ax.twinx()
    ax2.plot(mod["periodo"], mod[TARGET_COL], color=PALETTE[1], ls="--", label="freq_at")
    ax.set_title("DFM — factor latente del ciclo vs frecuencia AT")
    ax.set_ylabel("Factor")
    ax2.set_ylabel("freq_at × 100")
    plt.xticks(rotation=45, ha="right")
    lines1, lab1 = ax.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lab1 + lab2, loc="best")
    fig.tight_layout()
    save_fig(fig, "02_dfm_factor.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(loadings["indicator"][::-1], loadings["loading"][::-1], color=PALETTE[2])
    ax.set_xlabel("Carga / correlación con factor")
    ax.set_title("DFM — contribución de indicadores (ragged-edge)")
    fig.tight_layout()
    save_fig(fig, "02_dfm_loadings.png")

    fig, ax = plt.subplots(figsize=(9, 4))
    te = preds_df.loc[preds_df["split"] == "test"]
    ax.errorbar(
        te["periodo"], te["y_pred"],
        yerr=[te["y_pred"] - te["y_lo80"], te["y_hi80"] - te["y_pred"]],
        fmt="o", color=PALETTE[1], capsize=4, label="Test ±IC80",
    )
    ax.scatter(te["periodo"], te["y_true"], color=PALETTE[0], zorder=3, label="Observado")
    ax.errorbar(
        [fwd_row["periodo"]], [fwd_row["y_pred"]],
        yerr=[[fwd_row["y_pred"] - fwd_row["y_lo80"]],
              [fwd_row["y_hi80"] - fwd_row["y_pred"]]],
        fmt="D", color=PALETTE[2], capsize=4, label=f"Forward {fwd_row['periodo']}",
    )
    ax.set_ylabel("freq_at × 100")
    ax.set_title("DFM — test + nowcast forward con incertidumbre")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    save_fig(fig, "02_dfm_forward_uncertainty.png")

    print("\n✅  DFM complete.")


def _row(mod, i, split, y_true, y_pred, lo, hi):
    return {
        "modelo": MODEL_NAME,
        "split": split,
        "periodo": mod.iloc[i]["periodo"],
        "anio": int(mod.iloc[i]["anio"]),
        "q": int(mod.iloc[i]["q"]),
        "y_true": float(y_true),
        "y_pred": float(y_pred),
        "y_lo80": float(lo),
        "y_hi80": float(hi),
    }


if __name__ == "__main__":
    main()
