"""
Modelamiento dinámico ciclo construcción ↔ frecuencia AT
=========================================================
Sección: S02 – Modelación Económica Sectorial
Subsección: 2.2 – Modelamiento de relaciones (ítem 2.2.1)

Descripción:
    Construye la frecuencia trimestral de accidentes de trabajo (AT) del
    sector Construcción, alinea DANE (CEED/EC/IPOC) + macro sintético, y
    modela la relación dinámica vía:
    · Tests ADF / KPSS (orden de integración)
    · Cointegración Engle-Granger / Johansen
    · Selección VAR/VECM vs OLS / ADL
    · AIC/BIC/HQ para el orden p (hasta 4)
    · IRF ortogonalizadas y FEVD (h=4, 8)
    · Diagnósticos de residuos + bloque auxiliar IPOC

    Universo de empresas: sector Construcción en empresas.csv /
    temporal_empresa_anio. Agregación trimestral de AT desde
    siniestros_imputados (fechas); totales anuales se validan contra
    temporal_empresa_anio.

Inputs:
    - data/staging/S02/panel_fuentes_trimestral.parquet
    - data/raw/macro_sectorial.csv
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S01/siniestros_imputados.parquet
    - data/raw/empresas.csv

Outputs:
    - data/staging/S02/at_construccion_trimestral.parquet
    - data/staging/S02/panel_ciclo_at_trimestral.parquet
    - data/staging/S02/estacionariedad_tests.parquet
    - data/staging/S02/var_lag_selection.parquet
    - data/staging/S02/var_irf_fevd.parquet
    - data/staging/S02/var_diagnosticos.parquet
    - sections/.../2_2_.../results/imgs/01_*.png

Uso:
    .venv/bin/python \\
      "sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/code/01-modelamiento/modelamiento_relaciones.py"
"""

from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

from statsmodels.tsa.stattools import adfuller, kpss, coint
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen, select_order as vecm_select_order
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.stats.stattools import jarque_bera

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────────────────────────────────────
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
    / "2_2_Modelamiento de relaciones"
    / "results"
    / "imgs"
)

DATA_S02.mkdir(parents=True, exist_ok=True)
RESULTS_IMGS.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()
PALETTE = sb.get_palette("categorical")

MAX_LAGS = 4
IRF_HORIZON = 8
ALPHA = 0.05


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, name: str) -> None:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _save_parquet(df: pd.DataFrame, name: str) -> Path:
    path = DATA_S02 / name
    df.to_parquet(path, index=False)
    print(f"   📦  {name}  shape={df.shape}")
    return path


def _period_label(anio: int, q: int) -> str:
    return f"{anio}-T{q}"


def run_adf(series: pd.Series, regression: str = "c") -> dict:
    s = series.dropna()
    if len(s) < 8:
        return {"adf_stat": np.nan, "adf_pvalue": np.nan, "adf_lags": np.nan,
                "adf_nobs": len(s), "adf_reject_h0": np.nan}
    # maxlag ≈ floor((T-1)**(1/3))
    maxlag = max(1, int((len(s) - 1) ** (1 / 3)))
    res = adfuller(s, maxlag=maxlag, regression=regression, autolag="AIC")
    return {
        "adf_stat": float(res[0]),
        "adf_pvalue": float(res[1]),
        "adf_lags": int(res[2]),
        "adf_nobs": int(res[3]),
        "adf_reject_h0": bool(res[1] < ALPHA),  # reject unit root → stationary
    }


def run_kpss(series: pd.Series, regression: str = "c") -> dict:
    s = series.dropna()
    if len(s) < 8:
        return {"kpss_stat": np.nan, "kpss_pvalue": np.nan, "kpss_lags": np.nan,
                "kpss_reject_h0": np.nan}
    res = kpss(s, regression=regression, nlags="auto")
    return {
        "kpss_stat": float(res[0]),
        "kpss_pvalue": float(res[1]),
        "kpss_lags": int(res[2]),
        "kpss_reject_h0": bool(res[1] < ALPHA),  # reject stationarity → unit root
    }


def classify_integration(level: pd.Series, name: str) -> dict:
    """Classify I(0)/I(1)/I(2) with ADF+KPSS concordance rule."""
    adf0 = run_adf(level)
    kpss0 = run_kpss(level)
    # Stationary if ADF rejects unit root AND KPSS does not reject stationarity
    is_i0 = bool(adf0["adf_reject_h0"]) and (not bool(kpss0["kpss_reject_h0"]))
    # Unit root if ADF fails to reject AND KPSS rejects stationarity
    is_unit = (not bool(adf0["adf_reject_h0"])) and bool(kpss0["kpss_reject_h0"])
    # Conflict → conservative: treat as non-stationary
    if is_i0:
        order, ndiff, decision = 0, 0, "concordancia_I0"
    else:
        d1 = level.diff().dropna()
        adf1 = run_adf(d1)
        kpss1 = run_kpss(d1)
        i0_d1 = bool(adf1["adf_reject_h0"]) and (not bool(kpss1["kpss_reject_h0"]))
        unit_d1 = (not bool(adf1["adf_reject_h0"])) and bool(kpss1["kpss_reject_h0"])
        if i0_d1 or (bool(adf1["adf_reject_h0"]) and not unit_d1):
            order, ndiff = 1, 1
            decision = "I1" if is_unit else "conflicto_nivel_tratado_I1"
        else:
            d2 = d1.diff().dropna()
            adf2 = run_adf(d2)
            if bool(adf2["adf_reject_h0"]):
                order, ndiff = 2, 2
                decision = "I2"
            else:
                order, ndiff = 1, 1
                decision = "inconcluso_default_I1"
        adf0 = {**adf0}  # keep level tests in row; store d1 briefly below

    row = {
        "serie": name,
        "n_obs": int(level.dropna().shape[0]),
        "orden_integracion": order,
        "n_diferencias": ndiff,
        "decision_regla": decision,
        **{f"level_{k}": v for k, v in adf0.items()},
        **{f"level_{k}": v for k, v in kpss0.items()},
    }
    # re-attach differenced tests for transparency
    d1 = level.diff().dropna()
    adf1 = run_adf(d1)
    kpss1 = run_kpss(d1)
    row.update({f"d1_{k}": v for k, v in adf1.items()})
    row.update({f"d1_{k}": v for k, v in kpss1.items()})
    return row


def portmanteau_var(resid: np.ndarray, lags: int = 4) -> dict:
    """Multivariate Ljung-Box style: average univariate LB p-values (small-T)."""
    pvals = []
    stats_ = []
    for j in range(resid.shape[1]):
        lb = acorr_ljungbox(resid[:, j], lags=[lags], return_df=True)
        pvals.append(float(lb["lb_pvalue"].iloc[0]))
        stats_.append(float(lb["lb_stat"].iloc[0]))
    return {
        "portmanteau_stat_mean": float(np.mean(stats_)),
        "portmanteau_pvalue_min": float(np.min(pvals)),
        "portmanteau_pvalue_mean": float(np.mean(pvals)),
        "portmanteau_pass": bool(np.min(pvals) >= ALPHA),
    }


def arch_multivariate(resid: np.ndarray, lags: int = 2) -> dict:
    pvals = []
    stats_ = []
    for j in range(resid.shape[1]):
        lm = het_arch(resid[:, j], nlags=lags)
        stats_.append(float(lm[0]))
        pvals.append(float(lm[1]))
    return {
        "arch_stat_mean": float(np.mean(stats_)),
        "arch_pvalue_min": float(np.min(pvals)),
        "arch_pvalue_mean": float(np.mean(pvals)),
        "arch_pass": bool(np.min(pvals) >= ALPHA),
    }


def jb_multivariate(resid: np.ndarray) -> dict:
    pvals = []
    stats_ = []
    for j in range(resid.shape[1]):
        jb_stat, jb_p, _, _ = jarque_bera(resid[:, j])
        stats_.append(float(jb_stat))
        pvals.append(float(jb_p))
    return {
        "jb_stat_mean": float(np.mean(stats_)),
        "jb_pvalue_min": float(np.min(pvals)),
        "jb_pvalue_mean": float(np.mean(pvals)),
        "jb_pass": bool(np.min(pvals) >= ALPHA),
    }


# ──────────────────────────────────────────────────────────────────────────────
#  1. Build AT quarterly series (construction)
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Building quarterly AT frequency for Construcción...")

empresas = pd.read_csv(DATA_RAW / "empresas.csv")
te = pd.read_parquet(DATA_S01 / "temporal_empresa_anio.parquet")
siniestros = pd.read_parquet(DATA_S01 / "siniestros_imputados.parquet")

ids_const = set(empresas.loc[empresas["sector"] == "Construccion", "id_empresa"])
# Prefer sector label from TE when available (same universe)
ids_te = set(te.loc[te["sector"] == "Construccion", "id_empresa"])
ids = ids_const | ids_te
print(f"   Empresas Construcción: {len(ids)}")

at = siniestros[
    (siniestros["id_empresa"].isin(ids)) & (siniestros["tipo"] == "AT")
].copy()
at["fecha"] = pd.to_datetime(at["fecha_ocurrencia"])
at["anio"] = at["fecha"].dt.year
at["q"] = at["fecha"].dt.quarter

n_at_q = (
    at.groupby(["anio", "q"], as_index=False)
    .size()
    .rename(columns={"size": "n_at"})
)

# Exposure: trabajadores del sector por año (panel TE; constante en estos datos)
trab_anio = (
    te.loc[te["id_empresa"].isin(ids)]
    .groupby("anio", as_index=False)["n_trabajadores"]
    .sum()
    .rename(columns={"n_trabajadores": "n_trabajadores_sector"})
)

at_q = n_at_q.merge(trab_anio, on="anio", how="left")
at_q["freq_at_x100"] = at_q["n_at"] / at_q["n_trabajadores_sector"] * 100
at_q["periodo"] = at_q.apply(lambda r: _period_label(int(r["anio"]), int(r["q"])), axis=1)
at_q["fecha"] = pd.to_datetime(
    at_q["anio"].astype(str) + "-" + (at_q["q"] * 3).astype(str).str.zfill(2) + "-01"
)
at_q = at_q.sort_values(["anio", "q"]).reset_index(drop=True)

# Annual validation vs TE
te_annual = (
    te.loc[te["id_empresa"].isin(ids)]
    .groupby("anio")["n_at"]
    .sum()
)
q_annual = at_q.groupby("anio")["n_at"].sum()
assert np.allclose(te_annual.reindex(q_annual.index).values, q_annual.values), \
    "Annual AT totals from quarterly aggregation must match temporal_empresa_anio"

_save_parquet(at_q, "at_construccion_trimestral.parquet")
print(f"   AT trimestral: {at_q['periodo'].iloc[0]} → {at_q['periodo'].iloc[-1]}  (n={len(at_q)})")
print(
    "   Justificación unidad trimestral: CEED e IPOC son trimestrales; "
    "EC se agrega a media trimestral; macro_sectorial es trimestral. "
    "Mensual forzaría interpolar CEED/IPOC y degradaría la identificación."
)

# ──────────────────────────────────────────────────────────────────────────────
#  2. Align panel: DANE + macro + AT
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔧  Aligning DANE + macro + AT panel...")

dane = pd.read_parquet(DATA_S02 / "panel_fuentes_trimestral.parquet")
macro = pd.read_csv(DATA_RAW / "macro_sectorial.csv")
macro_c = (
    macro.loc[macro["sector"] == "Construccion"]
    .rename(columns={"trimestre": "q"})
    [["anio", "q", "pib_sectorial_var", "empleo_sectorial",
      "ipp_sectorial", "tasa_informalidad"]]
    .copy()
)

panel = (
    at_q[["anio", "q", "periodo", "fecha", "n_at", "n_trabajadores_sector", "freq_at_x100"]]
    .merge(
        dane[["anio", "q", "area_censada_m2", "proceso_nueva_m2",
              "ipoc_total", "ec_m3_promedio_trim"]],
        on=["anio", "q"],
        how="left",
    )
    .merge(macro_c, on=["anio", "q"], how="left")
    .sort_values(["anio", "q"])
    .reset_index(drop=True)
)

# Modeling transforms (logs for levels; keep growth rates)
panel["log_ceed_flujo"] = np.log(panel["proceso_nueva_m2"])
panel["log_ceed_stock"] = np.log(panel["area_censada_m2"])
panel["log_ec"] = np.log(panel["ec_m3_promedio_trim"])
panel["log_ipoc"] = np.log(panel["ipoc_total"])
panel["log_empleo"] = np.log(panel["empleo_sectorial"])
panel["log_ipp"] = np.log(panel["ipp_sectorial"])
panel["log_freq_at"] = np.log(panel["freq_at_x100"])

_save_parquet(panel, "panel_ciclo_at_trimestral.parquet")

# Effective windows
mask_edif = panel[["freq_at_x100", "proceso_nueva_m2", "ec_m3_promedio_trim",
                   "pib_sectorial_var", "empleo_sectorial", "ipp_sectorial"]].notna().all(axis=1)
mask_ipoc = panel[["freq_at_x100", "ipoc_total", "pib_sectorial_var",
                   "empleo_sectorial"]].notna().all(axis=1)
sample_edif = panel.loc[mask_edif].copy()
sample_ipoc = panel.loc[mask_ipoc].copy()
print(f"   Panel completo: {panel['periodo'].iloc[0]} → {panel['periodo'].iloc[-1]} (n={len(panel)})")
print(f"   Muestra edificación (AT+CEED+EC+macro): "
      f"{sample_edif['periodo'].iloc[0]} → {sample_edif['periodo'].iloc[-1]} (n={len(sample_edif)})")
print(f"   Muestra IPOC (AT+IPOC+macro): "
      f"{sample_ipoc['periodo'].iloc[0]} → {sample_ipoc['periodo'].iloc[-1]} (n={len(sample_ipoc)})")

# ──────────────────────────────────────────────────────────────────────────────
#  3. Stationarity tests
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  Stationarity tests (ADF + KPSS)...")

series_map = {
    "freq_at_x100": panel["freq_at_x100"],
    "log_freq_at": panel["log_freq_at"],
    "log_ceed_flujo": panel["log_ceed_flujo"],
    "log_ec": panel["log_ec"],
    "log_ipoc": panel["log_ipoc"],
    "pib_sectorial_var": panel["pib_sectorial_var"],
    "empleo_sectorial": panel["empleo_sectorial"],
    "log_empleo": panel["log_empleo"],
    "ipp_sectorial": panel["ipp_sectorial"],
    "log_ipp": panel["log_ipp"],
}

stat_rows = [classify_integration(s, name) for name, s in series_map.items()]
stat_df = pd.DataFrame(stat_rows)
_save_parquet(stat_df, "estacionariedad_tests.parquet")
print(stat_df[["serie", "orden_integracion", "n_diferencias", "decision_regla",
               "level_adf_pvalue", "level_kpss_pvalue"]].to_string(index=False))

# Decision for modeling variables (prefer log versions for levels)
core_names = ["log_freq_at", "log_ceed_flujo", "log_ec", "log_ipoc",
              "pib_sectorial_var", "log_empleo", "log_ipp"]
core_orders = {
    r["serie"]: int(r["orden_integracion"])
    for r in stat_rows if r["serie"] in core_names
}
print("\n   Órdenes (núcleo modelado):", core_orders)

# ──────────────────────────────────────────────────────────────────────────────
#  4. Cointegration + specification choice (edificación block)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔎  Cointegration & specification (bloque edificación)...")

endog_cols = ["log_freq_at", "log_ceed_flujo", "log_ec"]
exog_cols = ["pib_sectorial_var", "log_empleo"]  # ipp reserved; keep DF

Y = sample_edif[endog_cols].copy()
Xex = sample_edif[exog_cols].copy()
Y.index = pd.PeriodIndex(
    [f"{int(a)}Q{int(q)}" for a, q in zip(sample_edif["anio"], sample_edif["q"])],
    freq="Q-DEC",
)
Xex.index = Y.index

# Engle-Granger: AT ~ CEED + EC
eg_stat, eg_p, eg_crit = coint(
    Y["log_freq_at"], Y[["log_ceed_flujo", "log_ec"]],
    trend="c", autolag="aic",
)
print(f"   Engle-Granger AT~CEED+EC: stat={eg_stat:.3f}  p={eg_p:.4f}")
eg_coint = bool(eg_p < ALPHA)

# Johansen (trace) — underpowered with T≈12; report with caveat
k_ar_diff = 1  # lag in differences for Johansen
joh = coint_johansen(Y.values, det_order=0, k_ar_diff=k_ar_diff)
# trace test: r=0, r<=1, r<=2
trace = joh.lr1
trace_crit_95 = joh.cvt[:, 1]
joh_r = 0
for r in range(len(trace)):
    if trace[r] > trace_crit_95[r]:
        joh_r = r + 1
    else:
        break
print(f"   Johansen trace: stats={np.round(trace, 2)}  crit95={np.round(trace_crit_95, 2)}  → r̂={joh_r}")

# Integration summary for endogenous
all_i1 = all(core_orders.get(c, 1) >= 1 for c in endog_cols)
any_i0 = any(core_orders.get(c, 1) == 0 for c in endog_cols)

# Small-sample rule (T_edif ≈ 12): Engle-Granger is primary.
# Johansen trace is known to over-reject (size distortion) in very short samples;
# treat it as corroborative only when EG also rejects the null of no-cointegration.
n_edif = len(Y)
if n_edif < 40:
    if eg_coint:
        spec_choice = "VECM"
        spec_reason = (
            f"T={n_edif} corto: EG detecta cointegración (p={eg_p:.3f}; Johansen r̂={joh_r} "
            "solo corroborativo). VECM captura equilibrio LP + dinámica CP."
        )
    else:
        spec_choice = "VAR_diferencias"
        spec_reason = (
            f"T={n_edif} corto: EG no rechaza ausencia de cointegración (p={eg_p:.3f}). "
            f"Johansen r̂={joh_r} se descarta por distorsión de tamaño en muestras pequeñas. "
            "Todas las endógenas se clasifican I(1) → VAR en primeras diferencias "
            "(evita regresión espuria). Preferible a OLS estático, ADL sin equilibrio LP "
            "formal, y VAR en niveles con series integradas."
        )
elif eg_coint or joh_r >= 1:
    spec_choice = "VECM"
    spec_reason = (
        f"Cointegración detectada (EG p={eg_p:.3f}, Johansen r̂={joh_r}). "
        "VECM captura equilibrio de largo plazo + dinámica de corto plazo."
    )
else:
    spec_choice = "VAR_diferencias"
    spec_reason = (
        f"Sin cointegración robusta (EG p={eg_p:.3f}, Johansen r̂={joh_r}). "
        "VAR en primeras diferencias evita regresión espuria; preferible a "
        "VAR en niveles o OLS estático con series I(1)."
    )

print(f"   → Especificación elegida: {spec_choice}")
print(f"     {spec_reason}")

# ──────────────────────────────────────────────────────────────────────────────
#  5. Lag selection
# ──────────────────────────────────────────────────────────────────────────────
print("\n📏  Lag selection (AIC/BIC/HQ), p≤4...")

# Work in differences for VAR path; levels for VECM path
Y_diff = Y.diff().dropna()
Xex_diff = Xex.diff().dropna()
# align
Xex_diff = Xex_diff.loc[Y_diff.index]

# Max feasible lags given T and k
k = Y_diff.shape[1]
T = Y_diff.shape[0]
# Need T > k*p + n_exog*p + k roughly; keep conservative
max_p = min(MAX_LAGS, max(1, (T - k - Xex_diff.shape[1] - 2) // (k + Xex_diff.shape[1])))
max_p = max(1, max_p)
print(f"   T_diff={T}, k={k}, max_p factible={max_p}")

lag_rows = []
best = {"aic": np.inf, "bic": np.inf, "hqic": np.inf}
best_p = {"aic": 1, "bic": 1, "hqic": 1}

for p in range(1, max_p + 1):
    try:
        model = VAR(Y_diff, exog=Xex_diff)
        res = model.fit(p)
        aic, bic, hq = float(res.aic), float(res.bic), float(res.hqic)
        lag_rows.append({"bloque": "edificacion_diff", "p": p, "aic": aic, "bic": bic, "hqic": hq,
                         "nobs": int(res.nobs), "ok": True})
        for crit, val in [("aic", aic), ("bic", bic), ("hqic", hq)]:
            if val < best[crit]:
                best[crit] = val
                best_p[crit] = p
    except Exception as exc:
        lag_rows.append({"bloque": "edificacion_diff", "p": p, "aic": np.nan, "bic": np.nan,
                         "hqic": np.nan, "nobs": np.nan, "ok": False, "error": str(exc)})

# Prefer BIC for short samples (more parsimonious); fall back AIC
p_star = best_p["bic"] if best_p["bic"] else best_p["aic"]
print(f"   Mejor p: AIC={best_p['aic']}, BIC={best_p['bic']}, HQ={best_p['hqic']} → p*={p_star} (BIC)")

# VECM lag selection if chosen (deterministic constant)
if spec_choice == "VECM":
    try:
        # select_order on levels
        so = vecm_select_order(Y, maxlags=max_p, deterministic="ci", seasons=0)
        # attributes: aic, bic, hqic, fpe as arrays indexed by lag
        for p in range(1, max_p + 1):
            lag_rows.append({
                "bloque": "edificacion_vecm",
                "p": p,
                "aic": float(so.aic[p]) if p in so.aic else np.nan,
                "bic": float(so.bic[p]) if p in so.bic else np.nan,
                "hqic": float(so.hqic[p]) if p in so.hqic else np.nan,
                "nobs": len(Y),
                "ok": True,
            })
        p_star_vecm = int(so.bic) if so.bic is not None else p_star
        print(f"   VECM select_order BIC p*={p_star_vecm}")
    except Exception as exc:
        p_star_vecm = p_star
        print(f"   VECM select_order falló ({exc}); uso p*={p_star}")
else:
    p_star_vecm = p_star

lag_df = pd.DataFrame(lag_rows)
_save_parquet(lag_df, "var_lag_selection.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  6. Estimate selected model + alternatives
# ──────────────────────────────────────────────────────────────────────────────
print("\n⚙️  Estimating models...")

results_store = {}

# --- Selected: VAR in differences or VECM ---
if spec_choice == "VECM":
    try:
        vecm = VECM(
            Y, k_ar_diff=p_star_vecm, coint_rank=max(1, joh_r),
            deterministic="ci", exog=Xex,
        )
        vecm_res = vecm.fit()
        results_store["selected"] = ("VECM", vecm_res, Y, None)
        print(f"   VECM rank={max(1, joh_r)}  k_ar_diff={p_star_vecm}  OK")
        p_used = p_star_vecm
    except Exception as exc:
        print(f"   VECM falló ({exc}); fallback VAR en diferencias")
        spec_choice = "VAR_diferencias"
        spec_reason += f" [VECM falló: {exc}]"

if spec_choice == "VAR_diferencias":
    var_model = VAR(Y_diff, exog=Xex_diff)
    var_res = var_model.fit(p_star)
    results_store["selected"] = ("VAR_diff", var_res, Y_diff, Xex_diff)
    print(f"   VAR(p={p_star}) en diferencias OK")
    p_used = p_star

# --- Alternative A: OLS estático freq ~ CEED + EC + macro ---
ols_df = sample_edif.dropna(subset=endog_cols + exog_cols).copy()
ols_y = ols_df["log_freq_at"]
ols_x = add_constant(ols_df[["log_ceed_flujo", "log_ec"] + exog_cols])
ols_res = OLS(ols_y, ols_x).fit()
results_store["ols"] = ols_res

# --- Alternative B: ADL(1) ---
adl_df = ols_df.copy()
adl_df["log_freq_at_l1"] = adl_df["log_freq_at"].shift(1)
adl_df["log_ceed_flujo_l1"] = adl_df["log_ceed_flujo"].shift(1)
adl_df = adl_df.dropna()
adl_y = adl_df["log_freq_at"]
adl_x = add_constant(adl_df[
    ["log_freq_at_l1", "log_ceed_flujo", "log_ceed_flujo_l1", "log_ec"] + exog_cols
])
adl_res = OLS(adl_y, adl_x).fit()
results_store["adl"] = adl_res

# --- Alternative C: VAR en niveles (para comparar, no preferido si I(1)) ---
try:
    var_lvl = VAR(Y, exog=Xex).fit(max(1, min(p_used, 2)))
    results_store["var_levels"] = var_lvl
except Exception as exc:
    print(f"   VAR niveles no estimado: {exc}")

# ──────────────────────────────────────────────────────────────────────────────
#  7. IRF + FEVD (edificación)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📈  IRF & FEVD...")

irf_rows = []
fevd_rows = []

sel_name, sel_res, Y_used, X_used = results_store["selected"]

def _extract_irf_fevd_var(res, names, horizon=IRF_HORIZON):
    irf = res.irf(horizon)
    # orth=True for orthogonalized
    orth = irf.orth_irfs  # shape (h+1, neqs, neqs) — response, shock
    fevd = res.fevd(horizon)
    fevd_arr = fevd.decomp  # (neqs, horizon, neqs) in some versions
    return orth, fevd_arr, fevd


if sel_name == "VAR_diff":
    orth, fevd_arr, fevd_obj = _extract_irf_fevd_var(sel_res, endog_cols)
    names = list(sel_res.names)
    # Map names
    i_at = names.index("log_freq_at")
    i_ceed = names.index("log_ceed_flujo")
    for h in range(orth.shape[0]):
        for i_resp, rn in enumerate(names):
            for i_sh, sn in enumerate(names):
                irf_rows.append({
                    "bloque": "edificacion",
                    "modelo": sel_name,
                    "horizonte": h,
                    "respuesta": rn,
                    "shock": sn,
                    "irf_orth": float(orth[h, i_resp, i_sh]),
                })
    # FEVD at 4 and 8 (1-indexed horizons in decomp)
    # fevd.decomp shape: (neqs, periods, neqs) where periods = horizon
    decomp = np.asarray(fevd_obj.decomp)
    for h_target in [4, 8]:
        h_idx = min(h_target, decomp.shape[1]) - 1
        for i_resp, rn in enumerate(names):
            for i_sh, sn in enumerate(names):
                fevd_rows.append({
                    "bloque": "edificacion",
                    "modelo": sel_name,
                    "horizonte": h_target,
                    "respuesta": rn,
                    "shock": sn,
                    "fevd_share": float(decomp[i_resp, h_idx, i_sh]),
                })
    print(f"   IRF CEED→AT (h=1..4): "
          f"{[round(orth[h, i_at, i_ceed], 4) for h in range(1, 5)]}")
    print(f"   IRF AT→CEED (h=1..4): "
          f"{[round(orth[h, i_ceed, i_at], 4) for h in range(1, 5)]}")

elif sel_name == "VECM":
    # VECM IRF via fitted VAR representation if available
    try:
        irf = sel_res.irf(periods=IRF_HORIZON)
        # statsmodels VECMResults.irf returns IRF object
        orth = irf.orth_irfs if hasattr(irf, "orth_irfs") else irf.irfs
        names = endog_cols
        i_at, i_ceed = 0, 1
        for h in range(orth.shape[0]):
            for i_resp, rn in enumerate(names):
                for i_sh, sn in enumerate(names):
                    irf_rows.append({
                        "bloque": "edificacion",
                        "modelo": sel_name,
                        "horizonte": h,
                        "respuesta": rn,
                        "shock": sn,
                        "irf_orth": float(orth[h, i_resp, i_sh]),
                    })
        # FEVD approximate via companion VAR
        var_rep = sel_res.var_rep if hasattr(sel_res, "var_rep") else None
        if var_rep is not None:
            # Fall back: estimate VAR on levels residuals path — skip detailed FEVD
            print("   VECM: IRF OK; FEVD vía VAR en diferencias auxiliar")
            aux = VAR(Y_diff, exog=Xex_diff).fit(p_used)
            fevd_obj = aux.fevd(IRF_HORIZON)
            decomp = np.asarray(fevd_obj.decomp)
            names_aux = list(aux.names)
            for h_target in [4, 8]:
                h_idx = min(h_target, decomp.shape[1]) - 1
                for i_resp, rn in enumerate(names_aux):
                    for i_sh, sn in enumerate(names_aux):
                        fevd_rows.append({
                            "bloque": "edificacion",
                            "modelo": "VECM_fevd_via_VARdiff",
                            "horizonte": h_target,
                            "respuesta": rn,
                            "shock": sn,
                            "fevd_share": float(decomp[i_resp, h_idx, i_sh]),
                        })
        print(f"   IRF CEED→AT (h=1..4): "
              f"{[round(orth[h, i_at, i_ceed], 4) for h in range(1, min(5, orth.shape[0]))]}")
    except Exception as exc:
        print(f"   IRF VECM falló ({exc}); reestimando VAR diff para IRF")
        aux = VAR(Y_diff, exog=Xex_diff).fit(p_used)
        results_store["selected"] = ("VAR_diff", aux, Y_diff, Xex_diff)
        sel_name, sel_res = "VAR_diff", aux
        orth, fevd_arr, fevd_obj = _extract_irf_fevd_var(sel_res, endog_cols)
        names = list(sel_res.names)
        i_at = names.index("log_freq_at")
        i_ceed = names.index("log_ceed_flujo")
        for h in range(orth.shape[0]):
            for i_resp, rn in enumerate(names):
                for i_sh, sn in enumerate(names):
                    irf_rows.append({
                        "bloque": "edificacion",
                        "modelo": sel_name,
                        "horizonte": h,
                        "respuesta": rn,
                        "shock": sn,
                        "irf_orth": float(orth[h, i_resp, i_sh]),
                    })
        decomp = np.asarray(fevd_obj.decomp)
        for h_target in [4, 8]:
            h_idx = min(h_target, decomp.shape[1]) - 1
            for i_resp, rn in enumerate(names):
                for i_sh, sn in enumerate(names):
                    fevd_rows.append({
                        "bloque": "edificacion",
                        "modelo": sel_name,
                        "horizonte": h_target,
                        "respuesta": rn,
                        "shock": sn,
                        "fevd_share": float(decomp[i_resp, h_idx, i_sh]),
                    })

# ──────────────────────────────────────────────────────────────────────────────
#  8. Diagnostics comparison
# ──────────────────────────────────────────────────────────────────────────────
print("\n🩺  Residual diagnostics...")

diag_rows = []

def _diag_from_resid(name, resid, aic=np.nan, bic=np.nan, nobs=np.nan, k_params=np.nan):
    if resid.ndim == 1:
        resid = resid.reshape(-1, 1)
    row = {
        "modelo": name,
        "nobs": nobs,
        "k_params": k_params,
        "aic": aic,
        "bic": bic,
    }
    row.update(portmanteau_var(resid, lags=min(4, max(1, resid.shape[0] // 4))))
    row.update(arch_multivariate(resid, lags=min(2, max(1, resid.shape[0] // 5))))
    row.update(jb_multivariate(resid))
    return row


# Selected
if sel_name == "VAR_diff":
    resid = np.asarray(sel_res.resid)
    diag_rows.append(_diag_from_resid(
        "VAR_diff_edificacion", resid,
        aic=float(sel_res.aic), bic=float(sel_res.bic),
        nobs=int(sel_res.nobs), k_params=int(sel_res.df_model),
    ))
elif sel_name == "VECM":
    resid = np.asarray(sel_res.resid)
    diag_rows.append(_diag_from_resid(
        "VECM_edificacion", resid,
        aic=np.nan, bic=np.nan,
        nobs=int(resid.shape[0]), k_params=np.nan,
    ))

# OLS
diag_rows.append(_diag_from_resid(
    "OLS_estatico", np.asarray(ols_res.resid),
    aic=float(ols_res.aic), bic=float(ols_res.bic),
    nobs=int(ols_res.nobs), k_params=int(ols_res.df_model),
))
# ADL
diag_rows.append(_diag_from_resid(
    "ADL_1", np.asarray(adl_res.resid),
    aic=float(adl_res.aic), bic=float(adl_res.bic),
    nobs=int(adl_res.nobs), k_params=int(adl_res.df_model),
))
# VAR levels
if "var_levels" in results_store:
    vr = results_store["var_levels"]
    diag_rows.append(_diag_from_resid(
        "VAR_niveles", np.asarray(vr.resid),
        aic=float(vr.aic), bic=float(vr.bic),
        nobs=int(vr.nobs), k_params=int(vr.df_model),
    ))

diag_df = pd.DataFrame(diag_rows)
print(diag_df[["modelo", "aic", "bic", "portmanteau_pvalue_min",
               "arch_pvalue_min", "jb_pvalue_min",
               "portmanteau_pass", "arch_pass", "jb_pass"]].to_string(index=False))

# ──────────────────────────────────────────────────────────────────────────────
#  9. IPOC auxiliary block
# ──────────────────────────────────────────────────────────────────────────────
print("\n🏗️  Auxiliary IPOC block (infraestructura)...")

endog_ipoc = ["log_freq_at", "log_ipoc"]
exog_ipoc = ["pib_sectorial_var", "log_empleo"]
Y_i = sample_ipoc[endog_ipoc].copy()
X_i = sample_ipoc[exog_ipoc].copy()
Y_i.index = pd.PeriodIndex(
    [f"{int(a)}Q{int(q)}" for a, q in zip(sample_ipoc["anio"], sample_ipoc["q"])],
    freq="Q-DEC",
)
X_i.index = Y_i.index

# Stationarity already done; cointegration EG
eg_i_stat, eg_i_p, _ = coint(Y_i["log_freq_at"], Y_i["log_ipoc"], trend="c", autolag="aic")
print(f"   EG AT~IPOC: stat={eg_i_stat:.3f} p={eg_i_p:.4f}")

Y_i_diff = Y_i.diff().dropna()
X_i_diff = X_i.diff().dropna().loc[Y_i_diff.index]
T_i, k_i = Y_i_diff.shape
max_p_i = min(MAX_LAGS, max(1, (T_i - k_i - X_i_diff.shape[1] - 2) // (k_i + X_i_diff.shape[1])))
max_p_i = max(1, max_p_i)

best_bic_i, p_star_i = np.inf, 1
for p in range(1, max_p_i + 1):
    try:
        r = VAR(Y_i_diff, exog=X_i_diff).fit(p)
        lag_rows.append({"bloque": "ipoc_diff", "p": p, "aic": float(r.aic),
                         "bic": float(r.bic), "hqic": float(r.hqic),
                         "nobs": int(r.nobs), "ok": True})
        if r.bic < best_bic_i:
            best_bic_i, p_star_i = r.bic, p
    except Exception:
        pass

if eg_i_p < ALPHA:
    try:
        vecm_i = VECM(Y_i, k_ar_diff=p_star_i, coint_rank=1, deterministic="ci", exog=X_i).fit()
        ipoc_model_name = "VECM"
        ipoc_res = vecm_i
        print(f"   IPOC: VECM p={p_star_i}")
    except Exception:
        ipoc_res = VAR(Y_i_diff, exog=X_i_diff).fit(p_star_i)
        ipoc_model_name = "VAR_diff"
        print(f"   IPOC: VAR_diff p={p_star_i} (VECM fallback)")
else:
    ipoc_res = VAR(Y_i_diff, exog=X_i_diff).fit(p_star_i)
    ipoc_model_name = "VAR_diff"
    print(f"   IPOC: VAR_diff p={p_star_i} (sin cointegración)")

# IRF IPOC
try:
    if ipoc_model_name == "VAR_diff":
        irf_i = ipoc_res.irf(IRF_HORIZON)
        orth_i = irf_i.orth_irfs
        names_i = list(ipoc_res.names)
        i_at_i = names_i.index("log_freq_at")
        i_ip = names_i.index("log_ipoc")
        for h in range(orth_i.shape[0]):
            for i_resp, rn in enumerate(names_i):
                for i_sh, sn in enumerate(names_i):
                    irf_rows.append({
                        "bloque": "ipoc",
                        "modelo": ipoc_model_name,
                        "horizonte": h,
                        "respuesta": rn,
                        "shock": sn,
                        "irf_orth": float(orth_i[h, i_resp, i_sh]),
                    })
        fevd_i = ipoc_res.fevd(IRF_HORIZON)
        decomp_i = np.asarray(fevd_i.decomp)
        for h_target in [4, 8]:
            h_idx = min(h_target, decomp_i.shape[1]) - 1
            for i_resp, rn in enumerate(names_i):
                for i_sh, sn in enumerate(names_i):
                    fevd_rows.append({
                        "bloque": "ipoc",
                        "modelo": ipoc_model_name,
                        "horizonte": h_target,
                        "respuesta": rn,
                        "shock": sn,
                        "fevd_share": float(decomp_i[i_resp, h_idx, i_sh]),
                    })
        print(f"   IRF IPOC→AT (h=1..4): "
              f"{[round(orth_i[h, i_at_i, i_ip], 4) for h in range(1, 5)]}")
        # diagnostics
        diag_rows.append(_diag_from_resid(
            "VAR_diff_ipoc", np.asarray(ipoc_res.resid),
            aic=float(ipoc_res.aic), bic=float(ipoc_res.bic),
            nobs=int(ipoc_res.nobs), k_params=int(ipoc_res.df_model),
        ))
    else:
        irf_i = ipoc_res.irf(periods=IRF_HORIZON)
        orth_i = irf_i.orth_irfs if hasattr(irf_i, "orth_irfs") else irf_i.irfs
        for h in range(orth_i.shape[0]):
            for i_resp, rn in enumerate(endog_ipoc):
                for i_sh, sn in enumerate(endog_ipoc):
                    irf_rows.append({
                        "bloque": "ipoc",
                        "modelo": ipoc_model_name,
                        "horizonte": h,
                        "respuesta": rn,
                        "shock": sn,
                        "irf_orth": float(orth_i[h, i_resp, i_sh]),
                    })
        diag_rows.append(_diag_from_resid(
            "VECM_ipoc", np.asarray(ipoc_res.resid),
            nobs=int(np.asarray(ipoc_res.resid).shape[0]),
        ))
except Exception as exc:
    print(f"   IRF IPOC falló: {exc}")

# Spearman contemporaneous on overlapping sample
ov = sample_edif.dropna(subset=["proceso_nueva_m2", "ipoc_total", "freq_at_x100"])
rho_ceed_ipoc = ov["proceso_nueva_m2"].corr(ov["ipoc_total"], method="spearman")
rho_ceed_at = ov["proceso_nueva_m2"].corr(ov["freq_at_x100"], method="spearman")
rho_ipoc_at = ov["ipoc_total"].corr(ov["freq_at_x100"], method="spearman")
print(f"   Spearman muestra edif: CEED↔IPOC={rho_ceed_ipoc:.3f}  "
      f"CEED↔AT={rho_ceed_at:.3f}  IPOC↔AT={rho_ipoc_at:.3f}")

# Persist IRF/FEVD/diag/lags (refresh lag_df)
irf_df = pd.DataFrame(irf_rows)
fevd_df = pd.DataFrame(fevd_rows)
irf_fevd = pd.concat([
    irf_df.assign(metric="irf"),
    fevd_df.rename(columns={"fevd_share": "valor"}).assign(metric="fevd")
      .rename(columns={"valor": "irf_orth"})  # unify col later
], ignore_index=True)
# cleaner separate save
_save_parquet(irf_df, "var_irf.parquet")
_save_parquet(fevd_df, "var_fevd.parquet")
diag_df = pd.DataFrame(diag_rows)
_save_parquet(diag_df, "var_diagnosticos.parquet")
lag_df = pd.DataFrame(lag_rows)
_save_parquet(lag_df, "var_lag_selection.parquet")

# Combined summary for docs
summary = pd.DataFrame([{
    "spec_elegida": spec_choice,
    "spec_reason": spec_reason,
    "p_star": int(p_used),
    "eg_pvalue_edif": float(eg_p),
    "johansen_r": int(joh_r),
    "ventana_edif": f"{sample_edif['periodo'].iloc[0]}:{sample_edif['periodo'].iloc[-1]}",
    "n_edif": int(len(sample_edif)),
    "ventana_ipoc": f"{sample_ipoc['periodo'].iloc[0]}:{sample_ipoc['periodo'].iloc[-1]}",
    "n_ipoc": int(len(sample_ipoc)),
    "ipoc_spec": ipoc_model_name,
    "ipoc_p": int(p_star_i),
    "eg_pvalue_ipoc": float(eg_i_p),
    "rho_ceed_ipoc": float(rho_ceed_ipoc),
    "rho_ceed_at": float(rho_ceed_at),
    "rho_ipoc_at": float(rho_ipoc_at),
    "ols_ceed_coef": float(ols_res.params.get("log_ceed_flujo", np.nan)),
    "ols_ceed_pvalue": float(ols_res.pvalues.get("log_ceed_flujo", np.nan)),
    "adl_r2": float(adl_res.rsquared),
}])
_save_parquet(summary, "var_modelo_resumen.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  10. Plots
# ──────────────────────────────────────────────────────────────────────────────
print("\n🎨  Generating plots...")

# 01 series panel
fig, axes = sb.create_dashboard(
    2, 2,
    title="Series trimestrales: AT Construcción y ciclo sectorial",
    subtitle=f"AT {at_q['periodo'].iloc[0]}–{at_q['periodo'].iloc[-1]} | "
             f"Edificación modelada {sample_edif['periodo'].iloc[0]}–{sample_edif['periodo'].iloc[-1]}",
)
ax = axes[0]
ax.plot(panel["periodo"], panel["freq_at_x100"], color=PALETTE[0], marker="o", ms=3, lw=1.8)
ax.set_title("Frecuencia AT (×100 trabajadores)")
ax.tick_params(axis="x", rotation=45, labelsize=7)
ax.set_ylabel("freq_at_x100")

ax = axes[1]
ax.plot(panel["periodo"], panel["proceso_nueva_m2"] / 1e6, color=PALETTE[1],
        marker="o", ms=3, lw=1.8, label="CEED flujo")
ax.set_title("CEED proceso_nueva (M m²)")
ax.tick_params(axis="x", rotation=45, labelsize=7)

ax = axes[2]
ax.plot(panel["periodo"], panel["ec_m3_promedio_trim"] / 1e3, color=PALETTE[2],
        marker="o", ms=3, lw=1.8)
ax.set_title("EC m³ (prom. trim., miles)")
ax.tick_params(axis="x", rotation=45, labelsize=7)

ax = axes[3]
ax.plot(panel["periodo"], panel["ipoc_total"], color=PALETTE[3], marker="o", ms=3, lw=1.8)
ax.plot(panel["periodo"], panel["empleo_sectorial"], color=PALETTE[4],
        marker="s", ms=3, lw=1.5, label="Empleo")
ax.set_title("IPOC e empleo sectorial")
ax.legend(fontsize=7, frameon=True)
ax.tick_params(axis="x", rotation=45, labelsize=7)

for a in axes:
    # show every 4th tick
    ticks = list(range(0, len(panel), 4))
    a.set_xticks(ticks)
    a.set_xticklabels([panel["periodo"].iloc[i] for i in ticks], rotation=45, ha="right")

sb.add_sura_footer(fig, text="S02 – 2.2.1 | Series alineadas")
_save_fig(fig, "01_series_at_ciclo.png")

# 02 stationarity
fig, ax = sb.create_report_figure(
    title="Clasificación de integración (ADF + KPSS)",
    subtitle="Orden I(d); regla de concordancia α=0.05",
)
plot_stat = stat_df[stat_df["serie"].isin(core_names)].copy()
colors = [PALETTE[min(int(o), 2)] for o in plot_stat["orden_integracion"]]
ax.barh(plot_stat["serie"], plot_stat["orden_integracion"], color=colors, alpha=0.9)
ax.set_xlabel("Orden de integración d")
ax.set_xticks([0, 1, 2])
for i, (d, dec) in enumerate(zip(plot_stat["orden_integracion"], plot_stat["decision_regla"])):
    ax.text(d + 0.05, i, f"I({d}) · {dec}", va="center", fontsize=7)
sb.add_sura_footer(fig, text="S02 – 2.2.1 | Estacionariedad")
_save_fig(fig, "01_estacionariedad_orden.png")

# 03 IRF edificación CEED↔AT
irf_ed = irf_df[irf_df["bloque"] == "edificacion"]
fig, axes = sb.create_dashboard(
    1, 2,
    title=f"IRF ortogonalizadas — bloque edificación ({sel_name}, p={p_used})",
    subtitle="Shock de 1 d.e. | respuesta en log",
)
for ax, shock, resp, title in [
    (axes[0], "log_ceed_flujo", "log_freq_at", "Shock CEED → respuesta AT"),
    (axes[1], "log_freq_at", "log_ceed_flujo", "Shock AT → respuesta CEED"),
]:
    sub = irf_ed[(irf_ed["shock"] == shock) & (irf_ed["respuesta"] == resp)].sort_values("horizonte")
    if len(sub):
        ax.plot(sub["horizonte"], sub["irf_orth"], color=PALETTE[0], marker="o", lw=2)
        ax.axhline(0, color="#888", lw=0.9)
    ax.set_title(title)
    ax.set_xlabel("Trimestres")
    ax.set_ylabel("IRF")
sb.add_sura_footer(fig, text="S02 – 2.2.1 | IRF edificación")
_save_fig(fig, "01_irf_ceed_at.png")

# 04 FEVD
fevd_ed = fevd_df[fevd_df["bloque"] == "edificacion"]
fig, axes = sb.create_dashboard(
    1, 2,
    title="FEVD — varianza de log_freq_at explicada por shocks",
    subtitle="Horizontes 4 y 8 trimestres | bloque edificación",
)
for ax, h in zip(axes, [4, 8]):
    sub = fevd_ed[(fevd_ed["horizonte"] == h) & (fevd_ed["respuesta"] == "log_freq_at")]
    if len(sub):
        ax.bar(sub["shock"], sub["fevd_share"] * 100, color=PALETTE[: len(sub)], alpha=0.9)
        for i, v in enumerate(sub["fevd_share"] * 100):
            ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_title(f"h = {h}")
    ax.set_ylabel("% de varianza")
    ax.tick_params(axis="x", rotation=20)
    ax.set_ylim(0, 110)
sb.add_sura_footer(fig, text="S02 – 2.2.1 | FEVD")
_save_fig(fig, "01_fevd_at.png")

# 05 diagnostics comparison
fig, ax = sb.create_report_figure(
    title="Diagnósticos de residuos — comparación de especificaciones",
    subtitle="p-valores mínimos (Portmanteau / ARCH / Jarque-Bera); línea α=0.05",
)
models = diag_df["modelo"].tolist()
x = np.arange(len(models))
w = 0.25
ax.bar(x - w, diag_df["portmanteau_pvalue_min"], width=w, color=PALETTE[0], label="Portmanteau")
ax.bar(x, diag_df["arch_pvalue_min"], width=w, color=PALETTE[1], label="ARCH")
ax.bar(x + w, diag_df["jb_pvalue_min"], width=w, color=PALETTE[2], label="Jarque-Bera")
ax.axhline(ALPHA, color="#C62828", ls="--", lw=1.2, label="α=0.05")
ax.set_xticks(x)
ax.set_xticklabels(models, rotation=25, ha="right", fontsize=8)
ax.set_ylabel("p-valor mínimo")
ax.legend(frameon=True, fontsize=8)
ax.set_ylim(0, 1.05)
sb.add_sura_footer(fig, text="S02 – 2.2.1 | Diagnósticos")
_save_fig(fig, "01_diagnosticos_residuos.png")

# 06 IPOC vs CEED IRF comparison
fig, axes = sb.create_dashboard(
    1, 2,
    title="Comparación IRF: shock de ciclo → frecuencia AT",
    subtitle="Edificación (CEED) vs infraestructura (IPOC) | fases del ciclo",
)
sub_c = irf_df[(irf_df["bloque"] == "edificacion") &
               (irf_df["shock"] == "log_ceed_flujo") &
               (irf_df["respuesta"] == "log_freq_at")].sort_values("horizonte")
sub_i = irf_df[(irf_df["bloque"] == "ipoc") &
               (irf_df["shock"] == "log_ipoc") &
               (irf_df["respuesta"] == "log_freq_at")].sort_values("horizonte")
ax = axes[0]
if len(sub_c):
    ax.plot(sub_c["horizonte"], sub_c["irf_orth"], color=PALETTE[0], marker="o", lw=2, label="CEED→AT")
if len(sub_i):
    ax.plot(sub_i["horizonte"], sub_i["irf_orth"], color=PALETTE[2], marker="s", lw=2, label="IPOC→AT")
ax.axhline(0, color="#888", lw=0.9)
ax.legend(frameon=True, fontsize=8)
ax.set_title("IRF sobre log_freq_at")
ax.set_xlabel("Trimestres")

ax = axes[1]
labels = ["CEED↔IPOC", "CEED↔AT", "IPOC↔AT"]
vals = [rho_ceed_ipoc, rho_ceed_at, rho_ipoc_at]
colors = [PALETTE[0] if v >= 0 else PALETTE[2] for v in vals]
ax.barh(labels, vals, color=colors, alpha=0.9)
ax.axvline(0, color="#888", lw=0.9)
ax.set_title("Spearman contemporáneo (muestra edif.)")
ax.set_xlim(-1, 1)
for i, v in enumerate(vals):
    ax.text(v + (0.02 if v >= 0 else -0.02), i, f"{v:.2f}",
            va="center", ha="left" if v >= 0 else "right", fontsize=8)

sb.add_sura_footer(fig, text="S02 – 2.2.1 | Bloque IPOC vs edificación")
_save_fig(fig, "01_irf_ipoc_vs_ceed.png")

# 07 lag selection
fig, ax = sb.create_report_figure(
    title="Selección de rezagos VAR (diferencias) — bloque edificación",
    subtitle="AIC / BIC / HQ; p* por BIC (muestras cortas)",
)
sub = lag_df[lag_df["bloque"] == "edificacion_diff"].dropna(subset=["aic"])
if len(sub):
    ax.plot(sub["p"], sub["aic"], marker="o", color=PALETTE[0], label="AIC")
    ax.plot(sub["p"], sub["bic"], marker="s", color=PALETTE[1], label="BIC")
    ax.plot(sub["p"], sub["hqic"], marker="^", color=PALETTE[2], label="HQ")
    ax.axvline(p_used, color="#C62828", ls="--", lw=1.2, label=f"p*={p_used}")
ax.set_xlabel("p (trimestres)")
ax.set_ylabel("Criterio de información")
ax.legend(frameon=True, fontsize=8)
sb.add_sura_footer(fig, text="S02 – 2.2.1 | Lag selection")
_save_fig(fig, "01_lag_selection.png")

# ──────────────────────────────────────────────────────────────────────────────
#  Print key findings for relaciones.md
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("HALLAZGOS CLAVE PARA relaciones.md")
print("=" * 72)
print(f"Especificación: {spec_choice} (p={p_used})")
print(f"Razón: {spec_reason}")
print(f"Ventana edificación: {summary.iloc[0]['ventana_edif']} n={summary.iloc[0]['n_edif']}")
print(f"Ventana IPOC: {summary.iloc[0]['ventana_ipoc']} n={summary.iloc[0]['n_ipoc']}")
print(f"EG edif p={eg_p:.4f} | Johansen r={joh_r} | EG ipoc p={eg_i_p:.4f}")
print(f"OLS log_ceed coef={ols_res.params.get('log_ceed_flujo', np.nan):.4f} "
      f"(p={ols_res.pvalues.get('log_ceed_flujo', np.nan):.4f})")
print(f"ADL R²={adl_res.rsquared:.3f}")
if len(irf_ed):
    s = irf_ed[(irf_ed.shock == "log_ceed_flujo") & (irf_ed.respuesta == "log_freq_at")]
    print("IRF CEED→AT:", s.sort_values("horizonte")["irf_orth"].round(4).tolist())
print(diag_df[["modelo", "aic", "portmanteau_pass", "arch_pass", "jb_pass"]].to_string(index=False))
print("\n✅  Modelamiento 2.2.1 completado.")
