"""
Nowcast 2.3.2 — Random Forest
=============================
Sección: S02 – Nowcast
Ítem: 2.3.2 (modelo ML #1)

Entrena un Random Forest sobre el panel ragged-edge (AT parcial +
indicadores líderes con rezagos de publicación), reporta métricas
train/val/test y produce el nowcast del trimestre forward (2025-T1)
con bandas de incertidumbre vía cuantiles de árboles.

Uso:
    .venv/bin/python \\
      "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/01_random_forest.py"
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import ParameterGrid

import sura_brand as sb

from nowcast_common import (
    FEATURE_COLS,
    FORWARD_PERIOD,
    PALETTE,
    TARGET_COL,
    build_ragged_panel,
    get_xy,
    impute_features,
    metrics_frame,
    plot_pred_vs_actual,
    regression_metrics,
    save_fig,
    save_parquet,
)

warnings.filterwarnings("ignore")
sb.apply_sura_style()

MODEL_NAME = "RandomForest"
RANDOM_SEED = 42


def _predict_interval(model: RandomForestRegressor, X: pd.DataFrame, q_lo=0.1, q_hi=0.9):
    """Quantile band from individual tree predictions."""
    tree_preds = np.column_stack([t.predict(X) for t in model.estimators_])
    point = tree_preds.mean(axis=1)
    lo = np.quantile(tree_preds, q_lo, axis=1)
    hi = np.quantile(tree_preds, q_hi, axis=1)
    return point, lo, hi


def main() -> None:
    print("=" * 70)
    print("🌲  Nowcast 2.3.2 — Random Forest")
    print("=" * 70)

    panel = build_ragged_panel(force=True)

    X_tr, y_tr, meta_tr = get_xy(panel, "train")
    X_va, y_va, meta_va = get_xy(panel, "val")
    X_te, y_te, meta_te = get_xy(panel, "test")
    X_tr, X_va, X_te = impute_features(X_tr, X_va, X_te)

    # Light grid on validation (small-T aware)
    grid = ParameterGrid(
        {
            "n_estimators": [100, 200],
            "max_depth": [2, 3, 4],
            "min_samples_leaf": [2, 3],
        }
    )
    best, best_rmse = None, np.inf
    for params in grid:
        rf = RandomForestRegressor(
            random_state=RANDOM_SEED,
            n_jobs=-1,
            max_features="sqrt",
            **params,
        )
        rf.fit(X_tr, y_tr)
        pred_va = rf.predict(X_va)
        rmse = regression_metrics(y_va.values, pred_va)["rmse"]
        if rmse < best_rmse:
            best_rmse, best = rmse, params

    print(f"   Best params (val RMSE={best_rmse:.4f}): {best}")

    # Refit on train+val for final test / forward
    X_tv = pd.concat([X_tr, X_va], axis=0)
    y_tv = pd.concat([y_tr, y_va], axis=0)
    model = RandomForestRegressor(
        random_state=RANDOM_SEED,
        n_jobs=-1,
        max_features="sqrt",
        **best,
    )
    model.fit(X_tv, y_tv)

    # Also keep a train-only fit for train metrics honesty
    model_tr = RandomForestRegressor(
        random_state=RANDOM_SEED, n_jobs=-1, max_features="sqrt", **best
    )
    model_tr.fit(X_tr, y_tr)

    rows_m = []
    preds_rows = []

    for split_name, X, y, meta, mdl in [
        ("train", X_tr, y_tr, meta_tr, model_tr),
        ("val", X_va, y_va, meta_va, model_tr),
        ("test", X_te, y_te, meta_te, model),
    ]:
        point, lo, hi = _predict_interval(mdl, X)
        m = regression_metrics(y.values, point)
        rows_m.append({"split": split_name, **m})
        for i, idx in enumerate(meta.index):
            preds_rows.append(
                {
                    "modelo": MODEL_NAME,
                    "split": split_name,
                    "periodo": meta.at[idx, "periodo"],
                    "anio": int(meta.at[idx, "anio"]),
                    "q": int(meta.at[idx, "q"]),
                    "y_true": float(y.loc[idx]),
                    "y_pred": float(point[i]),
                    "y_lo80": float(lo[i]),
                    "y_hi80": float(hi[i]),
                }
            )
        print(
            f"   {split_name:5s}  n={m['n']:2d}  MAE={m['mae']:.4f}  "
            f"RMSE={m['rmse']:.4f}  MAPE={m['mape']:.1f}%  R²={m['r2']:.3f}"
        )

    # Forward nowcast 2025-T1
    fa, fq = FORWARD_PERIOD
    fwd = panel.loc[(panel["anio"] == fa) & (panel["q"] == fq)].copy()
    X_fwd = fwd[FEATURE_COLS].copy()
    X_fwd = X_fwd.fillna(X_tv.median(numeric_only=True))
    point_f, lo_f, hi_f = _predict_interval(model, X_fwd)
    fwd_row = {
        "modelo": MODEL_NAME,
        "split": "forward",
        "periodo": fwd["periodo"].iloc[0],
        "anio": fa,
        "q": fq,
        "y_true": np.nan,
        "y_pred": float(point_f[0]),
        "y_lo80": float(lo_f[0]),
        "y_hi80": float(hi_f[0]),
    }
    preds_rows.append(fwd_row)
    print(
        f"\n   🔮 Nowcast {fwd_row['periodo']}: "
        f"{fwd_row['y_pred']:.4f}  [{fwd_row['y_lo80']:.4f}, {fwd_row['y_hi80']:.4f}]"
    )

    metrics_df = metrics_frame(rows_m, MODEL_NAME)
    preds_df = pd.DataFrame(preds_rows)
    imp = (
        pd.DataFrame({"feature": FEATURE_COLS, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    save_parquet(metrics_df, "nowcast_rf_metricas.parquet")
    save_parquet(preds_df, "nowcast_rf_predicciones.parquet")
    save_parquet(imp, "nowcast_rf_importancia.parquet")

    # Plots
    hist = preds_df.loc[preds_df["split"] != "forward"].sort_values(["anio", "q"])
    plot_pred_vs_actual(
        hist["periodo"].tolist(),
        hist["y_true"].values,
        hist["y_pred"].values,
        title="Random Forest — nowcast vs observado (ragged-edge)",
        fname="02_rf_pred_vs_actual.png",
        y_lo=hist["y_lo80"].values,
        y_hi=hist["y_hi80"].values,
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(imp["feature"][::-1], imp["importance"][::-1], color=PALETTE[0])
    ax.set_xlabel("Importancia (MDI)")
    ax.set_title("Random Forest — importancia de features (ragged-edge)")
    fig.tight_layout()
    save_fig(fig, "02_rf_importancia.png")

    # Highlight forward point
    fig, ax = plt.subplots(figsize=(9, 4))
    te = preds_df.loc[preds_df["split"] == "test"]
    ax.errorbar(
        te["periodo"],
        te["y_pred"],
        yerr=[te["y_pred"] - te["y_lo80"], te["y_hi80"] - te["y_pred"]],
        fmt="o",
        color=PALETTE[1],
        label="Test nowcast ±IC80",
        capsize=4,
    )
    ax.scatter(te["periodo"], te["y_true"], color=PALETTE[0], zorder=3, label="Observado")
    ax.errorbar(
        [fwd_row["periodo"]],
        [fwd_row["y_pred"]],
        yerr=[[fwd_row["y_pred"] - fwd_row["y_lo80"]],
              [fwd_row["y_hi80"] - fwd_row["y_pred"]]],
        fmt="D",
        color=PALETTE[2],
        capsize=4,
        label=f"Forward {fwd_row['periodo']}",
    )
    ax.set_ylabel("freq_at × 100")
    ax.set_title("Random Forest — test + nowcast forward con incertidumbre")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    save_fig(fig, "02_rf_forward_uncertainty.png")

    print("\n✅  Random Forest complete.")


if __name__ == "__main__":
    main()
