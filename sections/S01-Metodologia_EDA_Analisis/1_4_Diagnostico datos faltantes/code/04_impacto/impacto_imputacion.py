"""
Diagnóstico de Datos Faltantes – Impacto de Imputación vs Descarte
==================================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.4 – Diagnóstico de datos faltantes
Proceso: 1.4.4 – Efecto sobre el modelado

Descripción:
    Cuantifica el impacto de la estrategia 1.4.3 frente a listwise deletion
    sobre baselines de frecuencia y severidad/costos.

    Modelos (alineados a 1.3 / CRISP-DM):
      · Frecuencia (empresa): Binomial Negativa
            n_siniestros ~ C(clase_riesgo) + log_n_trabajadores + log_prima_anual
      · Severidad (siniestro): Lognormal ≡ OLS en log
            log1p(dias) ~ C(tipo) + C(gravedad)
      · Costo asistencial (siniestro): Lognormal ≡ OLS en log
            log1p(costo_asistencial) ~ C(tipo) + C(gravedad)
              + log1p(costo_prestacion_economica)

    Escenarios:
      (a) listwise  – descarta registros con faltantes originales en features/target
      (b) imputado  – usa empresas_imputadas / siniestros_imputados
      (c) imputado+flag – (b) + miss_* como predictores (p. ej. miss_costo_asist)

    Evaluación:
      · Coeficientes y EE (sesgo relativo vs escenario b; inflación de varianza)
      · Holdout 80/20 (semilla fija): MAE/RMSE predictivo sobre casos con
        outcome originalmente observado (comparación justa)
      · AIC in-sample por escenario

Inputs (reutilizados):
    - data/staging/S01/empresas_imputadas.parquet
    - data/staging/S01/siniestros_imputados.parquet
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/staging/S01/faltantes_imputacion_estrategia.parquet

Outputs:
    - results/imgs/04_*.png
    - results/faltantes_impacto_*.csv
    - data/staging/S01/faltantes_impacto_coefs.parquet
    - data/staging/S01/faltantes_impacto_metricas.parquet
    - data/staging/S01/faltantes_impacto_resumen.parquet

Uso:
    .venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/04_impacto/impacto_imputacion.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib.patches import Patch

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
TEST_SIZE = 0.20
rng = np.random.default_rng(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"
DATA_STAGING.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

ESCENARIOS = {
    "a_listwise": "a) Listwise deletion",
    "b_imputado": "b) Datos imputados",
    "c_imputado_flag": "c) Imputado + flag miss",
}

print("=" * 70)
print("  S01-1.4.4 | Impacto imputación vs listwise deletion")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga y paneles
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando staging reutilizado...")
emp_imp = pd.read_parquet(DATA_STAGING / "empresas_imputadas.parquet")
sin_imp = pd.read_parquet(DATA_STAGING / "siniestros_imputados.parquet")
emp_comp = pd.read_parquet(DATA_STAGING / "empresa_siniestralidad_completa.parquet")
_ = pd.read_parquet(DATA_STAGING / "faltantes_imputacion_estrategia.parquet")  # reutilizado / trazabilidad

# Panel frecuencia: conteo observado + features imputadas
freq = emp_comp[["id_empresa", "n_siniestros"]].merge(
    emp_imp[
        [
            "id_empresa",
            "clase_riesgo",
            "log_n_trabajadores",
            "log_prima_anual",
            "prima_anual",
            "miss_prima",
            "miss_geo",
            "antiguedad_meses",
            "sector",
        ]
    ],
    on="id_empresa",
    how="inner",
)
freq["clase_riesgo"] = freq["clase_riesgo"].astype(str)
freq["n_siniestros"] = freq["n_siniestros"].astype(int)

# Panel severidad / costo
sev = sin_imp.copy()
sev["log_dias"] = np.log1p(sev["dias_incapacidad"].astype(float))
sev["log_costo_asist"] = np.log1p(sev["costo_asistencial"].astype(float))
sev["log_prestacion"] = np.log1p(sev["costo_prestacion_economica"].astype(float))

print(f"  panel frecuencia: {freq.shape}")
print(f"  panel siniestros: {sev.shape}")
print(
    f"  listwise frecuencia (miss_prima|miss_geo): "
    f"{((freq.miss_prima == 1) | (freq.miss_geo == 1)).sum()} excluidas"
)
print(
    f"  listwise dias / costo: miss_dias={sev.miss_dias.sum()}, "
    f"miss_costo={sev.miss_costo_asist.sum()}"
)


def train_test_mask(n: int, seed: int = RANDOM_SEED) -> np.ndarray:
    """True = train."""
    idx = np.arange(n)
    rng_local = np.random.default_rng(seed)
    rng_local.shuffle(idx)
    n_test = int(round(n * TEST_SIZE))
    test_idx = set(idx[:n_test])
    return np.array([i not in test_idx for i in range(n)])


# Splits fijos por posición (reproducibles)
freq = freq.sort_values("id_empresa").reset_index(drop=True)
sev = sev.sort_values("id_siniestro").reset_index(drop=True)
freq["_train"] = train_test_mask(len(freq), seed=RANDOM_SEED)
sev["_train"] = train_test_mask(len(sev), seed=RANDOM_SEED + 1)

print(f"  split frecuencia train/test: {freq['_train'].sum()} / {(~freq['_train']).sum()}")
print(f"  split siniestros train/test: {sev['_train'].sum()} / {(~sev['_train']).sum()}")


# ──────────────────────────────────────────────────
# 2. Helpers de modelado y métricas
# ──────────────────────────────────────────────────
def pred_nb_mean(res, df: pd.DataFrame) -> np.ndarray:
    """Media μ de NB: exp(Xβ)."""
    return np.asarray(res.predict(df), dtype=float)


def metrics_count(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "bias_medio": float(np.mean(err)),
    }


def metrics_log(y_log_true: np.ndarray, y_log_pred: np.ndarray) -> dict:
    y_log_true = np.asarray(y_log_true, dtype=float)
    y_log_pred = np.asarray(y_log_pred, dtype=float)
    err = y_log_pred - y_log_true
    # también en escala original (expm1)
    y = np.expm1(y_log_true)
    yhat = np.expm1(y_log_pred)
    return {
        "mae_log": float(np.mean(np.abs(err))),
        "rmse_log": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(yhat - y))),
        "rmse": float(np.sqrt(np.mean((yhat - y) ** 2))),
        "bias_medio": float(np.mean(yhat - y)),
        "r2_log": float(1 - np.sum(err**2) / np.sum((y_log_true - y_log_true.mean()) ** 2)),
    }


def extract_coefs(res, modelo: str, escenario: str) -> pd.DataFrame:
    rows = []
    bse = res.bse
    for name, beta in res.params.items():
        rows.append(
            {
                "modelo": modelo,
                "escenario": escenario,
                "termino": name,
                "coef": float(beta),
                "ee": float(bse[name]),
                "pvalue": float(res.pvalues[name]),
                "n_obs": int(res.nobs),
            }
        )
    return pd.DataFrame(rows)


coef_frames: list[pd.DataFrame] = []
metric_rows: list[dict] = []


def register_metrics(modelo: str, escenario: str, n_train: int, n_test: int, aic: float, extra: dict):
    metric_rows.append(
        {
            "modelo": modelo,
            "escenario": escenario,
            "n_train": n_train,
            "n_test_eval": n_test,
            "aic": aic,
            **extra,
        }
    )


# ──────────────────────────────────────────────────
# 3. FRECUENCIA — Binomial Negativa
# ──────────────────────────────────────────────────
print("\n[FREQ] Binomial Negativa – n_siniestros ...")

FORM_FREQ_BASE = "n_siniestros ~ C(clase_riesgo) + log_n_trabajadores + log_prima_anual"
FORM_FREQ_FLAG = FORM_FREQ_BASE + " + miss_prima + miss_geo"

# Holdout de evaluación: test ∩ casos con features originalmente completas
# (para no evaluar predicción de prima imputada como si fuera verdad)
freq_test_complete = (~freq["_train"]) & (freq["miss_prima"] == 0) & (freq["miss_geo"] == 0)

freq_scenarios = {
    "a_listwise": {
        "train": freq["_train"] & (freq["miss_prima"] == 0) & (freq["miss_geo"] == 0),
        "formula": FORM_FREQ_BASE,
    },
    "b_imputado": {
        "train": freq["_train"],
        "formula": FORM_FREQ_BASE,
    },
    "c_imputado_flag": {
        "train": freq["_train"],
        "formula": FORM_FREQ_FLAG,
    },
}

for esc, cfg in freq_scenarios.items():
    d_tr = freq.loc[cfg["train"]].copy()
    res = smf.negativebinomial(cfg["formula"], data=d_tr).fit(disp=False, maxiter=200)
    coef_frames.append(extract_coefs(res, "frecuencia_NB", esc))

    d_te = freq.loc[freq_test_complete].copy()
    yhat = pred_nb_mean(res, d_te)
    m = metrics_count(d_te["n_siniestros"].to_numpy(), yhat)
    register_metrics(
        "frecuencia_NB",
        esc,
        n_train=len(d_tr),
        n_test=len(d_te),
        aic=float(res.aic),
        extra=m,
    )
    print(
        f"  {esc}: n_train={len(d_tr)}  AIC={res.aic:.1f}  "
        f"holdout RMSE={m['rmse']:.3f} MAE={m['mae']:.3f}"
    )


# ──────────────────────────────────────────────────
# 4. SEVERIDAD — Lognormal (días)
# ──────────────────────────────────────────────────
print("\n[SEV] Lognormal – dias_incapacidad ...")

FORM_DIAS_BASE = "log_dias ~ C(tipo) + C(gravedad)"
FORM_DIAS_FLAG = FORM_DIAS_BASE + " + miss_dias"

# Eval holdout: test ∩ días originalmente observados
sev_test_dias = (~sev["_train"]) & (sev["miss_dias"] == 0)

dias_scenarios = {
    "a_listwise": {
        "train": sev["_train"] & (sev["miss_dias"] == 0),
        "formula": FORM_DIAS_BASE,
    },
    "b_imputado": {
        "train": sev["_train"],
        "formula": FORM_DIAS_BASE,
    },
    "c_imputado_flag": {
        "train": sev["_train"],
        "formula": FORM_DIAS_FLAG,
    },
}

for esc, cfg in dias_scenarios.items():
    d_tr = sev.loc[cfg["train"]].copy()
    res = smf.ols(cfg["formula"], data=d_tr).fit()
    coef_frames.append(extract_coefs(res, "severidad_lognormal_dias", esc))

    d_te = sev.loc[sev_test_dias].copy()
    yhat = np.asarray(res.predict(d_te), dtype=float)
    m = metrics_log(d_te["log_dias"].to_numpy(), yhat)
    register_metrics(
        "severidad_lognormal_dias",
        esc,
        n_train=len(d_tr),
        n_test=len(d_te),
        aic=float(res.aic),
        extra=m,
    )
    print(
        f"  {esc}: n_train={len(d_tr)}  AIC={res.aic:.1f}  "
        f"holdout RMSE_log={m['rmse_log']:.4f} R²_log={m['r2_log']:.4f}"
    )


# ──────────────────────────────────────────────────
# 5. COSTO — Lognormal (costo asistencial)
# ──────────────────────────────────────────────────
print("\n[COSTO] Lognormal – costo_asistencial ...")

FORM_COSTO_BASE = "log_costo_asist ~ C(tipo) + C(gravedad) + log_prestacion"
FORM_COSTO_FLAG = FORM_COSTO_BASE + " + miss_costo_asist"

sev_test_costo = (~sev["_train"]) & (sev["miss_costo_asist"] == 0)

costo_scenarios = {
    "a_listwise": {
        "train": sev["_train"] & (sev["miss_costo_asist"] == 0),
        "formula": FORM_COSTO_BASE,
    },
    "b_imputado": {
        "train": sev["_train"],
        "formula": FORM_COSTO_BASE,
    },
    "c_imputado_flag": {
        "train": sev["_train"],
        "formula": FORM_COSTO_FLAG,
    },
}

for esc, cfg in costo_scenarios.items():
    d_tr = sev.loc[cfg["train"]].copy()
    res = smf.ols(cfg["formula"], data=d_tr).fit()
    coef_frames.append(extract_coefs(res, "costo_lognormal_asistencial", esc))

    d_te = sev.loc[sev_test_costo].copy()
    yhat = np.asarray(res.predict(d_te), dtype=float)
    m = metrics_log(d_te["log_costo_asist"].to_numpy(), yhat)
    register_metrics(
        "costo_lognormal_asistencial",
        esc,
        n_train=len(d_tr),
        n_test=len(d_te),
        aic=float(res.aic),
        extra=m,
    )
    print(
        f"  {esc}: n_train={len(d_tr)}  AIC={res.aic:.1f}  "
        f"holdout RMSE_log={m['rmse_log']:.4f} R²_log={m['r2_log']:.4f}"
    )


# ──────────────────────────────────────────────────
# 6. Comparación de coeficientes (sesgo vs b, EE)
# ──────────────────────────────────────────────────
coefs = pd.concat(coef_frames, ignore_index=True)
metrics = pd.DataFrame(metric_rows)

# Pivot referencia = b_imputado
ref = coefs[coefs["escenario"] == "b_imputado"][["modelo", "termino", "coef", "ee"]].rename(
    columns={"coef": "coef_b", "ee": "ee_b"}
)
comp = coefs.merge(ref, on=["modelo", "termino"], how="left")
comp["delta_vs_b"] = comp["coef"] - comp["coef_b"]
comp["sesgo_rel_pct"] = np.where(
    comp["coef_b"].abs() > 1e-8,
    100 * comp["delta_vs_b"] / comp["coef_b"].abs(),
    np.nan,
)
comp["ratio_ee_vs_b"] = np.where(comp["ee_b"] > 0, comp["ee"] / comp["ee_b"], np.nan)

# Resumen ejecutivo por modelo
resumen_rows = []
for modelo in metrics["modelo"].unique():
    msub = metrics[metrics["modelo"] == modelo].set_index("escenario")
    csub = comp[(comp["modelo"] == modelo) & (comp["escenario"] == "a_listwise")]
    # mediana |sesgo relativo| de términos comunes (excl intercept)
    csub_f = csub[~csub["termino"].str.contains("Intercept", case=False)]
    med_abs_sesgo = float(csub_f["sesgo_rel_pct"].abs().median()) if len(csub_f) else np.nan
    med_ratio_ee = float(csub_f["ratio_ee_vs_b"].median()) if len(csub_f) else np.nan

    # métrica principal holdout
    if "rmse_log" in msub.columns and msub["rmse_log"].notna().any():
        key_metric = "rmse_log"
    else:
        key_metric = "rmse"

    # Preferir (b) cuando (c) solo gana por un margen despreciable (flags inocuos).
    # Umbral: mejora relativa de c vs b < 0.5% → declarar empate operativo a favor de b.
    hold_a = float(msub.loc["a_listwise", key_metric])
    hold_b = float(msub.loc["b_imputado", key_metric])
    hold_c = float(msub.loc["c_imputado_flag", key_metric])
    mejora_c_vs_b = (hold_b - hold_c) / hold_b if hold_b > 0 else 0.0
    if mejora_c_vs_b < 0.005:  # < 0.5%
        best_esc = "b_imputado"
    else:
        best_esc = msub[key_metric].idxmin()

    resumen_rows.append(
        {
            "modelo": modelo,
            "n_train_a": int(msub.loc["a_listwise", "n_train"]),
            "n_train_b": int(msub.loc["b_imputado", "n_train"]),
            "n_train_c": int(msub.loc["c_imputado_flag", "n_train"]),
            "pct_n_perdido_listwise": round(
                100
                * (1 - msub.loc["a_listwise", "n_train"] / msub.loc["b_imputado", "n_train"]),
                2,
            ),
            "aic_a": float(msub.loc["a_listwise", "aic"]),
            "aic_b": float(msub.loc["b_imputado", "aic"]),
            "aic_c": float(msub.loc["c_imputado_flag", "aic"]),
            "holdout_metric": key_metric,
            "holdout_a": hold_a,
            "holdout_b": hold_b,
            "holdout_c": hold_c,
            "mejor_escenario_holdout": best_esc,
            "mediana_abs_sesgo_rel_a_vs_b_pct": round(med_abs_sesgo, 3),
            "mediana_ratio_ee_a_vs_b": round(med_ratio_ee, 3),
            "recomendacion": (
                "Preferir imputado (b): listwise pierde muestra y puede sesgar "
                "coeficientes bajo MAR. Flags (c) inocuos/innecesarios."
                if med_abs_sesgo > 5 or msub.loc["a_listwise", "n_train"] < 0.9 * msub.loc["b_imputado", "n_train"]
                else "Impacto moderado; preferir imputación (b) por tamaño muestral. Flags (c) innecesarios."
            ),
        }
    )

resumen = pd.DataFrame(resumen_rows)

print("\n[RESUMEN]")
for _, r in resumen.iterrows():
    print(
        f"  {r['modelo']}: listwise pierde {r['pct_n_perdido_listwise']}% train | "
        f"med |sesgo a vs b|={r['mediana_abs_sesgo_rel_a_vs_b_pct']}% | "
        f"mejor holdout={r['mejor_escenario_holdout']}"
    )


# ──────────────────────────────────────────────────
# 7. Persistencia
# ──────────────────────────────────────────────────
print("\n[SAVE] Staging + CSV...")
coefs_out = comp.copy()
coefs_out.to_parquet(DATA_STAGING / "faltantes_impacto_coefs.parquet", index=False)
metrics.to_parquet(DATA_STAGING / "faltantes_impacto_metricas.parquet", index=False)
resumen.to_parquet(DATA_STAGING / "faltantes_impacto_resumen.parquet", index=False)

coefs_out.to_csv(RESULTS_DIR / "faltantes_impacto_coefs.csv", index=False, encoding="utf-8")
metrics.to_csv(RESULTS_DIR / "faltantes_impacto_metricas.csv", index=False, encoding="utf-8")
resumen.to_csv(RESULTS_DIR / "faltantes_impacto_resumen.csv", index=False, encoding="utf-8")
print("  ✓ faltantes_impacto_{coefs,metricas,resumen}")


# ──────────────────────────────────────────────────
# 8. Plots
# ──────────────────────────────────────────────────
print("\n[PLOT] Figuras...")

colors_esc = {
    "a_listwise": "#B85C38",
    "b_imputado": sb.AZUL_SURA.hex,
    "c_imputado_flag": sb.AQUA_SURA.hex,
}

# ── 8.1 N train + AIC por modelo ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Tamaño muestral y AIC por escenario",
    subtitle="(a) listwise · (b) imputado · (c) imputado + flag",
)
ax1, ax2 = axes[0], axes[1]
modelos = list(metrics["modelo"].unique())
x = np.arange(len(modelos))
w = 0.25
for i, esc in enumerate(["a_listwise", "b_imputado", "c_imputado_flag"]):
    vals = [metrics[(metrics.modelo == m) & (metrics.escenario == esc)]["n_train"].iloc[0] for m in modelos]
    ax1.bar(x + (i - 1) * w, vals, w, color=colors_esc[esc], label=ESCENARIOS[esc])
ax1.set_xticks(x)
ax1.set_xticklabels(["Frec. NB", "Días logN", "Costo logN"], fontsize=8)
ax1.set_ylabel("N train")
ax1.set_title("Tamaño de entrenamiento")
ax1.legend(fontsize=7)

for i, esc in enumerate(["a_listwise", "b_imputado", "c_imputado_flag"]):
    vals = [metrics[(metrics.modelo == m) & (metrics.escenario == esc)]["aic"].iloc[0] for m in modelos]
    # normalizar AIC por modelo para comparabilidad visual (AIC_esc / AIC_b)
    vals_b = [metrics[(metrics.modelo == m) & (metrics.escenario == "b_imputado")]["aic"].iloc[0] for m in modelos]
    ratios = [v / b for v, b in zip(vals, vals_b)]
    ax2.bar(x + (i - 1) * w, ratios, w, color=colors_esc[esc], label=ESCENARIOS[esc])
ax2.axhline(1.0, color=sb.GRIS_MEDIO.hex, ls="--", lw=1)
ax2.set_xticks(x)
ax2.set_xticklabels(["Frec. NB", "Días logN", "Costo logN"], fontsize=8)
ax2.set_ylabel("AIC / AIC(b)")
ax2.set_title("AIC relativo a imputado (b)")
ax2.legend(fontsize=7)

sb.add_sura_footer(fig, text="S01-1.4.4 | N y AIC por escenario")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "04_impacto_n_aic.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 04_impacto_n_aic.png")

# ── 8.2 Holdout metrics ──
fig, axes = sb.create_dashboard(
    1,
    3,
    title="Métricas predictivas holdout (outcome originalmente observado)",
    subtitle="Misma partición test filtrada a casos completos originales",
)
plot_specs = [
    ("frecuencia_NB", "rmse", "RMSE conteo"),
    ("severidad_lognormal_dias", "rmse_log", "RMSE log(días)"),
    ("costo_lognormal_asistencial", "rmse_log", "RMSE log(costo)"),
]
for ax, (modelo, metric, title) in zip(axes, plot_specs):
    sub = metrics[metrics["modelo"] == modelo]
    ax.bar(
        [ESCENARIOS[e].split(")")[0] + ")" for e in sub["escenario"]],
        sub[metric],
        color=[colors_esc[e] for e in sub["escenario"]],
        alpha=0.9,
    )
    ax.set_title(title, fontsize=10)
    ax.set_ylabel(metric)
    for i, (_, r) in enumerate(sub.iterrows()):
        ax.text(i, r[metric] * 1.01, f"{r[metric]:.3g}", ha="center", fontsize=8)

sb.add_sura_footer(fig, text="S01-1.4.4 | Holdout predictivo")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "04_impacto_holdout_metricas.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 04_impacto_holdout_metricas.png")

# ── 8.3 Forest coefs clave frecuencia (clase_riesgo) ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Coeficientes clave: frecuencia (NB) y costo (Lognormal)",
    subtitle="Puntos = β · barras = IC≈β±1.96·EE",
)

# Frecuencia: clase 2..5
ax = axes[0]
terms_f = [f"C(clase_riesgo)[T.{k}]" for k in [2, 3, 4, 5]]
sub = coefs[(coefs["modelo"] == "frecuencia_NB") & (coefs["termino"].isin(terms_f))]
y_base = np.arange(len(terms_f))
for j, esc in enumerate(["a_listwise", "b_imputado", "c_imputado_flag"]):
    s = sub[sub["escenario"] == esc].set_index("termino").reindex(terms_f)
    y = y_base + (j - 1) * 0.25
    ax.errorbar(
        s["coef"],
        y,
        xerr=1.96 * s["ee"],
        fmt="o",
        color=colors_esc[esc],
        label=ESCENARIOS[esc],
        markersize=5,
        capsize=2,
    )
ax.set_yticks(y_base)
ax.set_yticklabels([f"clase {k}" for k in [2, 3, 4, 5]])
ax.axvline(0, color=sb.GRIS_MEDIO.hex, ls="--", lw=0.8)
ax.set_xlabel("β (log conteo)")
ax.set_title("NB – efecto clase de riesgo")
ax.legend(fontsize=6, loc="lower right")

# Costo: gravedad + miss_costo
ax = axes[1]
terms_c_all = ["C(gravedad)[T.grave]", "C(gravedad)[T.mortal]", "log_prestacion", "miss_costo_asist"]
label_map = {
    "C(gravedad)[T.grave]": "grave",
    "C(gravedad)[T.mortal]": "mortal",
    "log_prestacion": "log(prestación)",
    "miss_costo_asist": "miss_costo",
}
sub = coefs[(coefs["modelo"] == "costo_lognormal_asistencial") & (coefs["termino"].isin(terms_c_all))]
# unión de términos presentes en cualquier escenario (miss solo en c)
terms_c = [t for t in terms_c_all if t in set(sub["termino"])]
y_base = np.arange(len(terms_c))
for j, esc in enumerate(["a_listwise", "b_imputado", "c_imputado_flag"]):
    s = sub[sub["escenario"] == esc].set_index("termino").reindex(terms_c)
    y = y_base + (j - 1) * 0.25
    ax.errorbar(
        s["coef"],
        y,
        xerr=1.96 * s["ee"],
        fmt="o",
        color=colors_esc[esc],
        label=ESCENARIOS[esc],
        markersize=5,
        capsize=2,
    )
ax.set_yticks(y_base)
ax.set_yticklabels([label_map[t] for t in terms_c], fontsize=8)
ax.axvline(0, color=sb.GRIS_MEDIO.hex, ls="--", lw=0.8)
ax.set_xlabel("β (log costo)")
ax.set_title("Lognormal – costo asistencial")
ax.legend(fontsize=6, loc="best")

sb.add_sura_footer(fig, text="S01-1.4.4 | Comparación de coeficientes")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "04_impacto_coefs_forest.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 04_impacto_coefs_forest.png")

# ── 8.4 Sesgo relativo a vs b ──
fig, ax = plt.subplots(figsize=(9, 4.5))
a_only = comp[(comp["escenario"] == "a_listwise") & (~comp["termino"].str.contains("Intercept"))]
# top by abs sesgo within each model
parts = []
for modelo, g in a_only.groupby("modelo"):
    parts.append(g.reindex(g["sesgo_rel_pct"].abs().sort_values(ascending=False).index).head(4))
top = pd.concat(parts)
labels = top["modelo"].str.replace("frecuencia_NB", "NB", regex=False).str.replace(
    "severidad_lognormal_dias", "días", regex=False
).str.replace("costo_lognormal_asistencial", "costo", regex=False) + " | " + top["termino"]
y = np.arange(len(top))
ax.barh(y, top["sesgo_rel_pct"], color=sb.AZUL_SURA.hex, alpha=0.85)
ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=7)
ax.axvline(0, color=sb.GRIS_MEDIO.hex, ls="--")
ax.set_xlabel("Sesgo relativo de β: 100·(β_a − β_b) / |β_b|  (%)")
ax.set_title("Listwise (a) vs imputado (b): desplazamiento de coeficientes")
sb.add_sura_footer(fig, text="S01-1.4.4 | Sesgo relativo de coeficientes")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "04_impacto_sesgo_coefs.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 04_impacto_sesgo_coefs.png")

# ── 8.5 Tabla resumen visual ──
fig, ax = plt.subplots(figsize=(11, 3.6))
ax.axis("off")
disp = resumen[
    [
        "modelo",
        "pct_n_perdido_listwise",
        "holdout_a",
        "holdout_b",
        "holdout_c",
        "mediana_abs_sesgo_rel_a_vs_b_pct",
        "mejor_escenario_holdout",
    ]
].copy()
disp["modelo"] = disp["modelo"].map(
    {
        "frecuencia_NB": "Frecuencia NB",
        "severidad_lognormal_dias": "Severidad días",
        "costo_lognormal_asistencial": "Costo asistencial",
    }
)
for c in ["holdout_a", "holdout_b", "holdout_c", "mediana_abs_sesgo_rel_a_vs_b_pct", "pct_n_perdido_listwise"]:
    disp[c] = disp[c].map(lambda x: f"{x:.3g}")
disp["mejor_escenario_holdout"] = disp["mejor_escenario_holdout"].map(
    lambda x: {"a_listwise": "a", "b_imputado": "b", "c_imputado_flag": "c"}.get(x, x)
)
table = ax.table(
    cellText=disp.values,
    colLabels=["Modelo", "% n perdido (a)", "Holdout a", "Holdout b", "Holdout c", "Med|sesgo| a vs b %", "Mejor"],
    loc="center",
    cellLoc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(7.5)
table.scale(1.15, 1.55)
for (r, c), cell in table.get_celld().items():
    if r == 0:
        cell.set_facecolor(sb.AZUL_SURA.hex)
        cell.set_text_props(color="white", fontweight="bold")
ax.set_title("Resumen de impacto: sesgo y predictivo", color=sb.AZUL_SURA.hex, pad=8)
legend_elems = [Patch(facecolor=colors_esc[k], label=v) for k, v in ESCENARIOS.items()]
ax.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8)
sb.add_sura_footer(fig, text="S01-1.4.4 | Resumen ejecutivo")
fig.tight_layout(rect=[0, 0.08, 1, 1])
fig.savefig(IMGS_DIR / "04_impacto_resumen.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 04_impacto_resumen.png")


print("\n" + "=" * 70)
print("  Ejecución completada.")
print("=" * 70)
print("\n  Staging: faltantes_impacto_{coefs,metricas,resumen}.parquet")
print("  Plots: results/imgs/04_impacto_*.png")
