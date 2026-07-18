"""
Nowcast 2.3.2 — Comparativo RF / BSTS / DFM
===========================================
Consolida métricas, predicciones y nowcast forward; genera figuras
comparativas y staging agregado.

Uso:
    .venv/bin/python \\
      "sections/S02-Modelacion_Economica_Sectorial/2_3_Nowcast/code/02-produccion/04_comparativo.py"
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sura_brand as sb

from nowcast_common import DATA_S02, PALETTE, save_fig, save_parquet

sb.apply_sura_style()


def main() -> None:
    print("=" * 70)
    print("📑  Nowcast 2.3.2 — Comparativo de modelos")
    print("=" * 70)

    metrics = pd.concat(
        [
            pd.read_parquet(DATA_S02 / "nowcast_rf_metricas.parquet"),
            pd.read_parquet(DATA_S02 / "nowcast_bsts_metricas.parquet"),
            pd.read_parquet(DATA_S02 / "nowcast_dfm_metricas.parquet"),
        ],
        ignore_index=True,
    )
    preds = pd.concat(
        [
            pd.read_parquet(DATA_S02 / "nowcast_rf_predicciones.parquet"),
            pd.read_parquet(DATA_S02 / "nowcast_bsts_predicciones.parquet"),
            pd.read_parquet(DATA_S02 / "nowcast_dfm_predicciones.parquet"),
        ],
        ignore_index=True,
    )

    save_parquet(metrics, "nowcast_comparativo_metricas.parquet")
    save_parquet(preds, "nowcast_comparativo_predicciones.parquet")

    forward = preds.loc[preds["split"] == "forward"].copy()
    save_parquet(forward, "nowcast_forward_2025T1.parquet")

    # Ranking by test RMSE
    test = metrics.loc[metrics["split"] == "test"].sort_values("rmse")
    print("\n   Ranking test (RMSE):")
    for _, r in test.iterrows():
        print(
            f"     {r['modelo']:12s}  RMSE={r['rmse']:.4f}  "
            f"MAE={r['mae']:.4f}  MAPE={r['mape']:.1f}%"
        )
    best = test.iloc[0]["modelo"]
    print(f"\n   ★ Mejor en test: {best}")

    # Metrics bars
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    for ax, metric, label in zip(
        axes, ["mae", "rmse", "mape"], ["MAE", "RMSE", "MAPE (%)"]
    ):
        sub = metrics.pivot(index="split", columns="modelo", values=metric)
        sub = sub.reindex(["train", "val", "test"])
        sub.plot(kind="bar", ax=ax, color=PALETTE[:3], rot=0)
        ax.set_title(label)
        ax.set_xlabel("")
        ax.legend(fontsize=7)
    fig.suptitle("Comparativo nowcast — métricas por split", y=1.02)
    fig.tight_layout()
    save_fig(fig, "02_comparativo_metricas.png")

    # Forward fan chart
    fig, ax = plt.subplots(figsize=(8, 4.5))
    models = forward["modelo"].tolist()
    x = np.arange(len(models))
    ax.bar(
        x,
        forward["y_pred"],
        color=PALETTE[: len(models)],
        alpha=0.85,
        label="Punto nowcast",
    )
    ax.errorbar(
        x,
        forward["y_pred"],
        yerr=[
            forward["y_pred"] - forward["y_lo80"],
            forward["y_hi80"] - forward["y_pred"],
        ],
        fmt="none",
        ecolor="black",
        capsize=5,
        label="IC 80%",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylabel("freq_at × 100")
    ax.set_title("Nowcast forward 2025-T1 — punto e incertidumbre por modelo")
    ax.legend()
    fig.tight_layout()
    save_fig(fig, "02_comparativo_forward.png")

    # Test overlay
    fig, ax = plt.subplots(figsize=(10, 4.5))
    te = preds.loc[preds["split"] == "test"].copy()
    periods = sorted(te["periodo"].unique())
    for i, modelo in enumerate(["RandomForest", "BSTS", "DFM"]):
        sub = te.loc[te["modelo"] == modelo].set_index("periodo").reindex(periods)
        ax.plot(
            periods,
            sub["y_pred"],
            "o--",
            color=PALETTE[i],
            label=modelo,
            lw=1.8,
        )
    y_true = (
        te.loc[te["modelo"] == "DFM"]
        .set_index("periodo")
        .reindex(periods)["y_true"]
    )
    ax.plot(periods, y_true, "s-", color="black", label="Observado", lw=2)
    ax.set_ylabel("freq_at × 100")
    ax.set_title("Test 2024 — nowcasts vs observado")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    save_fig(fig, "02_comparativo_test.png")

    # Summary table for docs
    summary = test[["modelo", "n", "mae", "rmse", "mape", "r2"]].copy()
    summary["rank_rmse"] = range(1, len(summary) + 1)
    fwd_wide = forward[["modelo", "y_pred", "y_lo80", "y_hi80"]].rename(
        columns={
            "y_pred": "nowcast_2025T1",
            "y_lo80": "lo80",
            "y_hi80": "hi80",
        }
    )
    summary = summary.merge(fwd_wide, on="modelo", how="left")
    save_parquet(summary, "nowcast_resumen_final.parquet")
    print("\n✅  Comparativo complete.")


if __name__ == "__main__":
    main()
