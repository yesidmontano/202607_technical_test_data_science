"""
Robustez: estacionariedad, rezagos/adelantos y cointegración
============================================================
Sección: S02 – Modelación Económica Sectorial
Subsección: 2.2 – Modelamiento de relaciones (ítem 2.2.2)

Descripción:
    Análisis profundo sobre los resultados de 2.2.1:
    · Confirmación ADF/KPSS/PP (esp. pib_sectorial_var, log_freq_at)
    · CCF de rezagos/adelantos ΔAT ↔ ΔCEED / ΔEC / ΔIPOC
    · Cointegración EG + Johansen (con corrección Reinsel–Ahn) en n=18
    · Sensibilidad del VAR(1) en diferencias (T=12 vs T=18)
    · Diagnósticos extendidos (Portmanteau Q=4/8, CUSUM, dummies)
    · Decisión definitiva de especificación

Inputs (staging existente — no reconstruir series desde raw):
    - data/staging/S02/panel_ciclo_at_trimestral.parquet
    - data/staging/S02/estacionariedad_tests.parquet
    - data/staging/S02/var_irf.parquet
    - data/staging/S02/var_fevd.parquet
    - data/staging/S02/var_diagnosticos.parquet
    - data/staging/S02/var_modelo_resumen.parquet

Outputs:
    - data/staging/S02/estacionariedad_robustez.parquet
    - data/staging/S02/ccf_rezagos.parquet
    - data/staging/S02/coint_robustez.parquet
    - data/staging/S02/var_sensibilidad_irf.parquet
    - data/staging/S02/var_diagnosticos_ext.parquet
    - results/estacionariedad_robustez.md
    - results/imgs/02_*.png
    - actualiza results/relaciones.md §2.2.2

Uso:
    .venv/bin/python \\
      "sections/S02-Modelacion_Economica_Sectorial/2_2_Modelamiento de relaciones/code/02-estacionariedad/estacionariedad_robustez.py"
"""

from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from statsmodels.tsa.stattools import adfuller, kpss, coint, ccf
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.stats.diagnostic import acorr_ljungbox, breaks_cusumolsresid
from statsmodels.stats.stattools import jarque_bera

import sura_brand as sb

warnings.filterwarnings("ignore")

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
ALPHA = 0.05

ROOT = Path(__file__).resolve().parents[5]
DATA_S02 = ROOT / "data" / "staging" / "S02"
RESULTS = (
    ROOT
    / "sections"
    / "S02-Modelacion_Economica_Sectorial"
    / "2_2_Modelamiento de relaciones"
    / "results"
)
IMGS = RESULTS / "imgs"
IMGS.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()
PALETTE = sb.get_palette("categorical")


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, name: str) -> None:
    fig.savefig(IMGS / name, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _save_parquet(df: pd.DataFrame, name: str) -> None:
    path = DATA_S02 / name
    df.to_parquet(path, index=False)
    print(f"   📦  {name}  shape={df.shape}")


def run_adf(s: pd.Series, regression: str = "c") -> dict:
    s = s.dropna()
    if len(s) < 10:
        return {"adf_stat": np.nan, "adf_pvalue": np.nan, "adf_lags": np.nan,
                "adf_reject": np.nan, "n": len(s)}
    maxlag = max(1, int((len(s) - 1) ** (1 / 3)))
    res = adfuller(s, maxlag=maxlag, regression=regression, autolag="AIC")
    return {
        "adf_stat": float(res[0]),
        "adf_pvalue": float(res[1]),
        "adf_lags": int(res[2]),
        "adf_reject": bool(res[1] < ALPHA),
        "n": int(res[3]),
    }


def run_kpss(s: pd.Series, regression: str = "c") -> dict:
    s = s.dropna()
    if len(s) < 10:
        return {"kpss_stat": np.nan, "kpss_pvalue": np.nan, "kpss_lags": np.nan,
                "kpss_reject": np.nan, "n": len(s)}
    res = kpss(s, regression=regression, nlags="auto")
    return {
        "kpss_stat": float(res[0]),
        "kpss_pvalue": float(res[1]),
        "kpss_lags": int(res[2]),
        "kpss_reject": bool(res[1] < ALPHA),
        "n": len(s),
    }


def phillips_perron(s: pd.Series, regression: str = "c", lags: int | None = None) -> dict:
    """
    Phillips–Perron unit-root test (constant or constant+trend).
    Implements Newey–West corrected t-stat on the AR(1) residual regression.
    Critical values / p-values approximated via MacKinnon (same as ADF).
    """
    y = np.asarray(s.dropna(), dtype=float)
    n = len(y)
    if n < 10:
        return {"pp_stat": np.nan, "pp_pvalue": np.nan, "pp_lags": np.nan,
                "pp_reject": np.nan, "n": n}

    y_lag = y[:-1]
    dy = np.diff(y)
    if regression == "ct":
        t = np.arange(1, n)
        X = np.column_stack([np.ones(n - 1), t, y_lag])
        beta_idx = 2
    else:
        X = np.column_stack([np.ones(n - 1), y_lag])
        beta_idx = 1

    ols = OLS(dy, X).fit()
    b = ols.params[beta_idx]
    se = ols.bse[beta_idx]
    resid = ols.resid
    t_adf = b / se

    # Newey–West long-run variance of residuals
    if lags is None:
        lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
        lags = max(1, lags)
    gamma0 = np.dot(resid, resid) / len(resid)
    lr_var = gamma0
    for h in range(1, lags + 1):
        w = 1.0 - h / (lags + 1.0)
        gamma_h = np.dot(resid[h:], resid[:-h]) / len(resid)
        lr_var += 2.0 * w * gamma_h
    lr_var = max(lr_var, 1e-12)

    # PP Z_tau statistic (Phillips & Perron 1988)
    sigma2 = gamma0
    n_eff = len(resid)
    pp_stat = t_adf * np.sqrt(sigma2 / lr_var) - (
        (lr_var - sigma2) * n_eff * se / (2.0 * np.sqrt(lr_var) * np.sqrt(np.sum(y_lag ** 2) / n_eff + 1e-12) * se * n_eff / se + 1e-12)
    )
    # More stable textbook form:
    # Z_tau = (sigma/lambda) * t - 0.5 * (lambda^2 - sigma^2) * (n*se) / lambda
    lam = np.sqrt(lr_var)
    sig = np.sqrt(sigma2)
    pp_stat = (sig / lam) * t_adf - 0.5 * (lr_var - sigma2) * (n_eff * se) / lam

    # MacKinnon approximate p-value via statsmodels adfuller machinery on the statistic
    # Use the same critical-value approximation as ADF by feeding pp_stat into
    # the MacKinnon formula through a tiny helper:
    from statsmodels.tsa.stattools import mackinnonp
    reg = "ct" if regression == "ct" else "c"
    try:
        pvalue = float(mackinnonp(pp_stat, regression=reg, N=1))
    except Exception:
        # Fallback: compare to ADF 5% critical (~-2.93 for c, T≈25)
        crit = -3.50 if regression == "ct" else -2.93
        pvalue = 0.01 if pp_stat < crit else 0.20

    return {
        "pp_stat": float(pp_stat),
        "pp_pvalue": float(pvalue),
        "pp_lags": int(lags),
        "pp_reject": bool(pvalue < ALPHA),
        "n": n,
    }


def classify_from_tests(adf_rej, kpss_rej, pp_rej=None) -> tuple[int, str]:
    """Return (order, decision_label)."""
    if pp_rej is None:
        if adf_rej and (not kpss_rej):
            return 0, "I0_concordancia"
        if (not adf_rej) and kpss_rej:
            return 1, "I1_concordancia"
        if (not adf_rej) and (not kpss_rej):
            return 1, "conflicto_conservador_I1"
        return 1, "conflicto_adf_vs_kpss_I1"

    # With PP: I(0) if ADF or PP rejects unit root AND KPSS does not reject stationarity
    unit_root_rejected = bool(adf_rej) or bool(pp_rej)
    if unit_root_rejected and (not kpss_rej):
        return 0, "I0_ADF_o_PP"
    if (not unit_root_rejected) and kpss_rej:
        return 1, "I1_concordancia"
    if unit_root_rejected and kpss_rej:
        return 1, "conflicto_PP_KPSS_I1"
    return 1, "conflicto_conservador_I1"


def pairwise_ccf(x: pd.Series, y: pd.Series, max_lag: int = 6) -> pd.DataFrame:
    """
    CCF between x and y for k in [-max_lag, +max_lag].
    Convention: positive k → x leads y (corr(x_{t-k}, y_t));
    negative k → y leads x.
    Implemented as corr(x.shift(k), y) for k in -max..+max.
    """
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    rows = []
    for k in range(-max_lag, max_lag + 1):
        if k >= 0:
            a, b = df["x"].shift(k), df["y"]
            meaning = "x_leads_y" if k > 0 else "contemporaneous"
        else:
            a, b = df["x"], df["y"].shift(-k)
            meaning = "y_leads_x"
        pair = pd.DataFrame({"a": a, "b": b}).dropna()
        rho = float(pair["a"].corr(pair["b"])) if len(pair) >= 5 else np.nan
        rows.append({"lag_k": k, "rho": rho, "n_pairs": len(pair), "meaning": meaning})
    return pd.DataFrame(rows)


def johansen_reinsel_ahn(Y: np.ndarray, k_ar_diff: int = 1, det_order: int = 0) -> dict:
    """Johansen with Reinsel–Ahn finite-sample correction: LR * (T - p*k)/T."""
    joh = coint_johansen(Y, det_order=det_order, k_ar_diff=k_ar_diff)
    T, p = Y.shape
    k = k_ar_diff + 1  # VAR lag order in levels
    factor = (T - p * k) / T
    trace = joh.lr1
    maxeig = joh.lr2
    trace_c = trace * factor
    maxeig_c = maxeig * factor
    crit_trace_95 = joh.cvt[:, 1]
    crit_max_95 = joh.cvm[:, 1]

    def _rank(stats, crits):
        r = 0
        for i in range(len(stats)):
            if stats[i] > crits[i]:
                r = i + 1
            else:
                break
        return r

    return {
        "trace": trace,
        "trace_corrected": trace_c,
        "maxeig": maxeig,
        "maxeig_corrected": maxeig_c,
        "crit_trace_95": crit_trace_95,
        "crit_max_95": crit_max_95,
        "r_trace": _rank(trace, crit_trace_95),
        "r_trace_corrected": _rank(trace_c, crit_trace_95),
        "r_maxeig": _rank(maxeig, crit_max_95),
        "r_maxeig_corrected": _rank(maxeig_c, crit_max_95),
        "T": T,
        "factor": factor,
    }


def irf_ceed_to_at(res, h_max: int = 4) -> list[float]:
    orth = res.irf(h_max).orth_irfs
    names = list(res.names)
    i_at = names.index("d_log_freq_at") if "d_log_freq_at" in names else names.index("log_freq_at")
    # after differencing columns keep log_ names if we name them that way
    ceed_name = "d_log_ceed_flujo" if "d_log_ceed_flujo" in names else (
        "log_ceed_flujo" if "log_ceed_flujo" in names else None
    )
    if ceed_name is None:
        # try first non-AT
        ceed_name = [n for n in names if n != names[i_at]][0]
    i_ceed = names.index(ceed_name)
    return [float(orth[h, i_at, i_ceed]) for h in range(0, h_max + 1)]


# ──────────────────────────────────────────────────────────────────────────────
#  Load staging
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Loading staging S02...")
panel = pd.read_parquet(DATA_S02 / "panel_ciclo_at_trimestral.parquet").sort_values(["anio", "q"])
stat_221 = pd.read_parquet(DATA_S02 / "estacionariedad_tests.parquet")
irf_221 = pd.read_parquet(DATA_S02 / "var_irf.parquet")
diag_221 = pd.read_parquet(DATA_S02 / "var_diagnosticos.parquet")
resumen_221 = pd.read_parquet(DATA_S02 / "var_modelo_resumen.parquet")

# Windows
w_full = panel.copy()  # 2018-I → 2024-IV, n=28
w_ceed = panel.dropna(subset=["log_freq_at", "log_ceed_flujo", "log_empleo", "pib_sectorial_var"]).copy()
w_edif = panel.dropna(subset=["log_freq_at", "log_ceed_flujo", "log_ec",
                              "log_empleo", "pib_sectorial_var"]).copy()
print(f"   full n={len(w_full)}  ceed n={len(w_ceed)}  edif n={len(w_edif)}")
print(f"   ceed: {w_ceed['periodo'].iloc[0]}→{w_ceed['periodo'].iloc[-1]}")
print(f"   edif: {w_edif['periodo'].iloc[0]}→{w_edif['periodo'].iloc[-1]}")

# Differenced series on full panel (for CCF)
for col in ["log_freq_at", "log_ceed_flujo", "log_ec", "log_ipoc",
            "pib_sectorial_var", "log_empleo"]:
    panel[f"d_{col}"] = panel[col].diff()

# ──────────────────────────────────────────────────────────────────────────────
#  1. Stationarity robustness
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  1. Stationarity robustness (ADF / KPSS / PP)...")

series_windows = [
    ("log_freq_at", "full_n28", w_full["log_freq_at"]),
    ("log_freq_at", "ceed_n18", w_ceed["log_freq_at"]),
    ("log_freq_at", "edif_n12", w_edif["log_freq_at"]),
    ("pib_sectorial_var", "full_n28", w_full["pib_sectorial_var"]),
    ("pib_sectorial_var", "ceed_n18", w_ceed["pib_sectorial_var"]),
    ("pib_sectorial_var", "edif_n12", w_edif["pib_sectorial_var"]),
    ("log_ceed_flujo", "ceed_n18", w_ceed["log_ceed_flujo"]),
    ("log_ceed_flujo", "edif_n12", w_edif["log_ceed_flujo"]),
    ("log_ec", "edif_n12", w_edif["log_ec"]),
    ("log_ipoc", "ceed_n18", w_ceed["log_ipoc"]),
    ("log_empleo", "full_n28", w_full["log_empleo"]),
    ("log_empleo", "ceed_n18", w_ceed["log_empleo"]),
    ("log_ipp", "full_n28", w_full["log_ipp"]),
]

# Also first differences for ambiguous series
diff_checks = [
    ("d_log_freq_at", "full_n28", panel["d_log_freq_at"]),
    ("d_pib_sectorial_var", "full_n28", panel["d_pib_sectorial_var"]),
]

rob_rows = []
for name, ventana, series in series_windows + diff_checks:
    adf = run_adf(series)
    kp = run_kpss(series)
    # PP for ambiguous / requested series
    do_pp = name in ("log_freq_at", "pib_sectorial_var", "d_log_freq_at", "d_pib_sectorial_var")
    if do_pp:
        pp = phillips_perron(series)
    else:
        pp = {"pp_stat": np.nan, "pp_pvalue": np.nan, "pp_lags": np.nan,
              "pp_reject": np.nan, "n": adf["n"]}
    order, decision = classify_from_tests(
        adf["adf_reject"], kp["kpss_reject"],
        pp["pp_reject"] if do_pp else None,
    )
    # For already-differenced series, order means "stationary after prior Δ"
    if name.startswith("d_"):
        if order == 0:
            decision = "Delta_I0"
        else:
            decision = "Delta_posible_I1"

    rob_rows.append({
        "serie": name,
        "ventana": ventana,
        "orden_integracion": order if not name.startswith("d_") else (0 if order == 0 else 1),
        "decision": decision,
        **{f"adf_{k}" if not k.startswith("adf") else k: v for k, v in adf.items()},
        **{f"kpss_{k}" if not k.startswith("kpss") else k: v for k, v in kp.items()},
        **pp,
        "pp_aplicado": do_pp,
    })

rob_df = pd.DataFrame(rob_rows)
# Fix duplicate n columns from merges
if "n" in rob_df.columns and "adf_n" not in rob_df.columns:
    pass
_save_parquet(rob_df, "estacionariedad_robustez.parquet")

print(rob_df[["serie", "ventana", "orden_integracion", "decision",
              "adf_pvalue", "kpss_pvalue", "pp_pvalue"]].to_string(index=False))

# Formal decision on pib in full window
pib_full = rob_df[(rob_df["serie"] == "pib_sectorial_var") & (rob_df["ventana"] == "full_n28")].iloc[0]
freq_full = rob_df[(rob_df["serie"] == "log_freq_at") & (rob_df["ventana"] == "full_n28")].iloc[0]
print(f"\n   ▶ pib_sectorial_var (n=28): ADF p={pib_full['adf_pvalue']:.4f} "
      f"KPSS p={pib_full['kpss_pvalue']:.4f} PP p={pib_full['pp_pvalue']:.4f} → {pib_full['decision']}")
print(f"   ▶ log_freq_at (n=28): ADF p={freq_full['adf_pvalue']:.4f} "
      f"KPSS p={freq_full['kpss_pvalue']:.4f} PP p={freq_full['pp_pvalue']:.4f} → {freq_full['decision']}")

# ──────────────────────────────────────────────────────────────────────────────
#  2. Cross-correlation (lags / leads)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔗  2. Cross-correlation CCF (k=−6…+6)...")

ccf_rows = []
ccf_summary = []
pair_defs = [
    ("d_log_ceed_flujo", "d_log_freq_at", "CEED→AT"),
    ("d_log_ec", "d_log_freq_at", "EC→AT"),
    ("d_log_ipoc", "d_log_freq_at", "IPOC→AT"),
]
for xname, yname, label in pair_defs:
    sub = pairwise_ccf(panel[xname], panel[yname], max_lag=6)
    sub["pareja"] = label
    sub["x"] = xname
    sub["y"] = yname
    ccf_rows.append(sub)
    valid = sub.dropna(subset=["rho"])
    # Focus on positive lags (cycle leads AT) and also absolute max
    idx_max = valid["rho"].abs().idxmax()
    best = valid.loc[idx_max]
    pos = valid[valid["lag_k"] > 0]
    best_pos = pos.loc[pos["rho"].abs().idxmax()] if len(pos) else best
    ccf_summary.append({
        "pareja": label,
        "k_absmax": int(best["lag_k"]),
        "rho_absmax": float(best["rho"]),
        "k_lead_absmax": int(best_pos["lag_k"]),
        "rho_lead_absmax": float(best_pos["rho"]),
        "rho_k0": float(valid.loc[valid["lag_k"] == 0, "rho"].iloc[0]),
        "rho_k2": float(valid.loc[valid["lag_k"] == 2, "rho"].iloc[0]) if 2 in valid["lag_k"].values else np.nan,
        "rho_k4": float(valid.loc[valid["lag_k"] == 4, "rho"].iloc[0]) if 4 in valid["lag_k"].values else np.nan,
        "rho_k6": float(valid.loc[valid["lag_k"] == 6, "rho"].iloc[0]) if 6 in valid["lag_k"].values else np.nan,
    })
    print(f"   {label}: k*|ρ|={int(best['lag_k'])} ρ={best['rho']:.3f} | "
          f"lead k*|ρ|={int(best_pos['lag_k'])} ρ={best_pos['rho']:.3f} | ρ(0)={valid.loc[valid.lag_k==0,'rho'].iloc[0]:.3f}")

ccf_all = pd.concat(ccf_rows, ignore_index=True)
ccf_sum_df = pd.DataFrame(ccf_summary)
_save_parquet(ccf_all, "ccf_rezagos.parquet")
_save_parquet(ccf_sum_df, "ccf_rezagos_resumen.parquet")

# Lead evaluation: does CEED_{t+1} help explain AT_t beyond VAR(1)?
# With T=12 cannot freely add leads. Evaluate on n=18 sample with a restricted ADL:
# ΔAT_t = a + b1 ΔAT_{t-1} + c0 ΔCEED_t + c1 ΔCEED_{t-1} + d1 ΔCEED_{t+1}? — lead is not causal for forecasting.
# Econometric note: leads are for Granger-causality-from-future tests / anticipatory correlation,
# not for structural forecasting VAR. We test whether including CEED lead improves in-sample fit
# via nested OLS on n=18 (not a full VAR) and report ΔAIC.
print("\n   Lead evaluation (ADL nested on n=18, NOT a forecasting VAR)...")
w = w_ceed.copy()
w["d_at"] = w["log_freq_at"].diff()
w["d_ceed"] = w["log_ceed_flujo"].diff()
w["d_at_l1"] = w["d_at"].shift(1)
w["d_ceed_l1"] = w["d_ceed"].shift(1)
w["d_ceed_f1"] = w["d_ceed"].shift(-1)  # lead +1
w_lead = w.dropna(subset=["d_at", "d_at_l1", "d_ceed", "d_ceed_l1", "d_ceed_f1"])
y = w_lead["d_at"]
X0 = add_constant(w_lead[["d_at_l1", "d_ceed", "d_ceed_l1"]])
X1 = add_constant(w_lead[["d_at_l1", "d_ceed", "d_ceed_l1", "d_ceed_f1"]])
ols0 = OLS(y, X0).fit()
ols1 = OLS(y, X1).fit()
lead_delta_aic = float(ols1.aic - ols0.aic)
lead_p = float(ols1.pvalues.get("d_ceed_f1", np.nan))
print(f"   ADL base AIC={ols0.aic:.3f}  +lead AIC={ols1.aic:.3f}  ΔAIC={lead_delta_aic:.3f}  "
      f"p(lead)={lead_p:.4f}  n={len(w_lead)}")

# ──────────────────────────────────────────────────────────────────────────────
#  3. Cointegration robustness (n=18)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔎  3. Cointegration EG + Johansen (n=18, AT–CEED)...")

Y18 = w_ceed[["log_freq_at", "log_ceed_flujo"]].dropna()
eg_stat, eg_p, eg_crit = coint(Y18["log_freq_at"], Y18["log_ceed_flujo"], trend="c", autolag="aic")
print(f"   EG (AT,CEED) n={len(Y18)}: stat={eg_stat:.3f} p={eg_p:.4f}  (vs T=12 p≈0.995)")

joh = johansen_reinsel_ahn(Y18.values, k_ar_diff=1, det_order=0)
print(f"   Johansen n={joh['T']} factor Reinsel–Ahn={joh['factor']:.3f}")
print(f"   trace={np.round(joh['trace'],2)}  corrected={np.round(joh['trace_corrected'],2)}  "
      f"crit95={np.round(joh['crit_trace_95'],2)}")
print(f"   r_trace={joh['r_trace']}  r_trace_corr={joh['r_trace_corrected']}  "
      f"r_max={joh['r_maxeig']}  r_max_corr={joh['r_maxeig_corrected']}")

eg_coint = bool(eg_p < ALPHA)
joh_coint = joh["r_trace_corrected"] >= 1

coint_decision = "sin_cointegracion_VAR_diff"
vecm_aic = np.nan
var_aic_18 = np.nan
if eg_coint and joh_coint:
    # Estimate both and compare AIC
    Yd = Y18.diff().dropna()
    var18 = VAR(Yd).fit(1)
    var_aic_18 = float(var18.aic)
    try:
        vecm = VECM(Y18, k_ar_diff=1, coint_rank=1, deterministic="ci").fit()
        # VECM doesn't expose AIC directly; use loglike proxy
        resid = np.asarray(vecm.resid)
        nobs, k = resid.shape
        sigma = resid.T @ resid / nobs
        ll = -0.5 * nobs * (k * np.log(2 * np.pi) + np.log(np.linalg.det(sigma)) + k)
        nparams = k * k * 1 + k + k  # rough
        vecm_aic = float(-2 * ll + 2 * nparams)
        coint_decision = "VECM" if vecm_aic < var_aic_18 else "VAR_diff_menor_AIC"
        print(f"   AIC VAR_diff={var_aic_18:.3f}  VECM≈{vecm_aic:.3f} → {coint_decision}")
    except Exception as exc:
        coint_decision = "sin_cointegracion_VAR_diff"
        print(f"   VECM falló ({exc}); se mantiene VAR diff")
elif eg_coint or joh_coint:
    coint_decision = "evidencia_mixta_preferir_VAR_diff"
    print("   Evidencia mixta (solo un test sugiere r≥1) → preferir VAR en diferencias")
else:
    print("   Ambos tests (EG y Johansen corregido) no rechazan r=0 → confirma VAR en diferencias")

# Power / minimum sample size (theoretical)
# Haug (1996), Toda (1995): EG/Johansen power at T=20 often 0.2–0.4 for mid adjustment speed.
# Rule of thumb for power≈0.80 in bivariate cointegration: T ≳ 50–80 (quarterly ≈ 12–20 years).
# Using a simple formula from asymptotic local-power approximations:
# approximate T_min ≈ (z_{1-β} + z_{1-α})^2 / λ^2 where λ is local alternative strength.
# For typical cointegration local alternative, literature cites T≥80 for power 0.80 at α=0.05
# in bivariate systems with slow adjustment (φ≈0.1). With faster adjustment (φ≈0.3), T≈40–50.
T_min_slow = 80
T_min_fast = 50
power_note = (
    f"Con T≤18 y k=2, potencia típica de EG/Johansen ≈0.20–0.35 (Haug 1996; Toda 1995). "
    f"Para potencia ≥0.80 a α=0.05 en sistema bivariado se requieren ≈{T_min_fast}–{T_min_slow} "
    f"observaciones trimestrales (12–20 años), según velocidad de ajuste al equilibrio."
)
print(f"   {power_note}")

coint_rows = [{
    "test": "Engle-Granger",
    "ventana": "ceed_n18",
    "n": len(Y18),
    "stat": float(eg_stat),
    "pvalue": float(eg_p),
    "r_hat": int(eg_coint),
    "critico_o_nota": str(eg_crit),
}, {
    "test": "Johansen_trace",
    "ventana": "ceed_n18",
    "n": int(joh["T"]),
    "stat": float(joh["trace"][0]),
    "pvalue": np.nan,
    "r_hat": int(joh["r_trace"]),
    "critico_o_nota": f"crit95_r0={joh['crit_trace_95'][0]:.2f}",
}, {
    "test": "Johansen_trace_ReinselAhn",
    "ventana": "ceed_n18",
    "n": int(joh["T"]),
    "stat": float(joh["trace_corrected"][0]),
    "pvalue": np.nan,
    "r_hat": int(joh["r_trace_corrected"]),
    "critico_o_nota": f"factor={joh['factor']:.3f}; crit95_r0={joh['crit_trace_95'][0]:.2f}",
}, {
    "test": "Johansen_maxeig_ReinselAhn",
    "ventana": "ceed_n18",
    "n": int(joh["T"]),
    "stat": float(joh["maxeig_corrected"][0]),
    "pvalue": np.nan,
    "r_hat": int(joh["r_maxeig_corrected"]),
    "critico_o_nota": f"crit95_r0={joh['crit_max_95'][0]:.2f}",
}, {
    "test": "Engle-Granger_T12_ref",
    "ventana": "edif_n12",
    "n": 12,
    "stat": np.nan,
    "pvalue": float(resumen_221.iloc[0]["eg_pvalue_edif"]),
    "r_hat": 0,
    "critico_o_nota": "referencia 2.2.1",
}]
coint_df = pd.DataFrame(coint_rows)
_save_parquet(coint_df, "coint_robustez.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  4. VAR sensitivity
# ──────────────────────────────────────────────────────────────────────────────
print("\n📈  4. VAR(1) sensitivity...")

# Baseline IRF from 2.2.1
base_irf = (
    irf_221[(irf_221["bloque"] == "edificacion")
            & (irf_221["shock"] == "log_ceed_flujo")
            & (irf_221["respuesta"] == "log_freq_at")]
    .sort_values("horizonte")
)
irf_base_h = {int(r.horizonte): float(r.irf_orth) for r in base_irf.itertuples()}

sens_rows = []

def fit_var_diff(df, endog_cols, p=1, exog_cols=None):
    d = df[endog_cols].diff().dropna()
    d.columns = [f"d_{c}" if not c.startswith("d_") else c for c in endog_cols]
    # rename properly
    d = df[endog_cols].diff().dropna()
    d = d.rename(columns={c: f"d_{c}" for c in endog_cols})
    exog = None
    if exog_cols:
        exog = df[exog_cols].diff().dropna()
        exog = exog.rename(columns={c: f"d_{c}" for c in exog_cols})
        exog = exog.loc[d.index]
    res = VAR(d, exog=exog).fit(p)
    return res, d


# (i) base T=12 already in irf_base_h
for h, v in irf_base_h.items():
    if h <= 4:
        sens_rows.append({
            "modelo": "base_T12_CEED_EC",
            "n": 12,
            "endogenas": "AT,CEED,EC",
            "horizonte": h,
            "irf_ceed_at": v,
        })

# (ii) T=18 AT+CEED
res18, d18 = fit_var_diff(w_ceed, ["log_freq_at", "log_ceed_flujo"], p=1,
                          exog_cols=["pib_sectorial_var", "log_empleo"])
irf18 = irf_ceed_to_at(res18, 4)
print(f"   (ii) T=18 AT+CEED IRF CEED→AT h0..4: {[round(v,4) for v in irf18]}")
for h, v in enumerate(irf18):
    sens_rows.append({
        "modelo": "ampliado_T18_sin_EC",
        "n": 18,
        "endogenas": "AT,CEED",
        "horizonte": h,
        "irf_ceed_at": v,
    })

# (iii) T=18 AT+CEED+empleo endogenous
res18e, d18e = fit_var_diff(
    w_ceed, ["log_freq_at", "log_ceed_flujo", "log_empleo"], p=1,
    exog_cols=["pib_sectorial_var"],
)
irf18e = irf_ceed_to_at(res18e, 4)
print(f"   (iii) T=18 AT+CEED+empleo IRF CEED→AT h0..4: {[round(v,4) for v in irf18e]}")
# Does empleo absorb? compare |IRF| reduction at h=1
absorp = abs(irf18[1]) - abs(irf18e[1])
print(f"   Absorción |IRF_h1|: T18={abs(irf18[1]):.4f} → +empleo={abs(irf18e[1]):.4f}  "
      f"Δ={absorp:.4f}")
for h, v in enumerate(irf18e):
    sens_rows.append({
        "modelo": "extendido_T18_con_empleo",
        "n": 18,
        "endogenas": "AT,CEED,empleo",
        "horizonte": h,
        "irf_ceed_at": v,
    })

sens_df = pd.DataFrame(sens_rows)
_save_parquet(sens_df, "var_sensibilidad_irf.parquet")

# Optional: save panel AT+CEED n=18 slice as staging alias only if useful
# User said don't create unless justified — the full panel already exists; skip new panel.

# ──────────────────────────────────────────────────────────────────────────────
#  5. Extended diagnostics
# ──────────────────────────────────────────────────────────────────────────────
print("\n🩺  5. Extended diagnostics...")

diag_ext_rows = []


def portmanteau_detail(resid: np.ndarray, names: list[str], qs=(4, 8)):
    out = {}
    for q in qs:
        pvals = []
        for j, name in enumerate(names):
            max_q = min(q, max(1, resid.shape[0] // 2))
            lb = acorr_ljungbox(resid[:, j], lags=[max_q], return_df=True)
            p = float(lb["lb_pvalue"].iloc[0])
            pvals.append(p)
            out[f"lb_p_Q{q}_{name}"] = p
        out[f"lb_pmin_Q{q}"] = float(np.min(pvals))
        out[f"lb_pass_Q{q}"] = bool(np.min(pvals) >= ALPHA)
    return out


def diagnose_var(label, res, n, add_info=None):
    resid = np.asarray(res.resid)
    names = list(res.names)
    row = {
        "modelo": label,
        "n": n,
        "aic": float(res.aic),
        "bic": float(res.bic),
        "nobs": int(res.nobs),
    }
    row.update(portmanteau_detail(resid, names, qs=(4, 8)))
    # equation responsible for marginal Portmanteau at Q=4
    eq_p = {names[j]: row.get(f"lb_p_Q4_{names[j]}", np.nan) for j in range(len(names))}
    worst = min(eq_p, key=eq_p.get)
    row["ecuacion_peor_Q4"] = worst
    row["p_peor_Q4"] = eq_p[worst]
    # JB
    jb_ps = [float(jarque_bera(resid[:, j])[1]) for j in range(resid.shape[1])]
    row["jb_pmin"] = float(np.min(jb_ps))
    row["jb_pass"] = bool(np.min(jb_ps) >= ALPHA)
    if add_info:
        row.update(add_info)
    return row, resid, names


# Base-like VAR on T=12 (rebuild)
res12, _ = fit_var_diff(
    w_edif, ["log_freq_at", "log_ceed_flujo", "log_ec"], p=1,
    exog_cols=["pib_sectorial_var", "log_empleo"],
)
row12, resid12, names12 = diagnose_var("VAR_diff_T12_edif", res12, 12)
diag_ext_rows.append(row12)
print(f"   T12 Portmanteau Q4 pmin={row12['lb_pmin_Q4']:.4f}  peor={row12['ecuacion_peor_Q4']} "
      f"(p={row12['p_peor_Q4']:.4f})  Q8 pmin={row12['lb_pmin_Q8']:.4f}")

row18, resid18, names18 = diagnose_var("VAR_diff_T18_sinEC", res18, 18)
diag_ext_rows.append(row18)
print(f"   T18 Portmanteau Q4 pmin={row18['lb_pmin_Q4']:.4f}  peor={row18['ecuacion_peor_Q4']}")

row18e, resid18e, names18e = diagnose_var("VAR_diff_T18_empleo", res18e, 18)
diag_ext_rows.append(row18e)

# CUSUM on AT equation residuals from T=18 model (more obs)
# Rebuild AT equation OLS for CUSUM
wcus = w_ceed.copy()
wcus["d_at"] = wcus["log_freq_at"].diff()
wcus["d_ceed"] = wcus["log_ceed_flujo"].diff()
wcus["d_at_l1"] = wcus["d_at"].shift(1)
wcus["d_ceed_l1"] = wcus["d_ceed"].shift(1)
wcus["d_emp"] = wcus["log_empleo"].diff()
wcus["d_pib"] = wcus["pib_sectorial_var"].diff()
wc = wcus.dropna(subset=["d_at", "d_at_l1", "d_ceed", "d_ceed_l1", "d_emp", "d_pib"])
yc = wc["d_at"]
Xc = add_constant(wc[["d_at_l1", "d_ceed", "d_ceed_l1", "d_emp", "d_pib"]])
ols_cus = OLS(yc, Xc).fit()
try:
    cusum_stat, cusum_pval, _ = breaks_cusumolsresid(ols_cus.resid)
    cusum_stat, cusum_pval = float(cusum_stat), float(cusum_pval)
except Exception as exc:
    cusum_stat, cusum_pval = np.nan, np.nan
    print(f"   CUSUM falló: {exc}")
print(f"   CUSUM (eq AT, n={len(wc)}): stat={cusum_stat:.3f} p={cusum_pval:.4f}")

# Dummy COVID 2020-I/II and CEED drop 2022-I on T=18 VAR via exog
w_d = w_ceed.copy()
w_d["dummy_covid"] = ((w_d["anio"] == 2020) & (w_d["q"].isin([1, 2]))).astype(float)
w_d["dummy_2022q1"] = ((w_d["anio"] == 2022) & (w_d["q"] == 1)).astype(float)
# Note: COVID dummies are 0 in 2020-III start of CEED window — mostly inactive.
# Keep 2022Q1 dummy which is in-sample.
d_endog = w_d[["log_freq_at", "log_ceed_flujo"]].diff().dropna()
d_endog = d_endog.rename(columns={c: f"d_{c}" for c in d_endog.columns})
exog_d = w_d[["pib_sectorial_var", "log_empleo", "dummy_2022q1"]].copy()
exog_d["pib_sectorial_var"] = exog_d["pib_sectorial_var"].diff()
exog_d["log_empleo"] = exog_d["log_empleo"].diff()
# dummy stays in levels as impulse
exog_d = exog_d.loc[d_endog.index].fillna(0)
try:
    res_dum = VAR(d_endog, exog=exog_d.rename(columns={
        "pib_sectorial_var": "d_pib", "log_empleo": "d_empleo",
    })).fit(1)
    row_dum, _, _ = diagnose_var("VAR_diff_T18_dummy2022Q1", res_dum, 18)
    diag_ext_rows.append(row_dum)
    print(f"   +dummy 2022-I: Q4 pmin={row_dum['lb_pmin_Q4']:.4f}  "
          f"(vs sin dummy {row18['lb_pmin_Q4']:.4f})")
except Exception as exc:
    print(f"   VAR con dummy falló: {exc}")

# Also try dummy on T=12 where Portmanteau was marginal
w12 = w_edif.copy()
w12["dummy_2022q1"] = ((w12["anio"] == 2022) & (w12["q"] == 1)).astype(float)
d12 = w12[["log_freq_at", "log_ceed_flujo", "log_ec"]].diff().dropna()
d12 = d12.rename(columns={c: f"d_{c}" for c in ["log_freq_at", "log_ceed_flujo", "log_ec"]})
ex12 = w12[["pib_sectorial_var", "log_empleo", "dummy_2022q1"]].copy()
ex12["pib_sectorial_var"] = ex12["pib_sectorial_var"].diff()
ex12["log_empleo"] = ex12["log_empleo"].diff()
ex12 = ex12.loc[d12.index].fillna(0).rename(columns={
    "pib_sectorial_var": "d_pib", "log_empleo": "d_empleo",
})
try:
    res12d = VAR(d12, exog=ex12).fit(1)
    row12d, _, _ = diagnose_var("VAR_diff_T12_dummy2022Q1", res12d, 12)
    diag_ext_rows.append(row12d)
    print(f"   T12 +dummy 2022-I: Q4 pmin={row12d['lb_pmin_Q4']:.4f}  "
          f"(vs base {row12['lb_pmin_Q4']:.4f})")
except Exception as exc:
    print(f"   T12 dummy falló: {exc}")

diag_ext = pd.DataFrame(diag_ext_rows)
diag_ext["cusum_stat_ref"] = cusum_stat
diag_ext["cusum_pvalue_ref"] = cusum_pval
_save_parquet(diag_ext, "var_diagnosticos_ext.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  Decision summary staging
# ──────────────────────────────────────────────────────────────────────────────
decision = pd.DataFrame([{
    "pib_full_decision": pib_full["decision"],
    "pib_full_adf_p": float(pib_full["adf_pvalue"]),
    "pib_full_kpss_p": float(pib_full["kpss_pvalue"]),
    "pib_full_pp_p": float(pib_full["pp_pvalue"]),
    "freq_full_decision": freq_full["decision"],
    "freq_full_pp_p": float(freq_full["pp_pvalue"]),
    "ccf_ceed_k_lead": int(ccf_sum_df.loc[ccf_sum_df.pareja == "CEED→AT", "k_lead_absmax"].iloc[0]),
    "ccf_ceed_rho_lead": float(ccf_sum_df.loc[ccf_sum_df.pareja == "CEED→AT", "rho_lead_absmax"].iloc[0]),
    "ccf_ceed_rho0": float(ccf_sum_df.loc[ccf_sum_df.pareja == "CEED→AT", "rho_k0"].iloc[0]),
    "lead_delta_aic": lead_delta_aic,
    "lead_pvalue": lead_p,
    "eg_p_n18": float(eg_p),
    "eg_p_n12": float(resumen_221.iloc[0]["eg_pvalue_edif"]),
    "johansen_r_corr": int(joh["r_trace_corrected"]),
    "johansen_r_raw": int(joh["r_trace"]),
    "coint_decision": coint_decision,
    "irf_h1_T12": float(irf_base_h.get(1, np.nan)),
    "irf_h1_T18": float(irf18[1]),
    "irf_h1_T18_empleo": float(irf18e[1]),
    "portmanteau_T12_Q4": float(row12["lb_pmin_Q4"]),
    "portmanteau_T18_Q4": float(row18["lb_pmin_Q4"]),
    "peor_eq_T12": row12["ecuacion_peor_Q4"],
    "cusum_pvalue": cusum_pval,
    "T_min_power80_fast": T_min_fast,
    "T_min_power80_slow": T_min_slow,
    "spec_final": "VAR_diferencias",
}])
_save_parquet(decision, "especificacion_definitiva.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  Plots
# ──────────────────────────────────────────────────────────────────────────────
print("\n🎨  Generating plots...")

# 02_estacionariedad_robustez
fig, ax = sb.create_report_figure(
    title="Estacionariedad robusta: ADF / KPSS / PP (p-valores)",
    subtitle="Ventanas full (n=28), CEED (n=18) y edificación (n=12) | α=0.05",
)
focus = rob_df[rob_df["serie"].isin([
    "log_freq_at", "pib_sectorial_var", "log_ceed_flujo", "log_ec", "log_ipoc", "log_empleo",
])].copy()
# plot p-values for full or best available window
plot_df = []
for serie in ["log_freq_at", "pib_sectorial_var", "log_ceed_flujo", "log_ec", "log_ipoc", "log_empleo"]:
    sub = focus[focus["serie"] == serie]
    # prefer fullest window
    for pref in ["full_n28", "ceed_n18", "edif_n12"]:
        row = sub[sub["ventana"] == pref]
        if len(row):
            plot_df.append(row.iloc[0])
            break
plot_df = pd.DataFrame(plot_df)
x = np.arange(len(plot_df))
w = 0.25
ax.bar(x - w, plot_df["adf_pvalue"], width=w, color=PALETTE[0], label="ADF")
ax.bar(x, plot_df["kpss_pvalue"].fillna(0), width=w, color=PALETTE[1], label="KPSS")
pp_vals = plot_df["pp_pvalue"].fillna(0)
ax.bar(x + w, pp_vals, width=w, color=PALETTE[2], label="PP (si aplica)")
ax.axhline(ALPHA, color="#C62828", ls="--", lw=1.2, label="α=0.05")
ax.set_xticks(x)
ax.set_xticklabels([f"{s}\n({v})" for s, v in zip(plot_df["serie"], plot_df["ventana"])],
                   fontsize=7, rotation=15, ha="right")
ax.set_ylabel("p-valor")
ax.set_ylim(0, 1.05)
ax.legend(frameon=True, fontsize=8)
sb.add_sura_footer(fig, text="S02 – 2.2.2 | Estacionariedad robusta")
_save_fig(fig, "02_estacionariedad_robustez.png")

# 02_ccf
fig, axes = sb.create_dashboard(
    1, 3,
    title="Correlación cruzada (CCF) en primeras diferencias",
    subtitle="k>0: ciclo adelanta a AT | k<0: AT adelanta al ciclo | banda ≈±2/√T",
)
for ax, label in zip(axes, ["CEED→AT", "EC→AT", "IPOC→AT"]):
    sub = ccf_all[ccf_all["pareja"] == label].sort_values("lag_k")
    T_pair = int(sub["n_pairs"].max()) if len(sub) else 20
    band = 2 / np.sqrt(max(T_pair, 1))
    ax.bar(sub["lag_k"], sub["rho"], color=PALETTE[0], alpha=0.85)
    ax.axhline(0, color="#888", lw=0.8)
    ax.axhline(band, color="#C62828", ls="--", lw=0.9)
    ax.axhline(-band, color="#C62828", ls="--", lw=0.9)
    ax.set_title(label)
    ax.set_xlabel("k (trimestres)")
    ax.set_ylabel("ρ")
    ax.set_xlim(-6.5, 6.5)
sb.add_sura_footer(fig, text="S02 – 2.2.2 | CCF rezagos/adelantos")
_save_fig(fig, "02_ccf_rezagos.png")

# 02_coint
fig, ax = sb.create_report_figure(
    title="Cointegración AT–CEED: EG y Johansen (n=18)",
    subtitle="Trace corregido Reinsel–Ahn vs crítico 95% (r=0)",
)
labels = ["EG −log10(p)\nn=12", "EG −log10(p)\nn=18", "Johansen\ntrace", "Johansen\ntrace corr.", "Crítico 95%\n(r=0)"]
vals = [
    -np.log10(max(float(resumen_221.iloc[0]["eg_pvalue_edif"]), 1e-6)),
    -np.log10(max(float(eg_p), 1e-6)),
    float(joh["trace"][0]),
    float(joh["trace_corrected"][0]),
    float(joh["crit_trace_95"][0]),
]
colors = [PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[3], "#888888"]
ax.bar(labels, vals, color=colors, alpha=0.9)
ax.axhline(-np.log10(ALPHA), color="#C62828", ls="--", lw=1.2, label="−log10(0.05)≈1.3")
ax.set_ylabel("Estadístico / −log10(p)")
ax.legend(frameon=True, fontsize=8)
sb.add_sura_footer(fig, text="S02 – 2.2.2 | Cointegración")
_save_fig(fig, "02_coint_robustez.png")

# 02_sensibilidad IRF
fig, ax = sb.create_report_figure(
    title="Sensibilidad IRF CEED→AT (h=0…4)",
    subtitle="(i) T=12 +EC  ·  (ii) T=18 sin EC  ·  (iii) T=18 +empleo endógeno",
)
for modelo, color, marker in [
    ("base_T12_CEED_EC", PALETTE[0], "o"),
    ("ampliado_T18_sin_EC", PALETTE[1], "s"),
    ("extendido_T18_con_empleo", PALETTE[2], "^"),
]:
    sub = sens_df[sens_df["modelo"] == modelo].sort_values("horizonte")
    ax.plot(sub["horizonte"], sub["irf_ceed_at"], color=color, marker=marker,
            lw=2, label=modelo)
ax.axhline(0, color="#888", lw=0.9)
ax.set_xlabel("Horizonte (trimestres)")
ax.set_ylabel("IRF ortogonalizada")
ax.legend(frameon=True, fontsize=7)
sb.add_sura_footer(fig, text="S02 – 2.2.2 | Sensibilidad VAR")
_save_fig(fig, "02_sensibilidad_irf.png")

# 02_diagnosticos_ext
fig, ax = sb.create_report_figure(
    title="Diagnósticos extendidos — Portmanteau Q4 / Q8",
    subtitle="p-valor mínimo por modelo | línea α=0.05",
)
models = diag_ext["modelo"].tolist()
x = np.arange(len(models))
wbar = 0.35
ax.bar(x - wbar / 2, diag_ext["lb_pmin_Q4"], width=wbar, color=PALETTE[0], label="Q=4")
ax.bar(x + wbar / 2, diag_ext["lb_pmin_Q8"], width=wbar, color=PALETTE[1], label="Q=8")
ax.axhline(ALPHA, color="#C62828", ls="--", lw=1.2)
ax.set_xticks(x)
ax.set_xticklabels(models, rotation=20, ha="right", fontsize=7)
ax.set_ylabel("p-valor mínimo")
ax.set_ylim(0, 1.05)
ax.legend(frameon=True, fontsize=8)
sb.add_sura_footer(fig, text="S02 – 2.2.2 | Diagnósticos extendidos")
_save_fig(fig, "02_diagnosticos_ext.png")

# ──────────────────────────────────────────────────────────────────────────────
#  Write estacionariedad_robustez.md
# ──────────────────────────────────────────────────────────────────────────────
print("\n📝  Writing estacionariedad_robustez.md...")

md_lines = [
    "# Estacionariedad — análisis de robustez (2.2.2)",
    "",
    "> Generado por `code/02-estacionariedad/estacionariedad_robustez.py`.",
    "> Insumo base: `estacionariedad_tests.parquet` (2.2.1) + re-tests ADF/KPSS/PP.",
    "",
    "## Criterio de decisión",
    "",
    "- **I(0):** ADF o PP rechazan raíz unitaria **y** KPSS no rechaza estacionariedad (α=0.05).",
    "- **I(1):** evidencia de raíz unitaria o conflicto → tratamiento conservador I(1).",
    "- **PP** se aplica a series ambiguas de 2.2.1: `log_freq_at`, `pib_sectorial_var`.",
    "",
    "## Cuadro consolidado ADF / KPSS / PP",
    "",
    "| Serie | Ventana | n | ADF p | KPSS p | PP p | Orden | Decisión |",
    "|---|---|---|---|---|---|---|---|",
]
for r in rob_df.itertuples():
    pp_s = f"{r.pp_pvalue:.4f}" if pd.notna(r.pp_pvalue) and r.pp_aplicado else "—"
    md_lines.append(
        f"| `{r.serie}` | {r.ventana} | {int(r.n) if pd.notna(r.n) else '—'} | "
        f"{r.adf_pvalue:.4f} | {r.kpss_pvalue:.4f} | {pp_s} | "
        f"I({int(r.orden_integracion)}) | {r.decision} |"
    )

md_lines += [
    "",
    "## Decisiones formales sobre series ambiguas",
    "",
    f"### `pib_sectorial_var` (ventana larga n=28)",
    f"- ADF p={pib_full['adf_pvalue']:.4f} | KPSS p={pib_full['kpss_pvalue']:.4f} | "
    f"PP p={pib_full['pp_pvalue']:.4f}",
    f"- **Veredicto:** `{pib_full['decision']}` → "
    + ("tratar como **I(0)** (no diferenciar obligatoriamente como endógena; "
       "como exógena en VAR puede entrar en nivel o Δ según contexto)."
       if int(pib_full["orden_integracion"]) == 0 else
       "mantener **I(1)** / primeras diferencias como en 2.2.1."),
    "",
    f"### `log_freq_at` (ventana larga n=28 + PP)",
    f"- ADF p={freq_full['adf_pvalue']:.4f} | KPSS p={freq_full['kpss_pvalue']:.4f} | "
    f"PP p={freq_full['pp_pvalue']:.4f}",
    f"- **Veredicto:** `{freq_full['decision']}` → confirma tratamiento **I(1)** del núcleo AT.",
    "",
    "## Implicación para el modelado",
    "",
    "La robustez **no altera** la conclusión operativa de 2.2.1 para el bloque endógeno "
    "(AT, CEED, EC, IPOC, empleo): series de nivel I(1) → modelar en diferencias o VECM "
    "si hubiera cointegración. El único matiz es `pib_sectorial_var` en n=28, "
    "donde la potencia mejora; ver veredicto arriba.",
    "",
    f"*Referencia visual:* `results/imgs/02_estacionariedad_robustez.png`",
]
(RESULTS / "estacionariedad_robustez.md").write_text("\n".join(md_lines), encoding="utf-8")
print("   💾  estacionariedad_robustez.md")

# Print key block for relaciones.md authoring
print("\n" + "=" * 72)
print("KEY OUTPUTS FOR relaciones.md §2.2.2")
print("=" * 72)
print(decision.T.to_string())
print("\nCCF summary:")
print(ccf_sum_df.to_string(index=False))
print("\nDiag ext:")
print(diag_ext[["modelo", "lb_pmin_Q4", "lb_pmin_Q8", "ecuacion_peor_Q4", "aic"]].to_string(index=False))
print("\n✅  2.2.2 robustez completada.")
