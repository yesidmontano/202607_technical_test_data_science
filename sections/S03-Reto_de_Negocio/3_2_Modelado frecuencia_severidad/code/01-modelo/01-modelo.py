"""
Modelado frecuencia–severidad – Costo esperado de siniestralidad
================================================================
Sección: S03 – Reto de Negocio
Subsección: 3.2 – Modelado frecuencia / severidad
Proceso: 3.2.1 – Estimación de costo esperado por empresa y clase

Descripción:
    Estima el costo esperado de siniestralidad con arquitectura actuarial
    frecuencia × severidad, alineada a hallazgos S01 y supuestos 3.1.2:

      · Frecuencia (empresa-año): Binomial Negativa con offset log(n_trabajadores)
            n_siniestros ~ C(clase_riesgo) + C(segmento) + C(sector) + log1p(lag_n)
      · Severidad (siniestro, costo): Lognormal (OLS en log), modelos separados
            AT / EL  (P6)  condicionados a clase × tamaño × gravedad (S1)
            log(costo_total_w) ~ C(clase_riesgo) + C(segmento) + C(gravedad)
            Para pricing a nivel empresa se marginaliza P(gravedad|clase, tipo)
            y P(tipo|clase) estimados en train.
      · Pure premium:
            E[Costo_i] = E[N_i] × Σ_tipo p(tipo|clase)·Σ_g p(g|clase,tipo)·E[Sev|X,g,tipo]

    Evaluación temporal: train 2019–2023 (requiere lag), holdout 2024.
    Proyección de negocio: features 2024 + lag=n_siniestros_2024 → E[Costo] próximo año.

Inputs (reutilizados):
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S01/siniestros_tratados.parquet
    - data/staging/S03/supuestos_veredicto.parquet          (trazabilidad)

Outputs:
    - results/imgs/01_modelo_*.png
    - results/modelo_*.csv
    - data/staging/S03/modelo_*.parquet
    - results/model_frecuencia_serveridad.md

Uso:
    .venv/bin/python "sections/S03-Reto_de_Negocio/3_2_Modelado frecuencia_severidad/code/01-modelo/01-modelo.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ANIO_HOLDOUT = 2024
ANIOS_TRAIN = list(range(2019, ANIO_HOLDOUT))  # 2019–2023 (lag disponible)

ROOT = Path(__file__).resolve().parents[5]
DATA_S01 = ROOT / "data" / "staging" / "S01"
DATA_S03 = ROOT / "data" / "staging" / "S03"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_S03.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

SEG_ORDER = ["Micro (≤10)", "Pequeña (11-50)", "Mediana (51-200)", "Grande (>200)"]
FREQ_FORMULA = (
    "n_siniestros ~ C(clase_riesgo) + C(segmento) + C(sector) + log_lag_n"
)
SEV_FORMULA = "log_costo ~ C(clase_riesgo) + C(segmento) + C(gravedad)"

print("=" * 70)
print("  S03-3.2.1 | Modelado frecuencia–severidad → costo esperado")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga y panel empresa-año
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando staging...")
emp = pd.read_parquet(DATA_S01 / "empresa_siniestralidad_completa.parquet")
panel = pd.read_parquet(DATA_S01 / "temporal_empresa_anio.parquet")
sin = pd.read_parquet(DATA_S01 / "siniestros_tratados.parquet")
veredicto = pd.read_parquet(DATA_S03 / "supuestos_veredicto.parquet")

print(f"  empresas: {emp.shape} | panel: {panel.shape} | siniestros: {sin.shape}")
print(f"  Supuestos 3.1.2:\n{veredicto[['supuesto', 'veredicto']].to_string(index=False)}")

attrs = emp[[
    "id_empresa", "clase_riesgo", "sector", "segmento",
    "n_trabajadores", "prima_anual", "antiguedad_meses",
]].copy()
attrs["clase_riesgo"] = attrs["clase_riesgo"].astype(int)
attrs["segmento"] = pd.Categorical(attrs["segmento"], categories=SEG_ORDER, ordered=True)

df = panel.merge(
    attrs[["id_empresa", "segmento", "prima_anual", "antiguedad_meses"]],
    on="id_empresa",
    how="left",
)
df = df.sort_values(["id_empresa", "anio"]).reset_index(drop=True)
df["lag_n_siniestros"] = df.groupby("id_empresa")["n_siniestros"].shift(1)
df["log_lag_n"] = np.log1p(df["lag_n_siniestros"].fillna(0.0))
df["n_trab_exp"] = df["n_trabajadores"].clip(lower=1).astype(float)
df["log_exposure"] = np.log(df["n_trab_exp"])
df["clase_riesgo"] = df["clase_riesgo"].astype(int).astype(str)
df["segmento"] = df["segmento"].astype(str)
df["sector"] = df["sector"].astype(str)

# Solo años con lag observado (desde 2019)
df_model = df.loc[df["anio"] >= min(ANIOS_TRAIN)].copy()
train = df_model.loc[df_model["anio"].isin(ANIOS_TRAIN)].copy()
holdout = df_model.loc[df_model["anio"] == ANIO_HOLDOUT].copy()

print(f"\n  Train {ANIOS_TRAIN[0]}–{ANIOS_TRAIN[-1]}: {train.shape[0]:,} filas")
print(f"  Holdout {ANIO_HOLDOUT}:               {holdout.shape[0]:,} filas")

# Persist panel de modelado
panel_out = df_model[[
    "id_empresa", "anio", "n_siniestros", "costo_total", "severidad_media",
    "n_trabajadores", "n_trab_exp", "log_exposure", "clase_riesgo", "sector",
    "segmento", "prima_anual", "lag_n_siniestros", "log_lag_n",
]].copy()
panel_out["split"] = np.where(
    panel_out["anio"] == ANIO_HOLDOUT, "holdout",
    np.where(panel_out["anio"].isin(ANIOS_TRAIN), "train", "other"),
)


# ──────────────────────────────────────────────────
# 2. Modelo de frecuencia (NB)
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  FRECUENCIA – Binomial Negativa + offset log(exposición)")
print("=" * 70)

# Estimar α vía MLE discreto, luego GLM con α fijo (predict limpio con offset)
nb_mle = smf.negativebinomial(
    FREQ_FORMULA, data=train, offset=train["log_exposure"],
).fit(disp=False, maxiter=200)
alpha_hat = float(nb_mle.params["alpha"])
print(f"  α NB (MLE) = {alpha_hat:.4f}")

freq_glm = smf.glm(
    FREQ_FORMULA,
    data=train,
    family=sm.families.NegativeBinomial(alpha=alpha_hat),
    offset=train["log_exposure"],
).fit(cov_type="HC1")

print(f"  Pseudo-LL / AIC (MLE): llf={nb_mle.llf:.1f}  AIC={nb_mle.aic:.1f}")
print(f"  GLM deviance={freq_glm.deviance:.1f}  Pearson χ²={freq_glm.pearson_chi2:.1f}")

# Coeficientes
freq_coefs = (
    pd.DataFrame({
        "parametro": freq_glm.params.index,
        "coef": freq_glm.params.values,
        "ee_hc1": freq_glm.bse.values,
        "z": freq_glm.tvalues.values,
        "p_valor": freq_glm.pvalues.values,
    })
)
freq_coefs["irr"] = np.exp(freq_coefs["coef"])  # incidence rate ratio
freq_coefs["modelo"] = "frecuencia_NB"
freq_coefs["alpha_nb"] = alpha_hat

print("\n  IRR clase de riesgo (vs clase 1):")
for _, r in freq_coefs[freq_coefs["parametro"].str.contains("clase_riesgo")].iterrows():
    print(f"    {r['parametro']}: IRR={r['irr']:.3f} (p={r['p_valor']:.2e})")


def predict_freq(mod, data: pd.DataFrame) -> np.ndarray:
    return np.asarray(mod.predict(data, offset=data["log_exposure"]), dtype=float)


train["freq_pred"] = predict_freq(freq_glm, train)
holdout["freq_pred"] = predict_freq(freq_glm, holdout)


def _reg_metrics(y_true, y_pred, prefijo: str) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    bias = float(np.mean(err))
    # Spearman ranking
    if np.std(y_true) > 0 and np.std(y_pred) > 0:
        rho, _ = stats.spearmanr(y_true, y_pred)
    else:
        rho = np.nan
    # R² de Efron
    ss_res = np.sum(err ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan
    return {
        f"{prefijo}_mae": round(mae, 4),
        f"{prefijo}_rmse": round(rmse, 4),
        f"{prefijo}_bias": round(bias, 4),
        f"{prefijo}_spearman": round(float(rho), 4) if np.isfinite(rho) else np.nan,
        f"{prefijo}_r2": round(r2, 4) if np.isfinite(r2) else np.nan,
        f"{prefijo}_mean_obs": round(float(y_true.mean()), 4),
        f"{prefijo}_mean_pred": round(float(y_pred.mean()), 4),
        f"{prefijo}_n": int(len(y_true)),
    }


freq_metrics_hold = _reg_metrics(holdout["n_siniestros"], holdout["freq_pred"], "freq")
print(f"\n  Holdout frecuencia: MAE={freq_metrics_hold['freq_mae']:.3f}  "
      f"RMSE={freq_metrics_hold['freq_rmse']:.3f}  "
      f"Spearman={freq_metrics_hold['freq_spearman']:.3f}")


# ──────────────────────────────────────────────────
# 3. Severidad (costo por siniestro) – AT / EL separados
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  SEVERIDAD – Lognormal condicionada (AT / EL separados)")
print("=" * 70)

sin_m = sin.merge(
    attrs[["id_empresa", "clase_riesgo", "segmento", "sector"]],
    on="id_empresa",
    how="left",
)
sin_m = sin_m.loc[sin_m["costo_total_w"] > 0].copy()
sin_m["log_costo"] = np.log(sin_m["costo_total_w"].astype(float))
sin_m["clase_riesgo"] = sin_m["clase_riesgo"].astype(int).astype(str)
sin_m["segmento"] = sin_m["segmento"].astype(str)
sin_m["tipo"] = sin_m["tipo"].astype(str)
sin_m["gravedad"] = sin_m["gravedad"].astype(str)

sin_train = sin_m.loc[sin_m["anio"].isin(ANIOS_TRAIN)].copy()
sin_hold = sin_m.loc[sin_m["anio"] == ANIO_HOLDOUT].copy()

# Mix AT/EL por clase (train)
mix_tipo = (
    sin_train.groupby(["clase_riesgo", "tipo"], observed=True)
    .size()
    .unstack(fill_value=0)
)
mix_tipo = mix_tipo.div(mix_tipo.sum(axis=1), axis=0)
p_at_by_clase = mix_tipo.get("AT", pd.Series(dtype=float)).to_dict()
print("  P(AT | clase) train:")
for c, p in sorted(p_at_by_clase.items(), key=lambda x: str(x[0])):
    print(f"    Clase {c}: P(AT)={p:.3f}  P(EL)={1 - p:.3f}")

# Mix gravedad | clase × tipo (para marginalizar en pricing)
mix_grav = (
    sin_train.groupby(["clase_riesgo", "tipo", "gravedad"], observed=True)
    .size()
    .rename("n")
    .reset_index()
)
mix_grav["p"] = mix_grav.groupby(["clase_riesgo", "tipo"])["n"].transform(
    lambda s: s / s.sum()
)

sev_models: dict[str, object] = {}
sev_coefs_list: list[pd.DataFrame] = []
sev_metrics_rows: list[dict] = []

for tipo in ["AT", "EL"]:
    tr = sin_train.loc[sin_train["tipo"] == tipo].copy()
    te = sin_hold.loc[sin_hold["tipo"] == tipo].copy()
    mod = smf.ols(SEV_FORMULA, data=tr).fit()
    sev_models[tipo] = mod

    coefs = pd.DataFrame({
        "parametro": mod.params.index,
        "coef": mod.params.values,
        "ee": mod.bse.values,
        "t": mod.tvalues.values,
        "p_valor": mod.pvalues.values,
    })
    coefs["modelo"] = f"severidad_lognormal_{tipo}"
    coefs["sigma2"] = float(mod.scale)
    coefs["r2"] = float(mod.rsquared)
    coefs["n_train"] = len(tr)
    sev_coefs_list.append(coefs)

    # Holdout a nivel siniestro (gravedad observada)
    mu_te = mod.predict(te)
    pred_te = np.exp(mu_te + 0.5 * mod.scale)
    m = _reg_metrics(te["costo_total_w"], pred_te, "sev")
    m["tipo"] = tipo
    m["r2_log"] = round(float(mod.rsquared), 4)
    m["sigma"] = round(float(np.sqrt(mod.scale)), 4)
    m["n_train"] = len(tr)
    sev_metrics_rows.append(m)
    print(f"  {tipo}: n_train={len(tr):,}  R²_log={mod.rsquared:.3f}  "
          f"holdout MAE={m['sev_mae']:,.0f}  Spearman={m['sev_spearman']:.3f}")

sev_coefs = pd.concat(sev_coefs_list, ignore_index=True)
sev_metrics = pd.DataFrame(sev_metrics_rows)


def _grav_weights(clase: str, tipo: str) -> pd.DataFrame:
    sub = mix_grav.loc[
        (mix_grav["clase_riesgo"] == str(clase)) & (mix_grav["tipo"] == tipo)
    ]
    if len(sub) == 0:
        sub = (
            mix_grav.loc[mix_grav["tipo"] == tipo]
            .groupby("gravedad", as_index=False)["n"].sum()
        )
        sub["p"] = sub["n"] / sub["n"].sum()
    return sub


def expected_severity_tipo(clase: str, segmento: str, tipo: str) -> float:
    """E[costo | clase, segmento, tipo] marginalizando gravedad."""
    mod = sev_models[tipo]
    weights = _grav_weights(clase, tipo)
    total = 0.0
    for _, r in weights.iterrows():
        row = pd.DataFrame([{
            "clase_riesgo": str(clase),
            "segmento": str(segmento),
            "gravedad": str(r["gravedad"]),
        }])
        mu = float(mod.predict(row).iloc[0])
        total += float(r["p"]) * float(np.exp(mu + 0.5 * mod.scale))
    return total


def expected_severity(clase: str, segmento: str) -> float:
    """E[costo | clase, segmento] marginalizando tipo y gravedad."""
    p_at = float(p_at_by_clase.get(str(clase), 0.86))
    e_at = expected_severity_tipo(clase, segmento, "AT")
    e_el = expected_severity_tipo(clase, segmento, "EL")
    return p_at * e_at + (1.0 - p_at) * e_el


def attach_severity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.drop(columns=["sev_pred"], errors="ignore").copy()
    keys = out[["clase_riesgo", "segmento"]].drop_duplicates()
    keys["sev_pred"] = [
        expected_severity(c, s) for c, s in zip(keys["clase_riesgo"], keys["segmento"])
    ]
    return out.merge(keys, on=["clase_riesgo", "segmento"], how="left")


# ──────────────────────────────────────────────────
# 4. Pure premium: holdout 2024 + proyección próximo año
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  COSTO ESPERADO = E[N] × E[Sev | X]")
print("=" * 70)

holdout = attach_severity(holdout)
holdout["costo_pred"] = holdout["freq_pred"] * holdout["sev_pred"]
holdout["loss_ratio_pred"] = np.where(
    holdout["prima_anual"] > 0,
    holdout["costo_pred"] / holdout["prima_anual"],
    np.nan,
)
holdout["loss_ratio_obs"] = np.where(
    holdout["prima_anual"] > 0,
    holdout["costo_total"] / holdout["prima_anual"],
    np.nan,
)

cost_metrics = _reg_metrics(holdout["costo_total"], holdout["costo_pred"], "costo")
print(f"  Holdout costo: MAE={cost_metrics['costo_mae']:,.0f}  "
      f"RMSE={cost_metrics['costo_rmse']:,.0f}  "
      f"Spearman={cost_metrics['costo_spearman']:.3f}")
print(f"  Portafolio holdout: pred={holdout['costo_pred'].sum()/1e9:.2f}B  "
      f"obs={holdout['costo_total'].sum()/1e9:.2f}B  "
      f"ratio={holdout['costo_pred'].sum()/holdout['costo_total'].sum():.3f}")

# Proyección próximo año (features 2024, lag = n_siniestros 2024)
fwd = holdout.copy()
fwd["lag_n_siniestros"] = fwd["n_siniestros"].astype(float)
fwd["log_lag_n"] = np.log1p(fwd["lag_n_siniestros"])
fwd["freq_pred"] = predict_freq(freq_glm, fwd)
fwd = attach_severity(fwd)
fwd["costo_pred"] = fwd["freq_pred"] * fwd["sev_pred"]
fwd["loss_ratio_pred"] = np.where(
    fwd["prima_anual"] > 0, fwd["costo_pred"] / fwd["prima_anual"], np.nan
)
fwd["horizonte"] = "proximo_anio"
fwd["anio_base_features"] = ANIO_HOLDOUT

print(f"  Proyección próximo año (portafolio): "
      f"E[N]={fwd['freq_pred'].sum():,.0f}  "
      f"E[Costo]={fwd['costo_pred'].sum()/1e9:.2f}B COP")

# Dataset predicciones empresa (holdout + forward)
pred_hold = holdout[[
    "id_empresa", "anio", "clase_riesgo", "sector", "segmento",
    "n_trabajadores", "prima_anual",
    "n_siniestros", "costo_total",
    "freq_pred", "sev_pred", "costo_pred",
    "loss_ratio_pred", "loss_ratio_obs",
]].copy()
pred_hold["horizonte"] = "holdout_2024"
pred_hold["insuficiente_pred"] = (pred_hold["loss_ratio_pred"] > 1.0).astype(int)

pred_fwd = fwd[[
    "id_empresa", "clase_riesgo", "sector", "segmento",
    "n_trabajadores", "prima_anual",
    "freq_pred", "sev_pred", "costo_pred", "loss_ratio_pred",
]].copy()
pred_fwd["anio"] = ANIO_HOLDOUT + 1
pred_fwd["n_siniestros"] = np.nan
pred_fwd["costo_total"] = np.nan
pred_fwd["loss_ratio_obs"] = np.nan
pred_fwd["horizonte"] = "proximo_anio"
pred_fwd["insuficiente_pred"] = (pred_fwd["loss_ratio_pred"] > 1.0).astype(int)

pred_empresa = pd.concat([pred_hold, pred_fwd], ignore_index=True)
# tipos amigables
for c in ["clase_riesgo"]:
    pred_empresa[c] = pred_empresa[c].astype(str)

# Agregado por clase de riesgo
def _agg_clase(frame: pd.DataFrame, horizonte: str) -> pd.DataFrame:
    g = (
        frame.groupby("clase_riesgo", as_index=False)
        .agg(
            n_empresas=("id_empresa", "count"),
            n_trabajadores_suma=("n_trabajadores", "sum"),
            prima_suma=("prima_anual", "sum"),
            freq_pred_suma=("freq_pred", "sum"),
            freq_pred_media=("freq_pred", "mean"),
            sev_pred_media=("sev_pred", "mean"),
            costo_pred_suma=("costo_pred", "sum"),
            costo_pred_media=("costo_pred", "mean"),
            pct_insuficiente=("insuficiente_pred", "mean"),
        )
    )
    if "costo_total" in frame.columns and frame["costo_total"].notna().any():
        g2 = frame.groupby("clase_riesgo", as_index=False).agg(
            costo_obs_suma=("costo_total", "sum"),
            n_siniestros_obs_suma=("n_siniestros", "sum"),
        )
        g = g.merge(g2, on="clase_riesgo", how="left")
        g["ratio_pred_obs"] = g["costo_pred_suma"] / g["costo_obs_suma"].replace(0, np.nan)
    else:
        g["costo_obs_suma"] = np.nan
        g["n_siniestros_obs_suma"] = np.nan
        g["ratio_pred_obs"] = np.nan
    g["loss_ratio_pred"] = g["costo_pred_suma"] / g["prima_suma"].replace(0, np.nan)
    g["pct_insuficiente"] = (g["pct_insuficiente"] * 100).round(2)
    g["share_costo_pred_pct"] = (
        100 * g["costo_pred_suma"] / g["costo_pred_suma"].sum()
    ).round(2)
    g["horizonte"] = horizonte
    return g


pred_clase = pd.concat([
    _agg_clase(pred_hold, "holdout_2024"),
    _agg_clase(pred_fwd, "proximo_anio"),
], ignore_index=True)

print("\n  Costo esperado por clase (próximo año):")
print(
    pred_clase.query("horizonte == 'proximo_anio'")[
        ["clase_riesgo", "n_empresas", "freq_pred_media", "costo_pred_suma",
         "loss_ratio_pred", "share_costo_pred_pct"]
    ].to_string(index=False)
)


# ──────────────────────────────────────────────────
# 5. Métricas consolidadas + resumen
# ──────────────────────────────────────────────────
metricas = pd.DataFrame([
    {
        "componente": "frecuencia_NB",
        "split": "holdout_2024",
        **freq_metrics_hold,
        "alpha_nb": round(alpha_hat, 4),
        "aic_mle": round(float(nb_mle.aic), 1),
    },
    {
        "componente": "severidad_AT",
        "split": "holdout_2024",
        **{k: v for k, v in sev_metrics_rows[0].items() if k != "tipo"},
    },
    {
        "componente": "severidad_EL",
        "split": "holdout_2024",
        **{k: v for k, v in sev_metrics_rows[1].items() if k != "tipo"},
    },
    {
        "componente": "costo_pure_premium",
        "split": "holdout_2024",
        **cost_metrics,
        "portfolio_pred": float(holdout["costo_pred"].sum()),
        "portfolio_obs": float(holdout["costo_total"].sum()),
        "portfolio_ratio": float(
            holdout["costo_pred"].sum() / holdout["costo_total"].sum()
        ),
    },
])

resumen = pd.DataFrame([{
    "anio_holdout": ANIO_HOLDOUT,
    "anios_train": f"{ANIOS_TRAIN[0]}-{ANIOS_TRAIN[-1]}",
    "freq_formula": FREQ_FORMULA,
    "sev_formula": SEV_FORMULA,
    "alpha_nb": round(alpha_hat, 4),
    "freq_mae_holdout": freq_metrics_hold["freq_mae"],
    "freq_spearman_holdout": freq_metrics_hold["freq_spearman"],
    "sev_at_r2_log": sev_metrics_rows[0]["r2_log"],
    "sev_el_r2_log": sev_metrics_rows[1]["r2_log"],
    "costo_mae_holdout": cost_metrics["costo_mae"],
    "costo_spearman_holdout": cost_metrics["costo_spearman"],
    "portfolio_ratio_holdout": round(
        float(holdout["costo_pred"].sum() / holdout["costo_total"].sum()), 4
    ),
    "portfolio_costo_pred_proximo_anio": float(fwd["costo_pred"].sum()),
    "portfolio_freq_pred_proximo_anio": float(fwd["freq_pred"].sum()),
    "n_empresas_insuficientes_proximo": int(pred_fwd["insuficiente_pred"].sum()),
    "pct_empresas_insuficientes_proximo": round(
        100 * pred_fwd["insuficiente_pred"].mean(), 2
    ),
    "decision_s1": "severidad_condicionada_clase_x_segmento_x_gravedad_marginalizada",
    "decision_arquitectura": "NB_freq + Lognormal_sev_AT_EL",
}])


# ──────────────────────────────────────────────────
# 6. Figuras (sura_brand)
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  FIGURAS")
print("=" * 70)

# 6.1 Frecuencia obs vs pred
fig, axes = sb.create_dashboard(
    1, 2,
    title="Frecuencia – Holdout 2024 (NB + offset)",
    subtitle=(
        f"MAE={freq_metrics_hold['freq_mae']:.2f} · "
        f"RMSE={freq_metrics_hold['freq_rmse']:.2f} · "
        f"Spearman={freq_metrics_hold['freq_spearman']:.2f} · α={alpha_hat:.3f}"
    ),
)
ax1, ax2 = axes[0], axes[1]
samp = holdout.sample(n=min(1500, len(holdout)), random_state=RANDOM_SEED)
ax1.scatter(samp["n_siniestros"], samp["freq_pred"], s=12, alpha=0.35,
            color=sb.AZUL_SURA.hex, edgecolors="none")
lim = max(samp["n_siniestros"].quantile(0.99), samp["freq_pred"].quantile(0.99))
ax1.plot([0, lim], [0, lim], "--", color=sb.AQUA_SURA.hex, lw=1.3)
ax1.set_xlim(0, lim)
ax1.set_ylim(0, lim)
ax1.set_xlabel("n_siniestros observado")
ax1.set_ylabel("E[N] predicho")
ax1.set_title("Empresa: observado vs predicho")

by_c = (
    holdout.groupby("clase_riesgo", as_index=False)
    .agg(obs=("n_siniestros", "mean"), pred=("freq_pred", "mean"))
    .sort_values("clase_riesgo")
)
x = np.arange(len(by_c))
ax2.bar(x - 0.18, by_c["obs"], 0.36, label="Observado", color=sb.AZUL_SURA.hex)
ax2.bar(x + 0.18, by_c["pred"], 0.36, label="Predicho", color=sb.AQUA_SURA.hex)
ax2.set_xticks(x)
ax2.set_xticklabels([f"C{c}" for c in by_c["clase_riesgo"]])
ax2.set_ylabel("Frecuencia media")
ax2.set_title("Media por clase de riesgo")
ax2.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.2.1 | Frecuencia NB")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_freq_obs_vs_pred.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_freq_obs_vs_pred.png")

# 6.2 IRR / coeficientes clase
irr_clase = freq_coefs[freq_coefs["parametro"].str.contains("clase_riesgo")].copy()
irr_clase["clase"] = irr_clase["parametro"].str.extract(r"T\.(\d)").astype(int)
# añadir clase 1 = 1.0
irr_plot = pd.concat([
    pd.DataFrame([{"clase": 1, "irr": 1.0}]),
    irr_clase[["clase", "irr"]],
], ignore_index=True).sort_values("clase")
fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.bar(irr_plot["clase"].astype(str), irr_plot["irr"], color=sb.AZUL_SURA.hex)
ax.axhline(1.0, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.2)
ax.set_xlabel("Clase de riesgo")
ax.set_ylabel("Incidence Rate Ratio (vs clase 1)")
ax.set_title("Frecuencia NB – efecto de clase de riesgo (IRR)")
sb.add_sura_footer(fig, text="S03-3.2.1 | IRR frecuencia")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_freq_irr_clase.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_freq_irr_clase.png")

# 6.3 Severidad media predicha por clase × segmento
grid = pd.MultiIndex.from_product(
    [sorted(attrs["clase_riesgo"].astype(str).unique()), SEG_ORDER],
    names=["clase_riesgo", "segmento"],
).to_frame(index=False)
grid["sev_pred"] = [
    expected_severity(c, s) for c, s in zip(grid["clase_riesgo"], grid["segmento"])
]
heat = grid.pivot(index="clase_riesgo", columns="segmento", values="sev_pred")
heat = heat.reindex(columns=SEG_ORDER)
fig, ax = plt.subplots(figsize=(9, 4.8))
im = ax.imshow(heat.values / 1e6, cmap=sb.get_cmap("sura_blues"), aspect="auto")
ax.set_xticks(range(len(heat.columns)))
ax.set_xticklabels(heat.columns, rotation=25, ha="right", fontsize=8)
ax.set_yticks(range(len(heat.index)))
ax.set_yticklabels([f"Clase {i}" for i in heat.index])
ax.set_title("Severidad esperada E[costo|siniestro] (M COP) – condicionada clase × tamaño")
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        ax.text(j, i, f"{heat.values[i, j]/1e6:.2f}", ha="center", va="center",
                fontsize=8, color="white" if heat.values[i, j] > heat.values.mean() else "black")
plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="M COP")
sb.add_sura_footer(fig, text="S03-3.2.1 | Severidad condicionada")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_sev_heatmap_clase_segmento.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_sev_heatmap_clase_segmento.png")

# 6.4 Costo holdout obs vs pred
fig, axes = sb.create_dashboard(
    1, 2,
    title="Costo esperado – Holdout 2024 (pure premium)",
    subtitle=(
        f"MAE={cost_metrics['costo_mae']/1e6:.2f}M · "
        f"Spearman={cost_metrics['costo_spearman']:.2f} · "
        f"Portafolio pred/obs={holdout['costo_pred'].sum()/holdout['costo_total'].sum():.2f}"
    ),
)
ax1, ax2 = axes[0], axes[1]
s2 = holdout.sample(n=min(1500, len(holdout)), random_state=RANDOM_SEED)
ax1.scatter(s2["costo_total"] / 1e6, s2["costo_pred"] / 1e6, s=12, alpha=0.35,
            color=sb.AZUL_SURA.hex, edgecolors="none")
lim = max(s2["costo_total"].quantile(0.98), s2["costo_pred"].quantile(0.98)) / 1e6
ax1.plot([0, lim], [0, lim], "--", color=sb.AQUA_SURA.hex, lw=1.3)
ax1.set_xlim(0, lim)
ax1.set_ylim(0, lim)
ax1.set_xlabel("Costo observado (M COP)")
ax1.set_ylabel("Costo predicho (M COP)")
ax1.set_title("Empresa")

pc = pred_clase.query("horizonte == 'holdout_2024'").sort_values("clase_riesgo")
x = np.arange(len(pc))
ax2.bar(x - 0.18, pc["costo_obs_suma"] / 1e9, 0.36, label="Observado", color=sb.AZUL_SURA.hex)
ax2.bar(x + 0.18, pc["costo_pred_suma"] / 1e9, 0.36, label="Predicho", color=sb.AQUA_SURA.hex)
ax2.set_xticks(x)
ax2.set_xticklabels([f"C{c}" for c in pc["clase_riesgo"]])
ax2.set_ylabel("Costo agregado (B COP)")
ax2.set_title("Por clase de riesgo")
ax2.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.2.1 | Costo holdout")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_costo_obs_vs_pred.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_costo_obs_vs_pred.png")

# 6.5 Proyección por clase + LR
fig, axes = sb.create_dashboard(
    1, 2,
    title="Proyección próximo año – por clase de riesgo",
    subtitle=(
        f"Portafolio E[Costo]={fwd['costo_pred'].sum()/1e9:.2f}B COP · "
        f"{pred_fwd['insuficiente_pred'].mean()*100:.1f}% empresas con LR pred>1"
    ),
)
ax1, ax2 = axes[0], axes[1]
pf = pred_clase.query("horizonte == 'proximo_anio'").sort_values("clase_riesgo")
ax1.bar(pf["clase_riesgo"].astype(str), pf["costo_pred_suma"] / 1e9, color=sb.AZUL_SURA.hex)
ax1.set_xlabel("Clase de riesgo")
ax1.set_ylabel("Costo esperado (B COP)")
ax1.set_title("Costo esperado agregado")

colors_lr = [
    "#C62828" if v > 1 else sb.AQUA_SURA.hex for v in pf["loss_ratio_pred"]
]
ax2.bar(pf["clase_riesgo"].astype(str), pf["loss_ratio_pred"], color=colors_lr)
ax2.axhline(1.0, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.3, label="LR = 1")
ax2.set_xlabel("Clase de riesgo")
ax2.set_ylabel("Loss ratio predicho (costo/prima)")
ax2.set_title("LR agregado por clase")
ax2.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.2.1 | Proyección por clase")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_proyeccion_clase.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_proyeccion_clase.png")

# 6.6 Top empresas por costo esperado (forward)
fig, ax = plt.subplots(figsize=(9, 5.5))
top = pred_fwd.nlargest(20, "costo_pred").copy()
top["label"] = (
    top["id_empresa"] + " · C" + top["clase_riesgo"].astype(str)
    + " · " + top["segmento"].str.replace(r" \(.*\)", "", regex=True)
)
cols = ["#C62828" if x else sb.AZUL_SURA.hex for x in top["insuficiente_pred"]]
ax.barh(top["label"][::-1], (top["costo_pred"] / 1e6)[::-1], color=cols[::-1])
ax.set_xlabel("Costo esperado próximo año (M COP)")
ax.set_title("Top 20 empresas por costo esperado (rojo = LR pred > 1)")
sb.add_sura_footer(fig, text="S03-3.2.1 | Priorización suscripción")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_top_empresas_costo.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_top_empresas_costo.png")

# 6.7 Distribución LR predicho
fig, ax = plt.subplots(figsize=(8, 4.5))
lr = pred_fwd["loss_ratio_pred"].dropna()
ax.hist(lr.clip(upper=lr.quantile(0.99)), bins=40, color=sb.AZUL_SURA.hex, alpha=0.85)
ax.axvline(1.0, color="#C62828", ls="--", lw=1.4, label="LR = 1")
ax.axvline(lr.median(), color=sb.AQUA_SURA.hex, ls="--", lw=1.4,
           label=f"Mediana={lr.median():.2f}")
ax.set_xlabel("Loss ratio predicho (próximo año)")
ax.set_ylabel("Nº empresas")
ax.set_title("Distribución del LR esperado – priorización tarifaria")
ax.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.2.1 | LR predicho")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_modelo_lr_distribucion.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_modelo_lr_distribucion.png")


# ──────────────────────────────────────────────────
# 7. Persistencia staging + CSV
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  PERSISTENCIA")
print("=" * 70)

# Mix AT/EL y gravedad staging
mix_tipo_out = mix_tipo.reset_index().rename(columns={"AT": "p_at", "EL": "p_el"})
if "p_el" not in mix_tipo_out.columns:
    mix_tipo_out["p_el"] = 1.0 - mix_tipo_out["p_at"]
mix_grav_out = mix_grav[["clase_riesgo", "tipo", "gravedad", "n", "p"]].copy()

staging = {
    "modelo_panel_empresa_anio.parquet": panel_out,
    "modelo_freq_coefs.parquet": freq_coefs,
    "modelo_sev_coefs.parquet": sev_coefs,
    "modelo_sev_mix_tipo.parquet": mix_tipo_out,
    "modelo_sev_mix_gravedad.parquet": mix_grav_out,
    "modelo_pred_empresa.parquet": pred_empresa,
    "modelo_pred_clase.parquet": pred_clase,
    "modelo_metricas.parquet": metricas,
    "modelo_resumen.parquet": resumen,
}

for name, frame in staging.items():
    path = DATA_S03 / name
    frame.to_parquet(path, index=False)
    print(f"  ✓ {path.relative_to(ROOT)}  ({frame.shape[0]} × {frame.shape[1]})")

for name, frame in {
    "modelo_freq_coefs.csv": freq_coefs,
    "modelo_sev_coefs.csv": sev_coefs,
    "modelo_pred_clase.csv": pred_clase,
    "modelo_metricas.csv": metricas,
    "modelo_resumen.csv": resumen,
}.items():
    frame.to_csv(RESULTS_DIR / name, index=False)

# Pred empresa solo forward (lectura rápida)
pred_fwd.to_csv(RESULTS_DIR / "modelo_pred_empresa_proximo_anio.csv", index=False)

print("\n✓ Modelado frecuencia–severidad completado.")
print(resumen.T.to_string(header=False))
