"""
Shared utilities for S02–2.3.2 nowcast production
=================================================
Builds the ragged-edge feature panel (publication lags + partial AT),
train/val/test splits, metrics, and I/O helpers reused by RF / BSTS / DFM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sura_brand as sb

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
DATA_RAW = ROOT / "data" / "raw"
DATA_S01 = ROOT / "data" / "staging" / "S01"
DATA_S02 = ROOT / "data" / "staging" / "S02"
RESULTS_IMGS = (
    ROOT
    / "sections"
    / "S02-Modelacion_Economica_Sectorial"
    / "2_3_Nowcast"
    / "results"
    / "imgs"
)

DATA_S02.mkdir(parents=True, exist_ok=True)
RESULTS_IMGS.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()
PALETTE = sb.get_palette("categorical")

# Vintage assumption: ~day 40 of quarter T (EC month-1 just published; CEED_T not yet)
# → partial AT = first month of the quarter; cycle indicators use lag-1 (published).
FEATURE_COLS = [
    "freq_at_parcial_x100",
    "freq_at_lag1",
    "log_ceed_lag1",
    "log_ceed_ma3_lag1",
    "log_ceed_lag4",
    "log_ipoc_lag1",
    "log_ec_parcial",
    "pib_lag1",
    "log_empleo_lag1",
    "q_sin",
    "q_cos",
]

TARGET_COL = "freq_at_x100"

# Temporal splits on modeling window 2020-III → 2024-IV
TRAIN_END = (2023, 2)   # inclusive
VAL_END = (2023, 4)     # inclusive; test = 2024-I → 2024-IV
FORWARD_PERIOD = (2025, 1)

# Publication-lag metadata (days) — from caracterizacion.md §2.1.4
PUB_LAGS = {
    "EC": 38,
    "ELIC": 45,
    "CEED": 45,
    "IPOC": 48,
    "AT_parcial": 0,  # internal accrual
}


def period_label(anio: int, q: int) -> str:
    return f"{anio}-T{q}"


def save_fig(fig: plt.Figure, name: str) -> Path:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")
    return path


def save_parquet(df: pd.DataFrame, name: str) -> Path:
    path = DATA_S02 / name
    df.to_parquet(path, index=False)
    print(f"   📦  {name}  shape={df.shape}")
    return path


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true, y_pred = y_true[mask], y_pred[mask]
    if len(y_true) == 0:
        return {"n": 0, "mae": np.nan, "rmse": np.nan, "mape": np.nan, "r2": np.nan}
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mape = float(np.mean(np.abs(err) / np.maximum(np.abs(y_true), 1e-8)) * 100)
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan
    return {"n": int(len(y_true)), "mae": mae, "rmse": rmse, "mape": mape, "r2": r2}


def assign_split(anio: int, q: int) -> str:
    if (anio, q) <= TRAIN_END:
        return "train"
    if (anio, q) <= VAL_END:
        return "val"
    if anio == 2024:
        return "test"
    return "forward"


def _build_at_monthly(ids: set) -> pd.DataFrame:
    sin = pd.read_parquet(DATA_S01 / "siniestros_imputados.parquet")
    at = sin[(sin["id_empresa"].isin(ids)) & (sin["tipo"] == "AT")].copy()
    at["fecha"] = pd.to_datetime(at["fecha_ocurrencia"])
    at["anio"] = at["fecha"].dt.year
    at["q"] = at["fecha"].dt.quarter
    at["mes_en_q"] = ((at["fecha"].dt.month - 1) % 3) + 1
    return (
        at.groupby(["anio", "q", "mes_en_q"], as_index=False)
        .size()
        .rename(columns={"size": "n_at"})
    )


def _ec_month1_by_quarter(ec: pd.DataFrame) -> pd.DataFrame:
    """First calendar month of each quarter (bridge available ~day 38)."""
    ec = ec.copy()
    ec["q"] = ((ec["mes"] - 1) // 3) + 1
    ec["mes_en_q"] = ((ec["mes"] - 1) % 3) + 1
    m1 = ec.loc[ec["mes_en_q"] == 1, ["anio", "q", "m3_premezclado"]].copy()
    m1 = m1.rename(columns={"m3_premezclado": "ec_m3_mes1"})
    return m1


def build_ragged_panel(force: bool = False) -> pd.DataFrame:
    """
    Construct nowcast panel with explicit publication lags.

    Information set at vintage ≈ day 40 of quarter T:
      · AT partial  = claims in month 1 of T
      · EC partial   = EC of month 1 of T (pub lag ~38d)
      · CEED / IPOC / macro = lag-1 (current quarter not published yet)
      · Memory      = CEED MA3 and lag-4 (~12m; proxy for CCF k=6 channel)
    """
    out_path = DATA_S02 / "nowcast_panel_ragged.parquet"
    if out_path.exists() and not force:
        print("📂  Loading existing nowcast_panel_ragged.parquet")
        return pd.read_parquet(out_path)

    print("🔧  Building ragged-edge nowcast panel...")

    empresas = pd.read_csv(DATA_RAW / "empresas.csv")
    te = pd.read_parquet(DATA_S01 / "temporal_empresa_anio.parquet")
    ids = set(empresas.loc[empresas["sector"] == "Construccion", "id_empresa"]) | set(
        te.loc[te["sector"] == "Construccion", "id_empresa"]
    )

    at_q = pd.read_parquet(DATA_S02 / "at_construccion_trimestral.parquet")
    fuentes = pd.read_parquet(DATA_S02 / "panel_fuentes_trimestral.parquet")
    ciclo = pd.read_parquet(DATA_S02 / "panel_ciclo_at_trimestral.parquet")
    ec = pd.read_parquet(DATA_S02 / "ec_staging.parquet")

    at_m = _build_at_monthly(ids)
    at_m1 = (
        at_m.loc[at_m["mes_en_q"] == 1, ["anio", "q", "n_at"]]
        .rename(columns={"n_at": "n_at_parcial"})
    )
    ec_m1 = _ec_month1_by_quarter(ec)

    # Base: all quarters present in fuentes ∪ AT (allows forward rows)
    keys = (
        pd.concat(
            [
                fuentes[["anio", "q"]],
                at_q[["anio", "q"]],
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .sort_values(["anio", "q"])
        .reset_index(drop=True)
    )

    panel = (
        keys.merge(at_q[["anio", "q", "n_at", "n_trabajadores_sector", "freq_at_x100"]],
                   on=["anio", "q"], how="left")
        .merge(at_m1, on=["anio", "q"], how="left")
        .merge(
            fuentes[["anio", "q", "proceso_nueva_m2", "area_censada_m2",
                     "ipoc_total", "ec_m3_promedio_trim"]],
            on=["anio", "q"],
            how="left",
        )
        .merge(ec_m1, on=["anio", "q"], how="left")
        .merge(
            ciclo[["anio", "q", "pib_sectorial_var", "empleo_sectorial",
                   "ipp_sectorial", "tasa_informalidad"]],
            on=["anio", "q"],
            how="left",
        )
        .sort_values(["anio", "q"])
        .reset_index(drop=True)
    )

    # Carry exposure forward for forward quarters
    panel["n_trabajadores_sector"] = panel["n_trabajadores_sector"].ffill()

    panel["freq_at_parcial_x100"] = (
        panel["n_at_parcial"] / panel["n_trabajadores_sector"] * 100
    )

    # Lagged / published indicators (ragged edge)
    for col, new in [
        ("freq_at_x100", "freq_at_lag1"),
        ("proceso_nueva_m2", "ceed_lag1"),
        ("ipoc_total", "ipoc_lag1"),
        ("pib_sectorial_var", "pib_lag1"),
        ("empleo_sectorial", "empleo_lag1"),
    ]:
        panel[new] = panel[col].shift(1)

    panel["ceed_ma3"] = panel["proceso_nueva_m2"].rolling(3, min_periods=1).mean()
    panel["ceed_ma3_lag1"] = panel["ceed_ma3"].shift(1)
    panel["ceed_lag4"] = panel["proceso_nueva_m2"].shift(4)

    panel["log_ceed_lag1"] = np.log(panel["ceed_lag1"].clip(lower=1))
    panel["log_ceed_ma3_lag1"] = np.log(panel["ceed_ma3_lag1"].clip(lower=1))
    panel["log_ceed_lag4"] = np.log(panel["ceed_lag4"].clip(lower=1))
    panel["log_ipoc_lag1"] = np.log(panel["ipoc_lag1"].clip(lower=1e-6))
    panel["log_ec_parcial"] = np.log(panel["ec_m3_mes1"].clip(lower=1))
    panel["log_empleo_lag1"] = np.log(panel["empleo_lag1"].clip(lower=1))

    # Seasonal encoding (quarter)
    panel["q_sin"] = np.sin(2 * np.pi * panel["q"] / 4)
    panel["q_cos"] = np.cos(2 * np.pi * panel["q"] / 4)

    panel["periodo"] = panel.apply(
        lambda r: period_label(int(r["anio"]), int(r["q"])), axis=1
    )
    panel["fecha"] = pd.to_datetime(
        panel["anio"].astype(str)
        + "-"
        + (panel["q"] * 3).astype(str).str.zfill(2)
        + "-01"
    )
    panel["split"] = panel.apply(
        lambda r: assign_split(int(r["anio"]), int(r["q"])), axis=1
    )

    # Modeling rows: need target + core features (CEED available from 2020-III)
    panel["modelable"] = (
        panel[TARGET_COL].notna()
        & panel["freq_at_parcial_x100"].notna()
        & panel["log_ceed_lag1"].notna()
        & panel["log_ipoc_lag1"].notna()
        & panel["freq_at_lag1"].notna()
    )

    # Forward row: first quarter without AT target but with leading indicators
    fa, fq = FORWARD_PERIOD
    fwd_mask = (panel["anio"] == fa) & (panel["q"] == fq)
    if fwd_mask.any():
        # If AT partial missing, use historical month-1 share × lag1 AT
        share_m1 = float(
            (
                panel.loc[panel["modelable"], "freq_at_parcial_x100"]
                / panel.loc[panel["modelable"], TARGET_COL]
            ).median()
        )
        idx = panel.index[fwd_mask][0]
        if pd.isna(panel.at[idx, "freq_at_parcial_x100"]) and pd.notna(
            panel.at[idx, "freq_at_lag1"]
        ):
            panel.at[idx, "freq_at_parcial_x100"] = (
                share_m1 * float(panel.at[idx, "freq_at_lag1"])
            )
            panel.at[idx, "n_at_parcial"] = (
                panel.at[idx, "freq_at_parcial_x100"]
                * panel.at[idx, "n_trabajadores_sector"]
                / 100
            )
        # Fill log_ec if month-1 missing but trim mean exists
        if pd.isna(panel.at[idx, "log_ec_parcial"]) and pd.notna(
            panel.at[idx, "ec_m3_promedio_trim"]
        ):
            panel.at[idx, "ec_m3_mes1"] = panel.at[idx, "ec_m3_promedio_trim"]
            panel.at[idx, "log_ec_parcial"] = np.log(
                max(float(panel.at[idx, "ec_m3_mes1"]), 1.0)
            )

    panel["pub_lag_ec_dias"] = PUB_LAGS["EC"]
    panel["pub_lag_ceed_dias"] = PUB_LAGS["CEED"]
    panel["pub_lag_ipoc_dias"] = PUB_LAGS["IPOC"]
    panel["vintage_nota"] = (
        "Info set ≈ día 40 de T: AT mes1 + EC mes1; CEED/IPOC/macro en lag-1"
    )

    save_parquet(panel, "nowcast_panel_ragged.parquet")

    n_mod = int(panel["modelable"].sum())
    print(
        f"   Modelable quarters: {n_mod} | "
        f"splits train/val/test="
        f"{(panel.loc[panel['modelable'], 'split'] == 'train').sum()}/"
        f"{(panel.loc[panel['modelable'], 'split'] == 'val').sum()}/"
        f"{(panel.loc[panel['modelable'], 'split'] == 'test').sum()}"
    )
    return panel


def get_xy(
    panel: pd.DataFrame,
    split: str | Iterable[str],
    feature_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    feature_cols = feature_cols or FEATURE_COLS
    splits = {split} if isinstance(split, str) else set(split)
    sub = panel.loc[panel["modelable"] & panel["split"].isin(splits)].copy()
    # Impute rare NaNs in optional features (EC / lag4) with train median later
    X = sub[feature_cols].copy()
    y = sub[TARGET_COL].copy()
    return X, y, sub


def impute_features(
    X_train: pd.DataFrame,
    *others: pd.DataFrame,
) -> tuple[pd.DataFrame, ...]:
    med = X_train.median(numeric_only=True)
    out = [X_train.fillna(med)]
    for X in others:
        out.append(X.fillna(med))
    return tuple(out)


def metrics_frame(rows: list[dict], model: str) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df.insert(0, "modelo", model)
    return df


def plot_pred_vs_actual(
    periods: list[str],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    title: str,
    fname: str,
    y_lo: np.ndarray | None = None,
    y_hi: np.ndarray | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(periods))
    ax.plot(x, y_true, "o-", color=PALETTE[0], label="Observado", lw=2)
    ax.plot(x, y_pred, "s--", color=PALETTE[1], label="Nowcast", lw=2)
    if y_lo is not None and y_hi is not None:
        ax.fill_between(x, y_lo, y_hi, color=PALETTE[1], alpha=0.2, label="IC 80%")
    ax.set_xticks(x)
    ax.set_xticklabels(periods, rotation=45, ha="right")
    ax.set_ylabel("freq_at × 100")
    ax.set_title(title)
    ax.legend(loc="best")
    fig.tight_layout()
    save_fig(fig, fname)


def plot_metrics_bars(metrics_df: pd.DataFrame, title: str, fname: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    for ax, metric, label in zip(
        axes, ["mae", "rmse", "mape"], ["MAE", "RMSE", "MAPE (%)"]
    ):
        sub = metrics_df.pivot(index="split", columns="modelo", values=metric)
        sub = sub.reindex(["train", "val", "test"])
        sub.plot(kind="bar", ax=ax, color=PALETTE[: sub.shape[1]], rot=0)
        ax.set_title(label)
        ax.set_xlabel("")
        ax.legend(fontsize=8)
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    save_fig(fig, fname)
