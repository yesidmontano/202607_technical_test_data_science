"""
Nowcast 2.3.2 — Bayesian Structural Time Series (BSTS)
======================================================
Sección: S02 – Nowcast
Ítem: 2.3.2 (modelo econométrico #2)

BSTS ligero alineado al estado del arte:
  · Nivel local + estacionalidad trimestral (UnobservedComponents)
  · Regresión spike-and-slab: promedia modelos UC+exog según PIP
  · Intervalos a partir de draws posteriores / residuos

Uso:
    .venv/bin/python \\
      "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/02_bsts.py"
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.structural import UnobservedComponents

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

MODEL_NAME = "BSTS"
RANDOM_SEED = 42
N_GIBBS = 500
BURN_IN = 150
TOP_K = 4  # max regressors under small-T


def _standardize(X: np.ndarray, mu=None, sd=None):
    if mu is None:
        mu = np.nanmean(X, axis=0)
        sd = np.nanstd(X, axis=0)
        sd = np.where(sd < 1e-8, 1.0, sd)
    return (X - mu) / sd, mu, sd


def spike_slab_pip(
    y: np.ndarray,
    X: np.ndarray,
    n_iter: int = N_GIBBS,
    burn: int = BURN_IN,
    pi: float = 0.35,
    seed: int = RANDOM_SEED,
) -> np.ndarray:
    """Gibbs spike-and-slab → posterior inclusion probabilities."""
    rng = np.random.default_rng(seed)
    n, p = X.shape
    gamma = rng.binomial(1, pi, size=p).astype(float)
    beta = np.zeros(p)
    sigma2 = float(np.var(y)) if np.var(y) > 0 else 1.0
    tau2 = 2.0
    hist = []

    for it in range(n_iter):
        for j in range(p):
            g_wo = gamma.copy()
            g_wo[j] = 0
            active = g_wo.astype(bool)
            resid = y - X[:, active] @ beta[active] if active.any() else y.copy()
            xj = X[:, j]
            xtx = float(xj @ xj) + 1e-8
            post_prec = xtx / sigma2 + 1.0 / tau2
            post_mean = (xj @ resid / sigma2) / post_prec
            log_ml_in = (
                0.5 * np.log(1.0 / tau2)
                - 0.5 * np.log(post_prec)
                + 0.5 * post_prec * post_mean**2
            )
            log_odds = np.log(pi / (1 - pi)) + log_ml_in
            prob = 1.0 / (1.0 + np.exp(-np.clip(log_odds, -30, 30)))
            gamma[j] = float(rng.random() < prob)

        active = gamma.astype(bool)
        beta[:] = 0.0
        if active.any():
            Xa = X[:, active]
            XtX = Xa.T @ Xa + np.eye(active.sum()) * (sigma2 / tau2)
            try:
                cov = np.linalg.inv(XtX)
            except np.linalg.LinAlgError:
                cov = np.linalg.pinv(XtX)
            mean = cov @ (Xa.T @ y)
            beta[active] = rng.multivariate_normal(
                mean, sigma2 * cov + 1e-10 * np.eye(len(mean))
            )

        resid = y - X @ beta
        a_post = 2.0 + n / 2
        b_post = 1.0 + 0.5 * float(resid @ resid)
        sigma2 = 1.0 / rng.gamma(a_post, 1.0 / b_post)
        if it >= burn:
            hist.append(gamma.copy())

    return np.asarray(hist).mean(axis=0)


def fit_uc(y: np.ndarray, exog: np.ndarray | None = None):
    # Small-T: local level + regression; seasonal dummies already in features (q_sin/q_cos)
    kwargs = dict(level="local level", stochastic_level=True)
    if exog is not None and exog.size and exog.shape[1] > 0:
        mod = UnobservedComponents(y, exog=exog, **kwargs)
    else:
        mod = UnobservedComponents(y, **kwargs)
    return mod.fit(disp=False, maxiter=250)


def predict_uc(res, exog_future: np.ndarray | None, steps: int):
    if exog_future is not None and exog_future.size and exog_future.ndim == 1:
        exog_future = exog_future.reshape(1, -1)
    if exog_future is not None and exog_future.size:
        fc = res.get_forecast(steps=steps, exog=exog_future)
    else:
        fc = res.get_forecast(steps=steps)
    mean = np.asarray(fc.predicted_mean)
    # Approximate 80% PI from SE
    se = np.asarray(fc.se_mean)
    z = 1.28
    return mean, mean - z * se, mean + z * se


def main() -> None:
    print("=" * 70)
    print("📈  Nowcast 2.3.2 — BSTS (UC + spike-and-slab)")
    print("=" * 70)

    rng = np.random.default_rng(RANDOM_SEED)
    panel = build_ragged_panel(force=False)

    mod = panel.loc[panel["modelable"]].sort_values(["anio", "q"]).reset_index(drop=True)
    X_raw = mod[FEATURE_COLS].copy()
    med = X_raw.loc[mod["split"] == "train"].median()
    X_all = X_raw.fillna(med)
    y_all = mod[TARGET_COL].values.astype(float)
    X_std, mu, sd = _standardize(X_all.values)

    idx_tr = np.where(mod["split"].values == "train")[0]
    idx_va = np.where(mod["split"].values == "val")[0]
    idx_te = np.where(mod["split"].values == "test")[0]
    idx_tv = np.concatenate([idx_tr, idx_va])

    # Spike-slab on train (detrended residual vs features) for selection
    res0 = fit_uc(y_all[idx_tr], None)
    resid_tr = y_all[idx_tr] - np.asarray(res0.fittedvalues)
    pip = spike_slab_pip(resid_tr, X_std[idx_tr])
    top = np.argsort(-pip)[:TOP_K]
    # Keep features with PIP above median of top-k; always keep AT parcial
    cols_sel = list(top[pip[top] >= max(0.15, np.median(pip[top]))])
    if len(cols_sel) == 0:
        cols_sel = list(top[:3])
    # Mandatory: partial claims (ragged-edge information set)
    j_parcial = FEATURE_COLS.index("freq_at_parcial_x100")
    if j_parcial not in cols_sel:
        cols_sel = [j_parcial] + cols_sel
    cols_sel = np.array(cols_sel[: TOP_K + 1], dtype=int)

    print("   PIP (selección):")
    for j in np.argsort(-pip):
        mark = "✓" if j in cols_sel else " "
        print(f"     [{mark}] {FEATURE_COLS[j]:22s}  PIP={pip[j]:.2f}")

    sel_names = [FEATURE_COLS[j] for j in cols_sel]

    # Fit final UC+exog on train and train+val
    res_tr = fit_uc(y_all[idx_tr], X_std[idx_tr][:, cols_sel])
    res_tv = fit_uc(y_all[idx_tv], X_std[idx_tv][:, cols_sel])

    rows_m, preds_rows = [], []

    def block_fitted(res, indices, split):
        fitted = np.asarray(res.fittedvalues)
        resid = y_all[indices] - fitted if len(fitted) == len(indices) else None
        # residual bootstrap IC
        if resid is None:
            point = fitted
            lo = point - 0.1
            hi = point + 0.1
        else:
            boots = np.asarray(
                [fitted + rng.choice(resid, size=len(fitted), replace=True) for _ in range(200)]
            )
            point = fitted
            lo = np.quantile(boots, 0.1, axis=0)
            hi = np.quantile(boots, 0.9, axis=0)
        m = regression_metrics(y_all[indices], point)
        rows_m.append({"split": split, **m})
        for k, i in enumerate(indices):
            preds_rows.append(
                {
                    "modelo": MODEL_NAME,
                    "split": split,
                    "periodo": mod.iloc[i]["periodo"],
                    "anio": int(mod.iloc[i]["anio"]),
                    "q": int(mod.iloc[i]["q"]),
                    "y_true": float(y_all[i]),
                    "y_pred": float(point[k]),
                    "y_lo80": float(lo[k]),
                    "y_hi80": float(hi[k]),
                }
            )
        print(
            f"   {split:5s}  n={m['n']:2d}  MAE={m['mae']:.4f}  "
            f"RMSE={m['rmse']:.4f}  MAPE={m['mape']:.1f}%"
        )

    def block_forecast(res, fit_idx, pred_idx, split):
        steps = len(pred_idx)
        exog_f = X_std[pred_idx][:, cols_sel]
        point, lo, hi = predict_uc(res, exog_f, steps)
        # Widen with residual scale from fit
        fit_resid = y_all[fit_idx] - np.asarray(res.fittedvalues)
        scale = float(np.std(fit_resid)) if len(fit_resid) else 0.1
        lo = point - 1.28 * np.sqrt((point - lo) ** 2 + scale**2)
        hi = point + 1.28 * np.sqrt((hi - point) ** 2 + scale**2)
        m = regression_metrics(y_all[pred_idx], point)
        rows_m.append({"split": split, **m})
        for k, i in enumerate(pred_idx):
            preds_rows.append(
                {
                    "modelo": MODEL_NAME,
                    "split": split,
                    "periodo": mod.iloc[i]["periodo"],
                    "anio": int(mod.iloc[i]["anio"]),
                    "q": int(mod.iloc[i]["q"]),
                    "y_true": float(y_all[i]),
                    "y_pred": float(point[k]),
                    "y_lo80": float(lo[k]),
                    "y_hi80": float(hi[k]),
                }
            )
        print(
            f"   {split:5s}  n={m['n']:2d}  MAE={m['mae']:.4f}  "
            f"RMSE={m['rmse']:.4f}  MAPE={m['mape']:.1f}%"
        )

    block_fitted(res_tr, idx_tr, "train")
    block_forecast(res_tr, idx_tr, idx_va, "val")
    block_forecast(res_tv, idx_tv, idx_te, "test")

    # Forward
    fa, fq = FORWARD_PERIOD
    fwd = panel.loc[(panel["anio"] == fa) & (panel["q"] == fq)]
    X_fwd = fwd[FEATURE_COLS].fillna(med).values
    X_fwd_std = (X_fwd - mu) / sd
    point, lo, hi = predict_uc(res_tv, X_fwd_std[:, cols_sel], 1)
    fit_resid = y_all[idx_tv] - np.asarray(res_tv.fittedvalues)
    scale = float(np.std(fit_resid))
    lo = point - 1.28 * np.sqrt((point - lo) ** 2 + scale**2)
    hi = point + 1.28 * np.sqrt((hi - point) ** 2 + scale**2)

    fwd_row = {
        "modelo": MODEL_NAME,
        "split": "forward",
        "periodo": fwd["periodo"].iloc[0],
        "anio": fa,
        "q": fq,
        "y_true": np.nan,
        "y_pred": float(point[0]),
        "y_lo80": float(lo[0]),
        "y_hi80": float(hi[0]),
    }
    preds_rows.append(fwd_row)
    print(
        f"\n   🔮 Nowcast {fwd_row['periodo']}: "
        f"{fwd_row['y_pred']:.4f}  [{fwd_row['y_lo80']:.4f}, {fwd_row['y_hi80']:.4f}]"
    )
    print(f"   Regressors: {sel_names}")

    metrics_df = metrics_frame(rows_m, MODEL_NAME)
    preds_df = pd.DataFrame(preds_rows)
    pip_df = pd.DataFrame(
        {
            "feature": FEATURE_COLS,
            "pip": pip,
            "selected": [j in cols_sel for j in range(len(FEATURE_COLS))],
        }
    ).sort_values("pip", ascending=False)

    save_parquet(metrics_df, "nowcast_bsts_metricas.parquet")
    save_parquet(preds_df, "nowcast_bsts_predicciones.parquet")
    save_parquet(pip_df, "nowcast_bsts_pip.parquet")

    hist = preds_df.loc[preds_df["split"] != "forward"].sort_values(["anio", "q"])
    plot_pred_vs_actual(
        hist["periodo"].tolist(),
        hist["y_true"].values,
        hist["y_pred"].values,
        title="BSTS — nowcast vs observado (UC + spike-and-slab)",
        fname="02_bsts_pred_vs_actual.png",
        y_lo=hist["y_lo80"].values,
        y_hi=hist["y_hi80"].values,
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = [PALETTE[1] if s else PALETTE[3] for s in pip_df["selected"]]
    ax.barh(pip_df["feature"][::-1], pip_df["pip"][::-1], color=colors[::-1])
    ax.set_xlabel("Probabilidad de inclusión posterior (PIP)")
    ax.set_title("BSTS — spike-and-slab (selección de indicadores)")
    fig.tight_layout()
    save_fig(fig, "02_bsts_pip.png")

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
    ax.set_title("BSTS — test + nowcast forward con incertidumbre")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    save_fig(fig, "02_bsts_forward_uncertainty.png")

    print("\n✅  BSTS complete.")


if __name__ == "__main__":
    main()
