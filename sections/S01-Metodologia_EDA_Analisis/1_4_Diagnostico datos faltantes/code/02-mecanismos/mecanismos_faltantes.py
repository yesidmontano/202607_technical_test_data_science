"""
Diagnóstico de Datos Faltantes – Mecanismos (MCAR / MAR / MNAR)
==============================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.4 – Diagnóstico de datos faltantes
Proceso: 1.4.2 – Evaluación formal de mecanismos

Descripción:
    Evalúa formalmente las hipótesis de mecanismo de faltantes para cada
    variable con nulos en empresas.csv y siniestros.csv.

    Marco:
      H0 (MCAR): R ⊥ datos observados  (P(R=1 | X_obs) = P(R=1))
      H1 (no MCAR): R depende de X_obs  → evidencia compatible con MAR
      MNAR: R depende de X_miss; no es identificable solo con observados.
            Se reporta sospecha cuando proxies del valor faltante predicen R
            tras condicionar por covariables administrativas, o por juicio
            de dominio documentado.

    Pruebas (por variable con nulos):
      - χ² de independencia R × categóricas observadas (+ Cramér V)
      - Mann-Whitney U (o t de Welch si normalidad en ambos grupos) R vs
        numéricas observadas (+ Cliff's δ / Cohen d)
      - Regresión logística de la indicadora R ~ covariables observadas
        (razón de verosimilitud vs modelo nulo; OR)
      - Corrección Holm-Bonferroni dentro de cada familia de tests univariados
        de la misma variable R

    Señales prioritarias (Insights 1.4.1 §D):
      dias_incapacidad × tipo
      costo_asistencial × gravedad
      prima_anual × clase_riesgo
      ciudad × sector

Inputs (reutilizados):
    - data/raw/empresas.csv, data/raw/siniestros.csv
    - data/staging/S01/faltantes_por_estrato.parquet
    - data/staging/S01/faltantes_patrones.parquet

Outputs:
    - results/imgs/02_*.png
    - results/faltantes_mecanismos_*.csv
    - data/staging/S01/faltantes_mecanismos_tests.parquet
    - data/staging/S01/faltantes_mecanismos_logit.parquet
    - data/staging/S01/faltantes_mecanismos_veredicto.parquet

Uso:
    .venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/02-mecanismos/mecanismos_faltantes.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from matplotlib.patches import Patch
from statsmodels.stats.multitest import multipletests

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
ALPHA = 0.05

ROOT = Path(__file__).resolve().parents[5]
DATA_RAW = ROOT / "data" / "raw"
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"
DATA_STAGING.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S01-1.4.2 | Mecanismos de datos faltantes (MCAR / MAR / MNAR)")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando raw + staging de cuantificación...")
empresas = pd.read_csv(DATA_RAW / "empresas.csv", parse_dates=["fecha_afiliacion"])
siniestros = pd.read_csv(DATA_RAW / "siniestros.csv", parse_dates=["fecha_ocurrencia"])
estratos = pd.read_parquet(DATA_STAGING / "faltantes_por_estrato.parquet")
patrones = pd.read_parquet(DATA_STAGING / "faltantes_patrones.parquet")

print(f"  empresas:   {empresas.shape}")
print(f"  siniestros: {siniestros.shape}")
print(f"  faltantes_por_estrato (reutilizado): {estratos.shape}")
print(f"  faltantes_patrones (reutilizado):    {patrones.shape}")

# Indicadoras R y features auxiliares
emp = empresas.copy()
emp["miss_ciudad"] = emp["ciudad"].isna().astype(int)
emp["miss_departamento"] = emp["departamento"].isna().astype(int)
emp["miss_geo"] = emp["miss_ciudad"]  # idéntico a departamento (patrón 1.4.1)
emp["miss_prima"] = emp["prima_anual"].isna().astype(int)
emp["log_n_trabajadores"] = np.log1p(emp["n_trabajadores"])
emp["clase_riesgo"] = emp["clase_riesgo"].astype(str)

sin = siniestros.copy()
sin["miss_parte"] = sin["parte_cuerpo"].isna().astype(int)
sin["miss_dias"] = sin["dias_incapacidad"].isna().astype(int)
sin["miss_costo_asist"] = sin["costo_asistencial"].isna().astype(int)
sin["log_costo_prestacion"] = np.log1p(sin["costo_prestacion_economica"])
sin["anio"] = sin["fecha_ocurrencia"].dt.year.astype(str)

# Verificar bloque geo
assert (emp["miss_ciudad"] == emp["miss_departamento"]).all(), "ciudad/depto deben coincidir"


# ──────────────────────────────────────────────────
# 2. Helpers estadísticos
# ──────────────────────────────────────────────────
def cramers_v(table: np.ndarray) -> float:
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    n = table.sum()
    if n == 0:
        return np.nan
    r, k = table.shape
    return float(np.sqrt(chi2 / (n * (min(r, k) - 1))))


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """δ de Cliff: P(X>Y) - P(X<Y)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    # aproximación eficiente vía ranks
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return np.nan
    # Mann-Whitney U = # pares donde x < y + 0.5 ties
    u = stats.mannwhitneyu(x, y, alternative="two-sided").statistic
    # U cuenta pares x>y con convención scipy; δ = 2U/(nx*ny) - 1 con U=#(x>y)+0.5ties
    # scipy U is for first sample vs second: number of wins of x over y
    return float((2 * u) / (nx * ny) - 1)


def interpret_cramers(v: float) -> str:
    if np.isnan(v):
        return "n/a"
    a = abs(v)
    if a < 0.1:
        return "despreciable"
    if a < 0.3:
        return "pequeño"
    if a < 0.5:
        return "mediano"
    return "grande"


def interpret_delta(d: float) -> str:
    if np.isnan(d):
        return "n/a"
    a = abs(d)
    if a < 0.147:
        return "despreciable"
    if a < 0.33:
        return "pequeño"
    if a < 0.474:
        return "mediano"
    return "grande"


def test_chi2(df: pd.DataFrame, r_col: str, cat_col: str, dataset: str, target: str) -> dict:
    ct = pd.crosstab(df[r_col], df[cat_col])
    # filtrar columnas con total 0
    ct = ct.loc[:, ct.sum(axis=0) > 0]
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return {
            "dataset": dataset,
            "variable_faltante": target,
            "covariable": cat_col,
            "tipo_covariable": "categorica",
            "prueba": "chi2",
            "n": int(ct.values.sum()),
            "estadistico": np.nan,
            "gl": np.nan,
            "p_valor": np.nan,
            "efecto": np.nan,
            "metrica_efecto": "cramers_v",
            "magnitud_efecto": "n/a",
            "supuesto_ok": False,
            "nota_supuesto": "tabla degenerada",
        }
    chi2, p, dof, expected = stats.chi2_contingency(ct)
    # supuesto: expected >= 5 en ≥80% celdas
    pct_low = float((expected < 5).mean())
    ok = pct_low <= 0.20
    # si celdas esperadas bajas, Fisher exact solo 2x2
    if not ok and ct.shape == (2, 2):
        oddsr, p_f = stats.fisher_exact(ct)
        v = cramers_v(ct.values.astype(float))
        return {
            "dataset": dataset,
            "variable_faltante": target,
            "covariable": cat_col,
            "tipo_covariable": "categorica",
            "prueba": "fisher_exact",
            "n": int(ct.values.sum()),
            "estadistico": float(oddsr),
            "gl": 1,
            "p_valor": float(p_f),
            "efecto": round(v, 4),
            "metrica_efecto": "cramers_v",
            "magnitud_efecto": interpret_cramers(v),
            "supuesto_ok": True,
            "nota_supuesto": f"Fisher (expected<5 en {pct_low:.0%} celdas)",
        }
    v = cramers_v(ct.values.astype(float))
    return {
        "dataset": dataset,
        "variable_faltante": target,
        "covariable": cat_col,
        "tipo_covariable": "categorica",
        "prueba": "chi2",
        "n": int(ct.values.sum()),
        "estadistico": round(float(chi2), 4),
        "gl": int(dof),
        "p_valor": float(p),
        "efecto": round(v, 4),
        "metrica_efecto": "cramers_v",
        "magnitud_efecto": interpret_cramers(v),
        "supuesto_ok": ok,
        "nota_supuesto": (
            "expected≥5 ok" if ok else f"expected<5 en {pct_low:.0%} celdas (χ² aprox.)"
        ),
    }


def test_numerica(df: pd.DataFrame, r_col: str, num_col: str, dataset: str, target: str) -> dict:
    g0 = df.loc[df[r_col] == 0, num_col].dropna().astype(float).values
    g1 = df.loc[df[r_col] == 1, num_col].dropna().astype(float).values
    n0, n1 = len(g0), len(g1)
    base = {
        "dataset": dataset,
        "variable_faltante": target,
        "covariable": num_col,
        "tipo_covariable": "numerica",
        "n": int(n0 + n1),
        "n_completo_R0": n0,
        "n_faltante_R1": n1,
    }
    if n0 < 5 or n1 < 5:
        return {
            **base,
            "prueba": "n/a",
            "estadistico": np.nan,
            "gl": np.nan,
            "p_valor": np.nan,
            "efecto": np.nan,
            "metrica_efecto": "cliffs_delta",
            "magnitud_efecto": "n/a",
            "supuesto_ok": False,
            "nota_supuesto": "n insuficiente en un grupo",
        }

    # Normalidad (Shapiro, subsample)
    def shapiro_ok(a: np.ndarray) -> bool:
        sample = a if len(a) <= 5000 else np.random.default_rng(RANDOM_SEED).choice(a, 5000, replace=False)
        if len(sample) < 3:
            return False
        return float(stats.shapiro(sample).pvalue) >= ALPHA

    normal = shapiro_ok(g0) and shapiro_ok(g1)
    # Homocedasticidad (Levene) solo informativa para t
    levene_p = float(stats.levene(g0, g1).pvalue)

    if normal:
        # Welch t (no asume varianzas iguales)
        t_res = stats.ttest_ind(g0, g1, equal_var=False)
        # Cohen d (pooled approx con Welch)
        s0, s1 = g0.std(ddof=1), g1.std(ddof=1)
        d = (g1.mean() - g0.mean()) / np.sqrt((s0**2 + s1**2) / 2) if (s0 + s1) > 0 else np.nan
        return {
            **base,
            "prueba": "welch_t",
            "estadistico": round(float(t_res.statistic), 4),
            "gl": np.nan,
            "p_valor": float(t_res.pvalue),
            "efecto": round(float(d), 4) if d == d else np.nan,
            "metrica_efecto": "cohen_d",
            "magnitud_efecto": (
                "despreciable" if abs(d) < 0.2 else
                "pequeño" if abs(d) < 0.5 else
                "mediano" if abs(d) < 0.8 else "grande"
            ) if d == d else "n/a",
            "supuesto_ok": True,
            "nota_supuesto": f"Shapiro ok ambos; Levene p={levene_p:.3g} (Welch no requiere)",
        }

    u_res = stats.mannwhitneyu(g0, g1, alternative="two-sided")
    delta = cliffs_delta(g1, g0)  # R=1 vs R=0
    return {
        **base,
        "prueba": "mannwhitney_u",
        "estadistico": round(float(u_res.statistic), 4),
        "gl": np.nan,
        "p_valor": float(u_res.pvalue),
        "efecto": round(delta, 4),
        "metrica_efecto": "cliffs_delta",
        "magnitud_efecto": interpret_delta(delta),
        "supuesto_ok": True,
        "nota_supuesto": f"no normalidad → MWU; Levene p={levene_p:.3g}",
    }


def fit_logit(df: pd.DataFrame, formula: str, dataset: str, target: str, modelo: str) -> tuple[dict, pd.DataFrame]:
    """Ajusta logit y retorna resumen LR + tabla de coeficientes (OR)."""
    model_df = df.copy()
    # dropna solo en variables del modelo (formula parsing simple)
    # statsmodels formula maneja missing; usamos dropna explícito de columnas usadas
    try:
        fit = smf.logit(formula, data=model_df).fit(disp=False, maxiter=200)
        # modelo nulo
        y = fit.model.endog
        null = sm.Logit(y, np.ones((len(y), 1))).fit(disp=False, maxiter=200)
        lr_stat = float(2 * (fit.llf - null.llf))
        lr_df = int(fit.df_model)
        lr_p = float(stats.chi2.sf(lr_stat, lr_df)) if lr_df > 0 else np.nan
        # pseudo R2 McFadden
        mcf = float(1 - fit.llf / null.llf) if null.llf != 0 else np.nan

        summary = {
            "dataset": dataset,
            "variable_faltante": target,
            "modelo": modelo,
            "formula": formula,
            "n": int(fit.nobs),
            "llf": round(float(fit.llf), 4),
            "llf_null": round(float(null.llf), 4),
            "lr_stat": round(lr_stat, 4),
            "lr_df": lr_df,
            "lr_p": lr_p,
            "pseudo_r2_mcfadden": round(mcf, 4) if mcf == mcf else np.nan,
            "converged": bool(fit.mle_retvals.get("converged", True)),
        }

        coefs = []
        params = fit.params
        conf = fit.conf_int()
        pvals = fit.pvalues
        for name in params.index:
            if name == "Intercept":
                continue
            b = float(params[name])
            or_ = float(np.exp(b))
            lo, hi = float(np.exp(conf.loc[name, 0])), float(np.exp(conf.loc[name, 1]))
            coefs.append(
                {
                    "dataset": dataset,
                    "variable_faltante": target,
                    "modelo": modelo,
                    "termino": name,
                    "coef": round(b, 4),
                    "or": round(or_, 4),
                    "or_ic95_lo": round(lo, 4),
                    "or_ic95_hi": round(hi, 4),
                    "p_valor": float(pvals[name]),
                }
            )
        return summary, pd.DataFrame(coefs)
    except Exception as exc:
        summary = {
            "dataset": dataset,
            "variable_faltante": target,
            "modelo": modelo,
            "formula": formula,
            "n": np.nan,
            "llf": np.nan,
            "llf_null": np.nan,
            "lr_stat": np.nan,
            "lr_df": np.nan,
            "lr_p": np.nan,
            "pseudo_r2_mcfadden": np.nan,
            "converged": False,
            "error": str(exc),
        }
        return summary, pd.DataFrame()


# ──────────────────────────────────────────────────
# 3. Batería de tests univariados
# ──────────────────────────────────────────────────
print("\n[TESTS] Asociaciones univariadas R ⊥ X_obs ...")

test_rows: list[dict] = []

# --- empresas: miss_geo (ciudad ≡ departamento) ---
for cat in ["sector", "clase_riesgo"]:
    test_rows.append(test_chi2(emp, "miss_geo", cat, "empresas", "ciudad"))
for num in ["n_trabajadores", "antiguedad_meses"]:
    test_rows.append(test_numerica(emp, "miss_geo", num, "empresas", "ciudad"))
# prima observada (solo filas con prima no nula) como covariable de miss_geo
test_rows.append(test_numerica(emp.dropna(subset=["prima_anual"]), "miss_geo", "prima_anual", "empresas", "ciudad"))

# --- empresas: miss_prima ---
for cat in ["sector", "clase_riesgo"]:
    test_rows.append(test_chi2(emp, "miss_prima", cat, "empresas", "prima_anual"))
# miss_geo como categórica binaria
emp["_geo_cat"] = emp["miss_geo"].map({0: "geo_ok", 1: "geo_miss"})
test_rows.append(test_chi2(emp, "miss_prima", "_geo_cat", "empresas", "prima_anual"))
for num in ["n_trabajadores", "antiguedad_meses"]:
    test_rows.append(test_numerica(emp, "miss_prima", num, "empresas", "prima_anual"))

# --- siniestros: miss_parte ---
for cat in ["tipo", "gravedad"]:
    test_rows.append(test_chi2(sin, "miss_parte", cat, "siniestros", "parte_cuerpo"))
for num in ["costo_prestacion_economica"]:
    test_rows.append(test_numerica(sin, "miss_parte", num, "siniestros", "parte_cuerpo"))
test_rows.append(
    test_numerica(sin.dropna(subset=["dias_incapacidad"]), "miss_parte", "dias_incapacidad", "siniestros", "parte_cuerpo")
)
test_rows.append(
    test_numerica(sin.dropna(subset=["costo_asistencial"]), "miss_parte", "costo_asistencial", "siniestros", "parte_cuerpo")
)

# --- siniestros: miss_dias (señal D: tipo) ---
for cat in ["tipo", "gravedad"]:
    test_rows.append(test_chi2(sin, "miss_dias", cat, "siniestros", "dias_incapacidad"))
test_rows.append(test_numerica(sin, "miss_dias", "costo_prestacion_economica", "siniestros", "dias_incapacidad"))
test_rows.append(
    test_numerica(sin.dropna(subset=["costo_asistencial"]), "miss_dias", "costo_asistencial", "siniestros", "dias_incapacidad")
)

# --- siniestros: miss_costo_asist (señal D: gravedad) ---
for cat in ["tipo", "gravedad"]:
    test_rows.append(test_chi2(sin, "miss_costo_asist", cat, "siniestros", "costo_asistencial"))
test_rows.append(test_numerica(sin, "miss_costo_asist", "costo_prestacion_economica", "siniestros", "costo_asistencial"))
test_rows.append(
    test_numerica(sin.dropna(subset=["dias_incapacidad"]), "miss_costo_asist", "dias_incapacidad", "siniestros", "costo_asistencial")
)

tests_df = pd.DataFrame(test_rows)

# Holm por variable_faltante
tests_df["p_valor_ajustado_holm"] = np.nan
tests_df["rechaza_h0_ajustado"] = False
for var, idx in tests_df.groupby("variable_faltante").groups.items():
    ps = tests_df.loc[idx, "p_valor"].astype(float)
    valid = ps.notna()
    if valid.sum() == 0:
        continue
    reject, p_adj, _, _ = multipletests(ps[valid].values, alpha=ALPHA, method="holm")
    tests_df.loc[ps[valid].index, "p_valor_ajustado_holm"] = p_adj
    tests_df.loc[ps[valid].index, "rechaza_h0_ajustado"] = reject

print("\n  Tests univariados significativos tras Holm:")
sig = tests_df[tests_df["rechaza_h0_ajustado"] == True]  # noqa: E712
if sig.empty:
    print("    (ninguno)")
else:
    for _, r in sig.sort_values(["variable_faltante", "p_valor_ajustado_holm"]).iterrows():
        print(
            f"    {r['variable_faltante']} ~ {r['covariable']}: "
            f"{r['prueba']} p_adj={r['p_valor_ajustado_holm']:.3g} "
            f"| {r['metrica_efecto']}={r['efecto']} ({r['magnitud_efecto']})"
        )


# ──────────────────────────────────────────────────
# 4. Regresiones logísticas (multivariadas)
# ──────────────────────────────────────────────────
print("\n[LOGIT] Regresiones de indicadoras R ~ X_obs ...")

logit_summaries: list[dict] = []
logit_coefs_list: list[pd.DataFrame] = []

# Modelos alineados a señales D + controles administrativos
modelos = [
    # empresas
    ("empresas", "ciudad", "geo_base", "miss_geo ~ C(sector) + C(clase_riesgo)", emp),
    (
        "empresas",
        "ciudad",
        "geo_full",
        "miss_geo ~ C(sector) + C(clase_riesgo) + log_n_trabajadores + antiguedad_meses",
        emp,
    ),
    (
        "empresas",
        "prima_anual",
        "prima_base",
        "miss_prima ~ C(clase_riesgo) + C(sector)",
        emp,
    ),
    (
        "empresas",
        "prima_anual",
        "prima_full",
        "miss_prima ~ C(clase_riesgo) + C(sector) + log_n_trabajadores + antiguedad_meses + miss_geo",
        emp,
    ),
    # siniestros – señales D
    (
        "siniestros",
        "dias_incapacidad",
        "dias_tipo",
        "miss_dias ~ C(tipo)",
        sin,
    ),
    (
        "siniestros",
        "dias_incapacidad",
        "dias_full",
        "miss_dias ~ C(tipo) + C(gravedad) + log_costo_prestacion",
        sin,
    ),
    (
        "siniestros",
        "costo_asistencial",
        "costo_gravedad",
        "miss_costo_asist ~ C(gravedad)",
        sin,
    ),
    (
        "siniestros",
        "costo_asistencial",
        "costo_full",
        "miss_costo_asist ~ C(gravedad) + C(tipo) + log_costo_prestacion",
        sin,
    ),
    (
        "siniestros",
        "parte_cuerpo",
        "parte_full",
        "miss_parte ~ C(tipo) + C(gravedad) + log_costo_prestacion",
        sin,
    ),
]

for dataset, target, nombre, formula, dframe in modelos:
    summary, coefs = fit_logit(dframe, formula, dataset, target, nombre)
    logit_summaries.append(summary)
    if not coefs.empty:
        logit_coefs_list.append(coefs)
    p_txt = f"{summary['lr_p']:.3g}" if summary.get("lr_p") == summary.get("lr_p") else "NA"
    print(
        f"  {target}/{nombre}: n={summary.get('n')}  LR p={p_txt}  "
        f"pseudoR²={summary.get('pseudo_r2_mcfadden')}"
    )

logit_sum_df = pd.DataFrame(logit_summaries)
logit_coef_df = pd.concat(logit_coefs_list, ignore_index=True) if logit_coefs_list else pd.DataFrame()

# Holm sobre LR p de modelos "full" / señal principal (uno por variable)
primary_models = {
    "ciudad": "geo_full",
    "prima_anual": "prima_full",
    "dias_incapacidad": "dias_full",
    "costo_asistencial": "costo_full",
    "parte_cuerpo": "parte_full",
}
logit_sum_df["es_modelo_primario"] = logit_sum_df.apply(
    lambda r: primary_models.get(r["variable_faltante"]) == r["modelo"], axis=1
)
prim = logit_sum_df[logit_sum_df["es_modelo_primario"]].copy()
if not prim.empty and prim["lr_p"].notna().any():
    rej, p_adj, _, _ = multipletests(prim["lr_p"].fillna(1).values, alpha=ALPHA, method="holm")
    logit_sum_df.loc[prim.index, "lr_p_ajustado_holm"] = p_adj
    logit_sum_df.loc[prim.index, "rechaza_mcar_logit"] = rej


# ──────────────────────────────────────────────────
# 5. Veredictos por variable
# ──────────────────────────────────────────────────
print("\n[VEREDICTO] Mecanismo por variable...")


def veredicto_variable(var: str, dataset: str) -> dict:
    uni = tests_df[tests_df["variable_faltante"] == var]
    n_sig = int(uni["rechaza_h0_ajustado"].sum())
    logit_row = logit_sum_df[
        (logit_sum_df["variable_faltante"] == var) & (logit_sum_df["es_modelo_primario"])
    ]
    lr_p = float(logit_row["lr_p"].iloc[0]) if len(logit_row) else np.nan
    lr_p_adj = (
        float(logit_row["lr_p_ajustado_holm"].iloc[0])
        if len(logit_row) and "lr_p_ajustado_holm" in logit_row.columns
        else lr_p
    )
    pseudo = float(logit_row["pseudo_r2_mcfadden"].iloc[0]) if len(logit_row) else np.nan
    rechaza_logit = bool(lr_p_adj < ALPHA) if lr_p_adj == lr_p_adj else False
    rechaza_uni = n_sig > 0

    # Señales clave
    top = uni.sort_values("p_valor").head(3)
    top_txt = "; ".join(
        f"{r.covariable}({r.prueba} p_adj={r.p_valor_ajustado_holm:.2g}, {r.metrica_efecto}={r.efecto})"
        for r in top.itertuples()
        if r.p_valor == r.p_valor
    )

    # MNAR: no identificable; sospecha documentada
    sospecha_mnar = False
    nota_mnar = "MNAR no identificable solo con observados."

    if var == "costo_asistencial":
        # Si gravedad (admin) + costo_prestacion (proxy de magnitud económica) predicen R
        g = uni[uni["covariable"] == "gravedad"]
        c = uni[uni["covariable"] == "costo_prestacion_economica"]
        g_sig = bool(g["rechaza_h0_ajustado"].any()) if len(g) else False
        c_sig = bool(c["rechaza_h0_ajustado"].any()) if len(c) else False
        # OR de log_costo_prestacion en modelo full
        coef = logit_coef_df[
            (logit_coef_df["variable_faltante"] == var)
            & (logit_coef_df["modelo"] == "costo_full")
            & (logit_coef_df["termino"] == "log_costo_prestacion")
        ]
        prest_or_sig = bool((coef["p_valor"] < ALPHA).any()) if len(coef) else False
        if g_sig and (c_sig or prest_or_sig):
            sospecha_mnar = True
            nota_mnar = (
                "Sospecha MNAR parcial: además de gravedad (MAR), el proxy "
                "costo_prestacion predice el faltante de costo_asistencial — "
                "compatible con costos aún no liquidados / no reportados en "
                "eventos de alta severidad económica. No es prueba concluyente."
            )
        elif g_sig:
            nota_mnar = (
                "Patrón bien explicado por gravedad observada → MAR operativo; "
                "MNAR residual no descartable (p. ej. siniestros mortales con "
                "expediente de costo abierto)."
            )

    if var == "dias_incapacidad":
        t = uni[uni["covariable"] == "tipo"]
        if bool(t["rechaza_h0_ajustado"].any()):
            nota_mnar = (
                "Dependencia fuerte de tipo (EL≫AT) → MAR respecto de tipo. "
                "MNAR posible si la duración real (no observada) determina el "
                "no-registro, pero no contrastable aquí."
            )

    if var == "ciudad":
        # geo bloque; si no hay asociaciones fuertes → MCAR compatible
        nota_mnar = (
            "Bloque ciudad=departamento (patrón 1.4.1). MNAR poco plausible "
            "sin proceso de no-reporte geográfico ligado al valor mismo."
        )

    if var == "prima_anual":
        nota_mnar = (
            "Si no hay dependencia de observados → compatible con MCAR; "
            "MNAR (prima omitida por ser atípica) no contrastable sin auditoría."
        )

    if var == "parte_cuerpo":
        nota_mnar = (
            "Si asociaciones con observados son nulas/débiles → MCAR compatible; "
            "MNAR (parte no registrada por sensibilidad) no contrastable."
        )

    # Clasificación formal
    if not rechaza_uni and not rechaza_logit:
        mecanismo = "MCAR (no se rechaza)"
        evidencia = (
            f"Ninguna asociación univariada significativa tras Holm "
            f"(n_sig={n_sig}); LR logit primario p_adj={lr_p_adj:.3g}."
        )
    else:
        mecanismo = "MAR (depende de observados)"
        evidencia = (
            f"{n_sig} test(s) univariado(s) rechazan H0 tras Holm; "
            f"LR logit p_adj={lr_p_adj:.3g}, pseudoR²={pseudo:.3g}. "
            f"Top: {top_txt}"
        )
        if sospecha_mnar:
            mecanismo = "MAR con sospecha MNAR"

    return {
        "dataset": dataset,
        "variable_faltante": var,
        "n_faltantes": int(
            emp[var].isna().sum() if dataset == "empresas" and var in emp.columns
            else (
                emp["ciudad"].isna().sum() if var == "ciudad"
                else sin[
                    {"parte_cuerpo": "parte_cuerpo", "dias_incapacidad": "dias_incapacidad", "costo_asistencial": "costo_asistencial"}[var]
                ].isna().sum()
            )
        ),
        "pct_faltantes": round(
            100
            * (
                emp["ciudad"].isna().mean() if var == "ciudad"
                else emp["prima_anual"].isna().mean() if var == "prima_anual"
                else sin[var].isna().mean()
            ),
            4,
        ),
        "n_tests_univariados": int(len(uni)),
        "n_rechazos_holm": n_sig,
        "lr_p_modelo_primario": lr_p,
        "lr_p_ajustado_holm": lr_p_adj,
        "pseudo_r2_mcfadden": pseudo,
        "mecanismo": mecanismo,
        "sospecha_mnar": sospecha_mnar,
        "evidencia": evidencia,
        "nota_mnar": nota_mnar,
        "implicacion_imputacion": (
            "Imputación simple (media/moda) razonable si MCAR; "
            "preferir imputación condicionada / MICE si MAR; "
            "si sospecha MNAR, modelar missingness o análisis de sensibilidad."
            if "MCAR" in mecanismo
            else (
                "Usar imputación que condicione por las covariables asociadas "
                "(MAR); no listwise deletion. "
                + (
                    "Complementar con sensibilidad MNAR / flag de missing."
                    if sospecha_mnar
                    else ""
                )
            )
        ),
    }


# Fix n_faltantes helper more cleanly
def count_miss(dataset: str, var: str) -> tuple[int, float]:
    if dataset == "empresas":
        col = "ciudad" if var == "ciudad" else var
        s = emp[col]
    else:
        s = sin[var]
    return int(s.isna().sum()), round(100 * float(s.isna().mean()), 4)


veredictos = []
for dataset, var in [
    ("empresas", "ciudad"),
    ("empresas", "prima_anual"),
    ("siniestros", "parte_cuerpo"),
    ("siniestros", "dias_incapacidad"),
    ("siniestros", "costo_asistencial"),
]:
    v = veredicto_variable(var, dataset)
    n, pct = count_miss(dataset, var)
    v["n_faltantes"] = n
    v["pct_faltantes"] = pct
    # departamento: mismo veredicto que ciudad
    veredictos.append(v)
    print(f"  {dataset}.{var}: {v['mecanismo']}  (rechazos Holm={v['n_rechazos_holm']}, LR p_adj={v['lr_p_ajustado_holm']:.3g})")

# Agregar fila explícita para departamento (= ciudad)
dep = dict(veredictos[0])
dep["variable_faltante"] = "departamento"
dep["evidencia"] = (
    "Idéntico a ciudad (224 filas, correlación perfecta de indicadoras). "
    + dep["evidencia"]
)
veredictos.insert(1, dep)

veredicto_df = pd.DataFrame(veredictos)


# ──────────────────────────────────────────────────
# 6. Persistencia
# ──────────────────────────────────────────────────
print("\n[SAVE] Resultados y staging...")

# Limpiar columnas auxiliares de tests antes de guardar
cols_tests = [
    "dataset", "variable_faltante", "covariable", "tipo_covariable", "prueba",
    "n", "estadistico", "gl", "p_valor", "p_valor_ajustado_holm", "rechaza_h0_ajustado",
    "efecto", "metrica_efecto", "magnitud_efecto", "supuesto_ok", "nota_supuesto",
]
# n_completo opcionales
for c in ["n_completo_R0", "n_faltante_R1"]:
    if c in tests_df.columns:
        cols_tests.append(c)

tests_out = tests_df[[c for c in cols_tests if c in tests_df.columns]].copy()
tests_out.to_csv(RESULTS_DIR / "faltantes_mecanismos_tests.csv", index=False, encoding="utf-8")
tests_out.to_parquet(DATA_STAGING / "faltantes_mecanismos_tests.parquet", index=False)

logit_sum_df.to_csv(RESULTS_DIR / "faltantes_mecanismos_logit_resumen.csv", index=False, encoding="utf-8")
logit_coef_df.to_csv(RESULTS_DIR / "faltantes_mecanismos_logit_coefs.csv", index=False, encoding="utf-8")
# staging: unificar resumen + coefs en un parquet de resumen y otro de coefs
logit_sum_df.to_parquet(DATA_STAGING / "faltantes_mecanismos_logit.parquet", index=False)
logit_coef_df.to_parquet(DATA_STAGING / "faltantes_mecanismos_logit_coefs.parquet", index=False)

veredicto_df.to_csv(RESULTS_DIR / "faltantes_mecanismos_veredicto.csv", index=False, encoding="utf-8")
veredicto_df.to_parquet(DATA_STAGING / "faltantes_mecanismos_veredicto.parquet", index=False)

print("  ✓ CSV results + parquet staging")


# ──────────────────────────────────────────────────
# 7. Plots
# ──────────────────────────────────────────────────
print("\n[PLOT] Figuras...")

# ── 7.1 Señales sección D con anotación de tests formales ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Señales §D con pruebas formales (χ² / Fisher)",
    subtitle="Tasas de faltantes estratificadas + p Holm y Cramér V",
)
ax1, ax2 = axes[0], axes[1]

# dias × tipo
sub = estratos[
    (estratos["dataset"] == "siniestros")
    & (estratos["estrato_variable"] == "tipo")
    & (estratos["columna"] == "dias_incapacidad")
].sort_values("estrato_valor")
t_row = tests_df[
    (tests_df["variable_faltante"] == "dias_incapacidad") & (tests_df["covariable"] == "tipo")
].iloc[0]
ax1.bar(sub["estrato_valor"], sub["pct_faltantes"], color=sb.AQUA_SURA.hex, alpha=0.9)
ax1.set_ylabel("% faltantes")
ax1.set_title(
    f"dias_incapacidad × tipo\n"
    f"{t_row['prueba']}: p_adj={t_row['p_valor_ajustado_holm']:.2e} · V={t_row['efecto']:.3f} ({t_row['magnitud_efecto']})"
)
for i, (_, r) in enumerate(sub.iterrows()):
    ax1.text(i, r["pct_faltantes"] + 0.4, f"{r['pct_faltantes']:.1f}%", ha="center", fontsize=9)
ax1.set_ylim(0, max(sub["pct_faltantes"].max() * 1.35, 15))

# costo × gravedad
orden = ["leve", "grave", "mortal"]
sub2 = estratos[
    (estratos["dataset"] == "siniestros")
    & (estratos["estrato_variable"] == "gravedad")
    & (estratos["columna"] == "costo_asistencial")
].copy()
sub2["ord"] = sub2["estrato_valor"].map({v: i for i, v in enumerate(orden)})
sub2 = sub2.sort_values("ord")
c_row = tests_df[
    (tests_df["variable_faltante"] == "costo_asistencial") & (tests_df["covariable"] == "gravedad")
].iloc[0]
ax2.bar(sub2["estrato_valor"], sub2["pct_faltantes"], color=sb.AZUL_SURA.hex, alpha=0.9)
ax2.set_ylabel("% faltantes")
ax2.set_title(
    f"costo_asistencial × gravedad\n"
    f"{c_row['prueba']}: p_adj={c_row['p_valor_ajustado_holm']:.2e} · V={c_row['efecto']:.3f} ({c_row['magnitud_efecto']})"
)
for i, (_, r) in enumerate(sub2.iterrows()):
    ax2.text(i, r["pct_faltantes"] + 0.8, f"{r['pct_faltantes']:.1f}%", ha="center", fontsize=9)
ax2.set_ylim(0, max(sub2["pct_faltantes"].max() * 1.25, 40))

sb.add_sura_footer(fig, text="S01-1.4.2 | Señales D – tests formales")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_mecanismos_senales_D.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 02_mecanismos_senales_D.png")

# ── 7.2 Heatmap -log10(p_adj) por variable × covariable ──
heat = tests_df.dropna(subset=["p_valor_ajustado_holm"]).copy()
heat["neglog"] = -np.log10(heat["p_valor_ajustado_holm"].clip(lower=1e-300))
pivot = heat.pivot_table(
    index="variable_faltante",
    columns="covariable",
    values="neglog",
    aggfunc="max",
)
# orden filas
row_order = [v for v in ["ciudad", "prima_anual", "parte_cuerpo", "dias_incapacidad", "costo_asistencial"] if v in pivot.index]
pivot = pivot.reindex(row_order)

fig, ax = plt.subplots(figsize=(11, 4.8))
im = ax.imshow(pivot.fillna(0).values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=max(5, pivot.values[np.isfinite(pivot.values)].max()))
ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index, fontsize=9)
ax.set_title("Fuerza de evidencia contra MCAR (−log₁₀ p Holm)")
# anotar
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        val = pivot.values[i, j]
        if not np.isfinite(val):
            txt = "—"
        else:
            txt = f"{val:.1f}"
        ax.text(j, i, txt, ha="center", va="center", fontsize=7,
                color="white" if val > 2.5 else "black")
# umbral α=0.05 → -log10 ≈ 1.3
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("−log₁₀(p_adj)")
ax.axhline(-0.5, color="none")
sb.add_sura_footer(fig, text="S01-1.4.2 | Mapa de evidencia vs MCAR (Holm)")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_mecanismos_heatmap_pvalores.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 02_mecanismos_heatmap_pvalores.png")

# ── 7.3 Forest OR de modelos señal / full clave ──
focus_models = ["dias_tipo", "dias_full", "costo_gravedad", "costo_full", "prima_full", "geo_full"]
coef_plot = logit_coef_df[logit_coef_df["modelo"].isin(focus_models)].copy()
# acortar nombres
coef_plot["label"] = coef_plot["variable_faltante"] + " | " + coef_plot["termino"]
coef_plot = coef_plot.sort_values(["variable_faltante", "or"], ascending=[True, True])

fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(coef_plot))))
y = np.arange(len(coef_plot))
ax.errorbar(
    coef_plot["or"],
    y,
    xerr=[
        coef_plot["or"] - coef_plot["or_ic95_lo"],
        coef_plot["or_ic95_hi"] - coef_plot["or"],
    ],
    fmt="o",
    color=sb.AZUL_SURA.hex,
    ecolor=sb.AQUA_SURA.hex,
    capsize=3,
    markersize=5,
)
ax.axvline(1.0, color=sb.GRIS_MEDIO.hex, ls="--", lw=1)
ax.set_yticks(y)
ax.set_yticklabels(coef_plot["label"], fontsize=7)
ax.set_xlabel("Odds Ratio (IC 95%)")
ax.set_xscale("log")
ax.set_title("Regresión logística de R: OR de covariables (modelos clave)")
sb.add_sura_footer(fig, text="S01-1.4.2 | OR logit de missingness")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_mecanismos_logit_OR.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 02_mecanismos_logit_OR.png")

# ── 7.4 Empresas: prima × clase y ciudad × sector (señales D secundarias) ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Empresas: señales §D (prima × clase, ciudad × sector)",
    subtitle="Tasas + χ² con p Holm",
)
ax1, ax2 = axes[0], axes[1]

p_cls = estratos[
    (estratos["dataset"] == "empresas")
    & (estratos["estrato_variable"] == "clase_riesgo")
    & (estratos["columna"] == "prima_anual")
].sort_values("estrato_valor")
r_prima = tests_df[
    (tests_df["variable_faltante"] == "prima_anual") & (tests_df["covariable"] == "clase_riesgo")
].iloc[0]
ax1.bar(p_cls["estrato_valor"].astype(str), p_cls["pct_faltantes"], color=sb.AZUL_SURA.hex, alpha=0.9)
ax1.set_xlabel("clase_riesgo")
ax1.set_ylabel("% faltantes prima_anual")
ax1.set_title(
    f"prima_anual × clase_riesgo\n"
    f"p_adj={r_prima['p_valor_ajustado_holm']:.3g} · V={r_prima['efecto']:.3f}"
)
ax1.set_ylim(0, max(p_cls["pct_faltantes"].max() * 1.3, 20))

c_sec = estratos[
    (estratos["dataset"] == "empresas")
    & (estratos["estrato_variable"] == "sector")
    & (estratos["columna"] == "ciudad")
].sort_values("pct_faltantes", ascending=True)
r_geo = tests_df[
    (tests_df["variable_faltante"] == "ciudad") & (tests_df["covariable"] == "sector")
].iloc[0]
ax2.barh(c_sec["estrato_valor"], c_sec["pct_faltantes"], color=sb.AQUA_SURA.hex, alpha=0.9)
ax2.set_xlabel("% faltantes ciudad")
ax2.set_title(
    f"ciudad × sector\n"
    f"p_adj={r_geo['p_valor_ajustado_holm']:.3g} · V={r_geo['efecto']:.3f}"
)
sb.add_sura_footer(fig, text="S01-1.4.2 | Señales empresas")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_mecanismos_empresas_senales.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 02_mecanismos_empresas_senales.png")

# ── 7.5 Resumen de veredictos ──
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.axis("off")
colors_map = {
    "MCAR (no se rechaza)": "#4CAF50",
    "MAR (depende de observados)": sb.AQUA_SURA.hex,
    "MAR con sospecha MNAR": "#E67E22",
}
# tabla visual
disp = veredicto_df[
    ["dataset", "variable_faltante", "pct_faltantes", "n_rechazos_holm", "lr_p_ajustado_holm", "mecanismo"]
].copy()
disp["pct_faltantes"] = disp["pct_faltantes"].map(lambda x: f"{x:.2f}%")
disp["lr_p_ajustado_holm"] = disp["lr_p_ajustado_holm"].map(
    lambda x: f"{x:.2e}" if pd.notna(x) else "—"
)
col_labels = ["Dataset", "Variable", "% falt.", "# rech. Holm", "LR p Holm", "Mecanismo"]
table = ax.table(
    cellText=disp.values,
    colLabels=col_labels,
    loc="center",
    cellLoc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(8)
table.scale(1.15, 1.55)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_facecolor(sb.AZUL_SURA.hex)
        cell.set_text_props(color="white", fontweight="bold")
    elif col == 5 and row > 0:
        mech = disp.iloc[row - 1]["mecanismo"]
        cell.set_facecolor(colors_map.get(mech, "#EEEEEE"))
        cell.set_text_props(fontsize=7)
ax.set_title("Veredicto de mecanismo por variable", pad=12, fontsize=12, color=sb.AZUL_SURA.hex)
legend_elems = [Patch(facecolor=c, label=k) for k, c in colors_map.items()]
ax.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=8)
sb.add_sura_footer(fig, text="S01-1.4.2 | Veredictos MCAR / MAR / MNAR")
fig.tight_layout(rect=[0, 0.08, 1, 1])
fig.savefig(IMGS_DIR / "02_mecanismos_veredictos.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 02_mecanismos_veredictos.png")


print("\n" + "=" * 70)
print("  Ejecución completada.")
print("=" * 70)
print("\n  Resumen de mecanismos:")
for _, r in veredicto_df.iterrows():
    print(f"    {r['dataset']}.{r['variable_faltante']}: {r['mecanismo']}")
print("\n  Archivos: results/imgs/02_*.png + faltantes_mecanismos_*.csv")
print("  Staging: faltantes_mecanismos_{tests,logit,logit_coefs,veredicto}.parquet")
