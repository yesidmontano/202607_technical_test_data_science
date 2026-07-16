"""
Diagnóstico de Datos Faltantes – Estrategia de Imputación
========================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.4 – Diagnóstico de datos faltantes
Proceso: 1.4.3 – Propuesta y aplicación de imputación

Descripción:
    Aplica estrategias diferenciadas según mecanismos de 1.4.2:

    MCAR (no se rechaza)
      · ciudad / departamento  → categoría 'desconocido' (bloque geo)
      · parte_cuerpo           → categoría 'desconocido'

    MAR
      · prima_anual → regresión condicionada (estilo MICE univariado) en
        escala log: log1p(prima) ~ C(sector) + log1p(n_trabajadores)
        + antiguedad_meses  (+ predicción estocástica con residuales)
      · dias_incapacidad → OLS log1p(dias) ~ C(tipo) + C(gravedad)
        + log1p(costo_prestacion_economica)
      · costo_asistencial → OLS log1p(costo) ~ C(tipo) + C(gravedad)
        + log1p(costo_prestacion_economica) + log1p(dias_imputados)
        (flag miss_* conservado por sospecha MNAR → sensibilidad en 1.4.4)

    No modifica empresas_staging / siniestros_staging (inmutables 1.2).
    Genera datasets imputados nuevos en staging.

Inputs (reutilizados):
    - data/raw/empresas.csv, data/raw/siniestros.csv
    - data/staging/S01/faltantes_mecanismos_veredicto.parquet

Outputs:
    - data/staging/S01/empresas_imputadas.parquet
    - data/staging/S01/siniestros_imputados.parquet
    - data/staging/S01/faltantes_imputacion_estrategia.parquet
    - data/staging/S01/faltantes_imputacion_diagnostico.parquet
    - results/imgs/03_*.png
    - results/faltantes_imputacion_*.csv

Uso:
    .venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/03-estrategia_imputacion/estrategia_imputacion.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)
DESCONOCIDO = "desconocido"

ROOT = Path(__file__).resolve().parents[5]
DATA_RAW = ROOT / "data" / "raw"
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"
DATA_STAGING.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S01-1.4.3 | Estrategia de imputación (según mecanismos 1.4.2)")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando raw + veredictos 1.4.2...")
empresas = pd.read_csv(DATA_RAW / "empresas.csv", parse_dates=["fecha_afiliacion"])
siniestros = pd.read_csv(DATA_RAW / "siniestros.csv", parse_dates=["fecha_ocurrencia"])
veredictos = pd.read_parquet(DATA_STAGING / "faltantes_mecanismos_veredicto.parquet")

print(f"  empresas:   {empresas.shape}")
print(f"  siniestros: {siniestros.shape}")
print(f"  veredictos (reutilizado): {veredictos.shape}")

estrategia_rows: list[dict] = []
diag_rows: list[dict] = []


def add_estrategia(**kwargs):
    estrategia_rows.append(kwargs)


def dist_stats(series: pd.Series, label: str, dataset: str, variable: str, etapa: str) -> dict:
    s = series.dropna().astype(float)
    return {
        "dataset": dataset,
        "variable": variable,
        "etapa": etapa,
        "label": label,
        "n": int(len(s)),
        "mean": float(s.mean()) if len(s) else np.nan,
        "median": float(s.median()) if len(s) else np.nan,
        "std": float(s.std()) if len(s) else np.nan,
        "p25": float(s.quantile(0.25)) if len(s) else np.nan,
        "p75": float(s.quantile(0.75)) if len(s) else np.nan,
        "min": float(s.min()) if len(s) else np.nan,
        "max": float(s.max()) if len(s) else np.nan,
    }


def impute_log_ols(
    df: pd.DataFrame,
    target: str,
    formula_rhs: str,
    mask_miss: pd.Series,
    *,
    stochastic: bool = True,
    min_value: float = 0.0,
) -> tuple[pd.Series, dict]:
    """
    Imputa target en escala log1p vía OLS sobre casos completos.
    Predicción estocástica: ŷ + ε, ε ~ N(0, σ²_resid) (estilo MICE univariado).
    """
    out = df[target].astype(float).copy()
    work = df.copy()
    work["_y_log"] = np.log1p(work[target].astype(float))
    formula = f"_y_log ~ {formula_rhs}"
    train = work.loc[~mask_miss].dropna(subset=["_y_log"])
    # dropna en predictores implícito por OLS
    model = smf.ols(formula, data=train).fit()
    pred_log = model.predict(work.loc[mask_miss])
    if stochastic:
        sigma = float(np.sqrt(model.scale))
        pred_log = pred_log + rng.normal(0.0, sigma, size=len(pred_log))
    imputed = np.expm1(pred_log.to_numpy(dtype=float))
    imputed = np.clip(imputed, min_value, None)
    # días enteros si aplica
    if target == "dias_incapacidad":
        imputed = np.maximum(np.rint(imputed), min_value)
    out.loc[mask_miss] = imputed
    meta = {
        "formula": formula,
        "n_train": int(model.nobs),
        "n_imputed": int(mask_miss.sum()),
        "r2": round(float(model.rsquared), 4),
        "sigma_resid": round(float(np.sqrt(model.scale)), 4),
        "stochastic": stochastic,
    }
    return out, meta


# ──────────────────────────────────────────────────
# 2. EMPRESAS
# ──────────────────────────────────────────────────
print("\n[EMPRESAS] Imputación diferenciada...")

emp = empresas.copy()
emp["miss_ciudad"] = emp["ciudad"].isna().astype(int)
emp["miss_departamento"] = emp["departamento"].isna().astype(int)
emp["miss_geo"] = emp["miss_ciudad"]  # idéntico
emp["miss_prima"] = emp["prima_anual"].isna().astype(int)

assert (emp["miss_ciudad"] == emp["miss_departamento"]).all()

# --- MCAR: ciudad / departamento → 'desconocido' ---
n_geo = int(emp["miss_geo"].sum())
emp["ciudad_imp"] = emp["ciudad"].fillna(DESCONOCIDO)
emp["departamento_imp"] = emp["departamento"].fillna(DESCONOCIDO)
print(f"  ciudad/departamento: {n_geo} filas → '{DESCONOCIDO}' (MCAR)")

add_estrategia(
    dataset="empresas",
    variable="ciudad",
    mecanismo="MCAR (no se rechaza)",
    estrategia="categoria_desconocido",
    detalle=f"fillna('{DESCONOCIDO}'); bloque geo con departamento",
    n_imputados=n_geo,
    pct_imputados=round(100 * n_geo / len(emp), 4),
    formula=None,
    r2_modelo=None,
    columna_salida="ciudad_imp",
)
add_estrategia(
    dataset="empresas",
    variable="departamento",
    mecanismo="MCAR (no se rechaza)",
    estrategia="categoria_desconocido",
    detalle=f"fillna('{DESCONOCIDO}'); idéntico a ciudad",
    n_imputados=n_geo,
    pct_imputados=round(100 * n_geo / len(emp), 4),
    formula=None,
    r2_modelo=None,
    columna_salida="departamento_imp",
)

# --- MAR: prima_anual → regresión condicionada (MICE-style univariado) ---
diag_rows.append(dist_stats(emp["prima_anual"], "observado", "empresas", "prima_anual", "antes"))
mask_prima = emp["miss_prima"].astype(bool)
emp["log_n_trabajadores"] = np.log1p(emp["n_trabajadores"])
prima_imp, meta_prima = impute_log_ols(
    emp,
    "prima_anual",
    "C(sector) + log_n_trabajadores + antiguedad_meses",
    mask_prima,
    stochastic=True,
    min_value=0.0,
)
emp["prima_anual_imp"] = prima_imp
emp["log_prima_anual_imp"] = np.log1p(emp["prima_anual_imp"])
print(
    f"  prima_anual: {meta_prima['n_imputed']} filas | "
    f"OLS {meta_prima['formula']} | R²={meta_prima['r2']} σ={meta_prima['sigma_resid']}"
)

add_estrategia(
    dataset="empresas",
    variable="prima_anual",
    mecanismo="MAR (depende de observados)",
    estrategia="regresion_condicionada_log_OLS_estocastica",
    detalle=(
        "MICE univariado (única numérica incompleta del bloque): "
        "log1p(prima) ~ C(sector)+log1p(n_trabajadores)+antiguedad_meses; "
        "ŷ+ε, ε~N(0,σ²)"
    ),
    n_imputados=meta_prima["n_imputed"],
    pct_imputados=round(100 * meta_prima["n_imputed"] / len(emp), 4),
    formula=meta_prima["formula"],
    r2_modelo=meta_prima["r2"],
    columna_salida="prima_anual_imp",
)

diag_rows.append(
    dist_stats(
        emp.loc[~mask_prima, "prima_anual"],
        "observado_completo",
        "empresas",
        "prima_anual",
        "despues_ref",
    )
)
diag_rows.append(
    dist_stats(
        emp.loc[mask_prima, "prima_anual_imp"],
        "imputado",
        "empresas",
        "prima_anual",
        "despues",
    )
)
diag_rows.append(
    dist_stats(emp["prima_anual_imp"], "completo_post", "empresas", "prima_anual", "despues")
)

# Columnas de trabajo alineadas a staging
emp["ciudad"] = emp["ciudad_imp"]
emp["departamento"] = emp["departamento_imp"]
emp["prima_anual"] = emp["prima_anual_imp"]
emp["anio_afiliacion"] = emp["fecha_afiliacion"].dt.year
emp["log_prima_anual"] = emp["log_prima_anual_imp"]

empresas_imp = emp[
    [
        "id_empresa",
        "ciiu",
        "sector",
        "clase_riesgo",
        "n_trabajadores",
        "ciudad",
        "departamento",
        "antiguedad_meses",
        "prima_anual",
        "fecha_afiliacion",
        "anio_afiliacion",
        "log_n_trabajadores",
        "log_prima_anual",
        "miss_ciudad",
        "miss_departamento",
        "miss_geo",
        "miss_prima",
        "ciudad_imp",
        "departamento_imp",
        "prima_anual_imp",
    ]
].copy()
empresas_imp["clase_riesgo"] = empresas_imp["clase_riesgo"].astype("category")
empresas_imp["sector"] = empresas_imp["sector"].astype("category")

assert empresas_imp[["ciudad", "departamento", "prima_anual"]].isna().sum().sum() == 0
print(f"  ✓ empresas_imputadas: {empresas_imp.shape} | nulos restantes en targets: 0")


# ──────────────────────────────────────────────────
# 3. SINIESTROS
# ──────────────────────────────────────────────────
print("\n[SINIESTROS] Imputación diferenciada...")

sin = siniestros.copy()
sin["miss_parte"] = sin["parte_cuerpo"].isna().astype(int)
sin["miss_dias"] = sin["dias_incapacidad"].isna().astype(int)
sin["miss_costo_asist"] = sin["costo_asistencial"].isna().astype(int)
sin["log_costo_prestacion"] = np.log1p(sin["costo_prestacion_economica"])

# --- MCAR: parte_cuerpo → 'desconocido' ---
n_parte = int(sin["miss_parte"].sum())
sin["parte_cuerpo_imp"] = sin["parte_cuerpo"].fillna(DESCONOCIDO)
print(f"  parte_cuerpo: {n_parte} filas → '{DESCONOCIDO}' (MCAR)")

add_estrategia(
    dataset="siniestros",
    variable="parte_cuerpo",
    mecanismo="MCAR (no se rechaza)",
    estrategia="categoria_desconocido",
    detalle=f"fillna('{DESCONOCIDO}')",
    n_imputados=n_parte,
    pct_imputados=round(100 * n_parte / len(sin), 4),
    formula=None,
    r2_modelo=None,
    columna_salida="parte_cuerpo_imp",
)

# --- MAR: dias_incapacidad ---
diag_rows.append(
    dist_stats(sin["dias_incapacidad"], "observado", "siniestros", "dias_incapacidad", "antes")
)
mask_dias = sin["miss_dias"].astype(bool)
dias_imp, meta_dias = impute_log_ols(
    sin,
    "dias_incapacidad",
    "C(tipo) + C(gravedad) + log_costo_prestacion",
    mask_dias,
    stochastic=True,
    min_value=1.0,  # días de incapacidad ≥ 1 en observados
)
sin["dias_incapacidad_imp"] = dias_imp
print(
    f"  dias_incapacidad: {meta_dias['n_imputed']} filas | "
    f"R²={meta_dias['r2']} σ={meta_dias['sigma_resid']}"
)

add_estrategia(
    dataset="siniestros",
    variable="dias_incapacidad",
    mecanismo="MAR (depende de observados)",
    estrategia="regresion_condicionada_log_OLS_estocastica",
    detalle="log1p(dias)~C(tipo)+C(gravedad)+log1p(costo_prestacion); ŷ+ε",
    n_imputados=meta_dias["n_imputed"],
    pct_imputados=round(100 * meta_dias["n_imputed"] / len(sin), 4),
    formula=meta_dias["formula"],
    r2_modelo=meta_dias["r2"],
    columna_salida="dias_incapacidad_imp",
)

diag_rows.append(
    dist_stats(
        sin.loc[mask_dias, "dias_incapacidad_imp"],
        "imputado",
        "siniestros",
        "dias_incapacidad",
        "despues",
    )
)
diag_rows.append(
    dist_stats(
        sin["dias_incapacidad_imp"],
        "completo_post",
        "siniestros",
        "dias_incapacidad",
        "despues",
    )
)

# --- MAR (+ sospecha MNAR): costo_asistencial ---
# Usa días ya imputados como covariable adicional
diag_rows.append(
    dist_stats(sin["costo_asistencial"], "observado", "siniestros", "costo_asistencial", "antes")
)
sin["_dias_para_costo"] = sin["dias_incapacidad_imp"]
sin["log_dias_para_costo"] = np.log1p(sin["_dias_para_costo"])
mask_costo = sin["miss_costo_asist"].astype(bool)

# Temporalmente poner target con NaN y usar columna auxiliar en fórmula
costo_work = sin.copy()
costo_imp, meta_costo = impute_log_ols(
    costo_work,
    "costo_asistencial",
    "C(tipo) + C(gravedad) + log_costo_prestacion + log_dias_para_costo",
    mask_costo,
    stochastic=True,
    min_value=0.0,
)
sin["costo_asistencial_imp"] = costo_imp
print(
    f"  costo_asistencial: {meta_costo['n_imputed']} filas | "
    f"R²={meta_costo['r2']} σ={meta_costo['sigma_resid']} "
    f"(flag miss_costo_asist conservado → sensibilidad 1.4.4)"
)

add_estrategia(
    dataset="siniestros",
    variable="costo_asistencial",
    mecanismo="MAR con sospecha MNAR",
    estrategia="regresion_condicionada_log_OLS_estocastica",
    detalle=(
        "log1p(costo)~C(tipo)+C(gravedad)+log1p(prestacion)+log1p(dias_imp); "
        "conservar miss_costo_asist para sensibilidad MNAR en 1.4.4"
    ),
    n_imputados=meta_costo["n_imputed"],
    pct_imputados=round(100 * meta_costo["n_imputed"] / len(sin), 4),
    formula=meta_costo["formula"],
    r2_modelo=meta_costo["r2"],
    columna_salida="costo_asistencial_imp",
)

diag_rows.append(
    dist_stats(
        sin.loc[mask_costo, "costo_asistencial_imp"],
        "imputado",
        "siniestros",
        "costo_asistencial",
        "despues",
    )
)
diag_rows.append(
    dist_stats(
        sin["costo_asistencial_imp"],
        "completo_post",
        "siniestros",
        "costo_asistencial",
        "despues",
    )
)

# Derivadas post-imputación
sin["parte_cuerpo"] = sin["parte_cuerpo_imp"]
sin["dias_incapacidad"] = sin["dias_incapacidad_imp"]
sin["costo_asistencial"] = sin["costo_asistencial_imp"]
sin["anio"] = sin["fecha_ocurrencia"].dt.year
sin["mes"] = sin["fecha_ocurrencia"].dt.month
sin["costo_total"] = sin["costo_asistencial"] + sin["costo_prestacion_economica"]
sin["log_costo_total"] = np.log1p(sin["costo_total"])
sin["log_dias_incapacidad"] = np.log1p(sin["dias_incapacidad"])
sin["log_costo_asistencial"] = np.log1p(sin["costo_asistencial"])

siniestros_imp = sin[
    [
        "id_siniestro",
        "id_empresa",
        "fecha_ocurrencia",
        "tipo",
        "parte_cuerpo",
        "dias_incapacidad",
        "costo_asistencial",
        "costo_prestacion_economica",
        "gravedad",
        "anio",
        "mes",
        "costo_total",
        "log_costo_total",
        "log_dias_incapacidad",
        "log_costo_asistencial",
        "miss_parte",
        "miss_dias",
        "miss_costo_asist",
        "parte_cuerpo_imp",
        "dias_incapacidad_imp",
        "costo_asistencial_imp",
    ]
].copy()
siniestros_imp["tipo"] = siniestros_imp["tipo"].astype("category")
siniestros_imp["gravedad"] = siniestros_imp["gravedad"].astype("category")

assert (
    siniestros_imp[["parte_cuerpo", "dias_incapacidad", "costo_asistencial"]].isna().sum().sum()
    == 0
)
print(f"  ✓ siniestros_imputados: {siniestros_imp.shape} | nulos restantes en targets: 0")


# ──────────────────────────────────────────────────
# 4. Persistencia
# ──────────────────────────────────────────────────
print("\n[SAVE] Staging + CSV results...")

estrategia_df = pd.DataFrame(estrategia_rows)
diag_df = pd.DataFrame(diag_rows)

empresas_imp.to_parquet(DATA_STAGING / "empresas_imputadas.parquet", index=False)
siniestros_imp.to_parquet(DATA_STAGING / "siniestros_imputados.parquet", index=False)
estrategia_df.to_parquet(DATA_STAGING / "faltantes_imputacion_estrategia.parquet", index=False)
diag_df.to_parquet(DATA_STAGING / "faltantes_imputacion_diagnostico.parquet", index=False)

estrategia_df.to_csv(RESULTS_DIR / "faltantes_imputacion_estrategia.csv", index=False, encoding="utf-8")
diag_df.to_csv(RESULTS_DIR / "faltantes_imputacion_diagnostico.csv", index=False, encoding="utf-8")

print("  ✓ empresas_imputadas.parquet")
print("  ✓ siniestros_imputados.parquet")
print("  ✓ faltantes_imputacion_estrategia.parquet")
print("  ✓ faltantes_imputacion_diagnostico.parquet")


# ──────────────────────────────────────────────────
# 5. Plots
# ──────────────────────────────────────────────────
print("\n[PLOT] Figuras de diagnóstico...")

# ── 5.1 Resumen de estrategia ──
fig, ax = plt.subplots(figsize=(11, 3.8))
ax.axis("off")
disp = estrategia_df[
    ["dataset", "variable", "mecanismo", "estrategia", "n_imputados", "r2_modelo"]
].copy()
disp["r2_modelo"] = disp["r2_modelo"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
disp["estrategia"] = disp["estrategia"].str.replace("regresion_condicionada_log_OLS_estocastica", "OLS log estoc.")
disp["estrategia"] = disp["estrategia"].str.replace("categoria_desconocido", "desconocido")
disp["mecanismo"] = disp["mecanismo"].str.replace(" (no se rechaza)", "", regex=False)
disp["mecanismo"] = disp["mecanismo"].str.replace(" (depende de observados)", "", regex=False)
table = ax.table(
    cellText=disp.values,
    colLabels=["Dataset", "Variable", "Mecanismo", "Estrategia", "N imp.", "R²"],
    loc="center",
    cellLoc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(7.5)
table.scale(1.2, 1.45)
for (r, c), cell in table.get_celld().items():
    if r == 0:
        cell.set_facecolor(sb.AZUL_SURA.hex)
        cell.set_text_props(color="white", fontweight="bold")
ax.set_title("Estrategia de imputación aplicada (1.4.3)", color=sb.AZUL_SURA.hex, pad=8)
sb.add_sura_footer(fig, text="S01-1.4.3 | Catálogo de estrategias")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_imputacion_estrategia_resumen.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 03_imputacion_estrategia_resumen.png")

# ── 5.2 Prima: observado vs imputado (log) ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="prima_anual (MAR): distribución observada vs imputada",
    subtitle=f"OLS log | R²={meta_prima['r2']} | n imputados={meta_prima['n_imputed']}",
)
ax1, ax2 = axes[0], axes[1]
obs = np.log1p(empresas.loc[empresas["prima_anual"].notna(), "prima_anual"])
imp_vals = np.log1p(emp.loc[mask_prima, "prima_anual_imp"])
ax1.hist(obs, bins=40, density=True, alpha=0.75, color=sb.AZUL_SURA.hex, label="Observado")
ax1.hist(imp_vals, bins=30, density=True, alpha=0.55, color=sb.AQUA_SURA.hex, label="Imputado")
ax1.set_xlabel("log1p(prima_anual)")
ax1.set_ylabel("Densidad")
ax1.set_title("Overlapping densidades")
ax1.legend(fontsize=8)

# box por miss flag sobre valor final
ax2.boxplot(
    [obs, imp_vals],
    tick_labels=["Observado", "Imputado"],
    patch_artist=True,
    boxprops=dict(facecolor=sb.AZUL_SURA.hex, alpha=0.5),
)
ax2.set_ylabel("log1p(prima_anual)")
ax2.set_title("Comparación de nivel")
sb.add_sura_footer(fig, text="S01-1.4.3 | Imputación prima_anual")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_imputacion_prima_antes_despues.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 03_imputacion_prima_antes_despues.png")

# ── 5.3 Severidad: dias y costo ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Severidad (MAR): días y costo asistencial — observado vs imputado",
    subtitle=(
        f"dias R²={meta_dias['r2']} (n={meta_dias['n_imputed']}) · "
        f"costo R²={meta_costo['r2']} (n={meta_costo['n_imputed']})"
    ),
)
ax1, ax2 = axes[0], axes[1]

obs_d = np.log1p(siniestros.loc[siniestros["dias_incapacidad"].notna(), "dias_incapacidad"])
imp_d = np.log1p(sin.loc[mask_dias, "dias_incapacidad_imp"])
ax1.hist(obs_d, bins=40, density=True, alpha=0.75, color=sb.AZUL_SURA.hex, label="Observado")
ax1.hist(imp_d, bins=30, density=True, alpha=0.55, color=sb.AQUA_SURA.hex, label="Imputado")
ax1.set_xlabel("log1p(dias_incapacidad)")
ax1.set_title("Días de incapacidad")
ax1.legend(fontsize=8)

obs_c = np.log1p(siniestros.loc[siniestros["costo_asistencial"].notna(), "costo_asistencial"])
imp_c = np.log1p(sin.loc[mask_costo, "costo_asistencial_imp"])
ax2.hist(obs_c, bins=40, density=True, alpha=0.75, color=sb.AZUL_SURA.hex, label="Observado")
ax2.hist(imp_c, bins=30, density=True, alpha=0.55, color=sb.AQUA_SURA.hex, label="Imputado")
ax2.set_xlabel("log1p(costo_asistencial)")
ax2.set_title("Costo asistencial")
ax2.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01-1.4.3 | Imputación severidad")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_imputacion_severidad_antes_despues.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 03_imputacion_severidad_antes_despues.png")

# ── 5.4 MCAR categóricas: conteo 'desconocido' ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="MCAR: categoría 'desconocido' en variables categóricas",
    subtitle="ciudad/departamento (bloque) y parte_cuerpo",
)
ax1, ax2 = axes[0], axes[1]

geo_counts = emp["ciudad_imp"].value_counts()
top_geo = geo_counts.head(8)
ax1.barh(top_geo.index.astype(str)[::-1], top_geo.values[::-1], color=sb.AZUL_SURA.hex, alpha=0.9)
ax1.set_xlabel("N empresas")
ax1.set_title(f"ciudad_imp (desconocido={n_geo})")

parte_counts = sin["parte_cuerpo_imp"].value_counts()
top_parte = parte_counts.head(8)
ax2.barh(top_parte.index.astype(str)[::-1], top_parte.values[::-1], color=sb.AQUA_SURA.hex, alpha=0.9)
ax2.set_xlabel("N siniestros")
ax2.set_title(f"parte_cuerpo_imp (desconocido={n_parte})")

sb.add_sura_footer(fig, text="S01-1.4.3 | Imputación MCAR categórica")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_imputacion_mcar_categoricas.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 03_imputacion_mcar_categoricas.png")

# ── 5.5 Costo imputado por gravedad (chequeo MAR) ──
fig, ax = plt.subplots(figsize=(8, 4.5))
orden = ["leve", "grave", "mortal"]
plot_df = sin.loc[mask_costo].copy()
plot_df["gravedad"] = pd.Categorical(plot_df["gravedad"], categories=orden, ordered=True)
data_box = [np.log1p(plot_df.loc[plot_df["gravedad"] == g, "costo_asistencial_imp"]) for g in orden]
bp = ax.boxplot(
    data_box,
    tick_labels=orden,
    patch_artist=True,
)
colors = [sb.AQUA_SURA.hex, sb.AZUL_SURA.hex, "#001E60"]
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.7)
ax.set_ylabel("log1p(costo_asistencial_imp)")
ax.set_xlabel("gravedad")
ax.set_title(
    f"Valores imputados de costo_asistencial por gravedad\n"
    f"(n={int(mask_costo.sum())}; patrón MAR preservado)"
)
sb.add_sura_footer(fig, text="S01-1.4.3 | Costo imputado × gravedad")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_imputacion_costo_por_gravedad.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 03_imputacion_costo_por_gravedad.png")


print("\n" + "=" * 70)
print("  Ejecución completada.")
print("=" * 70)
print("\n  Resumen:")
for _, r in estrategia_df.iterrows():
    print(
        f"    {r['dataset']}.{r['variable']}: {r['estrategia']} "
        f"(n={r['n_imputados']}"
        + (f", R²={r['r2_modelo']}" if pd.notna(r["r2_modelo"]) else "")
        + ")"
    )
print("\n  Staging:")
print("    empresas_imputadas.parquet")
print("    siniestros_imputados.parquet")
print("    faltantes_imputacion_estrategia.parquet")
print("    faltantes_imputacion_diagnostico.parquet")
