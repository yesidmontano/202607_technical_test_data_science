"""
Traducción del ATT causal a valor económico
===========================================
Sección: S04 – Impacto e Inferencia Causal
Subsección: 4.3 – Efecto a valor económico
Proceso: 4.3.1 – Monetización del ATT de frecuencia

Descripción:
    Traduce el ATT de frecuencia estimado en 4.2.1 a siniestros evitados
    y COP evitados (valor económico bruto), propagando incertidumbre del
    ATT (IC95) y sensibilidad del costo medio por siniestro.

    Puente:
        ΔN_it = (−ATT / 100) × n_trabajadores_it     # ATT sobre frecuencia_x100
        Valor_it = ΔN_it × E[costo | siniestro]

    El valor es bruto (claims evitados); no hay costo del programa en COP
    en los datos → no se reporta ROI neto.

Inputs:
    - data/staging/S04/causal_resumen.parquet
    - data/staging/S04/causal_panel.parquet
    - data/staging/S04/causal_att_simple.parquet
    - data/staging/S01/siniestros_tratados.parquet

Outputs:
    - data/staging/S04/valor_economico_*.parquet
    - results/imgs/01_valor_*.png
    - results/efecto_economico.md (escrito aparte)

Uso:
    .venv/bin/python \\
      "sections/S04-Impacto_Inferencia_Causal/4_3_Efecto a valor economico/code/01-val_economico/01-val_economico.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
DATA_S01 = ROOT / "data" / "staging" / "S01"
DATA_S04 = ROOT / "data" / "staging" / "S04"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_S04.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S04-4.3.1 | ATT frecuencia → valor económico (COP evitados)")
print("=" * 70)


def save_parquet(df: pd.DataFrame, name: str) -> None:
    path = DATA_S04 / name
    df.to_parquet(path, index=False)
    print(f"  [staging] {path.relative_to(ROOT)}  ({df.shape[0]}×{df.shape[1]})")


def save_fig(fig: plt.Figure, name: str) -> None:
    path = IMGS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] {path.relative_to(ROOT)}")


def fmt_b(x: float) -> str:
    return f"{x / 1e9:.2f} B"


# ──────────────────────────────────────────────────
# 1. Carga
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando staging 4.2 / siniestros...")
resumen = pd.read_parquet(DATA_S04 / "causal_resumen.parquet").iloc[0]
panel = pd.read_parquet(DATA_S04 / "causal_panel.parquet")
att_simple = pd.read_parquet(DATA_S04 / "causal_att_simple.parquet")
sin = pd.read_parquet(DATA_S01 / "siniestros_tratados.parquet")

att = float(resumen["att_simple"])          # negativo = reducción
att_se = float(resumen["se_bootstrap"])
att_lo = float(resumen["ci95_low"])
att_hi = float(resumen["ci95_high"])
baseline = float(resumen["baseline_freq_pre_treated"])

print(f"  ATT={att:.4f}  SE={att_se:.4f}  IC95=[{att_lo:.4f}, {att_hi:.4f}]")

# ──────────────────────────────────────────────────
# 2. Costo unitario por siniestro (tratadas)
# ──────────────────────────────────────────────────
treated_ids = panel.loc[panel["g"] > 0, "id_empresa"].unique()
sin_t = sin.loc[sin["id_empresa"].isin(treated_ids)].copy()
cost_col = "costo_total_w" if "costo_total_w" in sin_t.columns else "costo_total"
unit_costs = {
    "p25": float(sin_t[cost_col].quantile(0.25)),
    "median": float(sin_t[cost_col].median()),
    "mean": float(sin_t[cost_col].mean()),
    "p75": float(sin_t[cost_col].quantile(0.75)),
}
print(
    f"  Costo/siniestro tratadas (n={len(sin_t):,}): "
    f"mean={unit_costs['mean']:,.0f}  median={unit_costs['median']:,.0f}"
)

# ──────────────────────────────────────────────────
# 3. Exposición post-tratamiento
# ──────────────────────────────────────────────────
post = panel.loc[(panel["g"] > 0) & (panel["post"] == 1)].copy()
post["n_trab_exp"] = post["n_trabajadores"].clip(lower=1).astype(float)

# Avoided claims (positive when ATT < 0).
# ATT IC: att_lo more negative → MORE savings; att_hi closer to 0 → LESS savings.
post["siniestros_evitados_point"] = (-att / 100.0) * post["n_trab_exp"]
post["siniestros_evitados_valor_hi"] = (-att_lo / 100.0) * post["n_trab_exp"]  # upper $
post["siniestros_evitados_valor_lo"] = (-att_hi / 100.0) * post["n_trab_exp"]  # lower $

post["valor_point_mean"] = post["siniestros_evitados_point"] * unit_costs["mean"]
post["valor_point_median"] = post["siniestros_evitados_point"] * unit_costs["median"]

# ──────────────────────────────────────────────────
# 4. Agregados empresa / año / escenarios
# ──────────────────────────────────────────────────
print("\n[CALC] Monetizando...")

empresa = (
    post.groupby(
        ["id_empresa", "g", "programa", "clase_riesgo", "sector", "segmento"],
        as_index=False,
    )
    .agg(
        n_anios_post=("anio", "nunique"),
        exposicion_trab_anio=("n_trab_exp", "sum"),
        siniestros_evitados=("siniestros_evitados_point", "sum"),
        valor_cop_mean=("valor_point_mean", "sum"),
        valor_cop_median=("valor_point_median", "sum"),
        costo_observado=("costo_total", "sum"),
    )
)
empresa["valor_cop_mean_anual"] = empresa["valor_cop_mean"] / empresa["n_anios_post"]
empresa["valor_cop_median_anual"] = empresa["valor_cop_median"] / empresa["n_anios_post"]

anual = (
    post.groupby("anio", as_index=False)
    .agg(
        n_empresas=("id_empresa", "nunique"),
        exposicion=("n_trab_exp", "sum"),
        siniestros_evitados_point=("siniestros_evitados_point", "sum"),
        siniestros_evitados_valor_lo=("siniestros_evitados_valor_lo", "sum"),
        siniestros_evitados_valor_hi=("siniestros_evitados_valor_hi", "sum"),
        costo_observado=("costo_total", "sum"),
    )
)
for ckey, cval in unit_costs.items():
    anual[f"valor_{ckey}_point"] = anual["siniestros_evitados_point"] * cval
    anual[f"valor_{ckey}_lo"] = anual["siniestros_evitados_valor_lo"] * cval
    anual[f"valor_{ckey}_hi"] = anual["siniestros_evitados_valor_hi"] * cval

# Escenarios: ATT × unit cost
rows_esc = []
for att_lab, a in [
    ("att_efecto_mayor", att_lo),   # more negative ATT → more savings
    ("point", att),
    ("att_efecto_menor", att_hi),   # closer to 0 → less savings
]:
    avoided = (-a / 100.0) * post["n_trab_exp"].sum()
    for c_lab, c in unit_costs.items():
        rows_esc.append(
            {
                "att_scenario": att_lab,
                "att": a,
                "cost_scenario": c_lab,
                "costo_por_siniestro": c,
                "siniestros_evitados_total": avoided,
                "valor_cop_total": avoided * c,
                "valor_cop_anual_pleno": (
                    (-a / 100.0)
                    * post.loc[post["anio"] >= 2022, "n_trab_exp"].sum()
                    / 3.0
                    * c
                ),
            }
        )
escenarios = pd.DataFrame(rows_esc)

# Run-rate pleno (2022–2024 average exposure of all treated)
exp_pleno_anual = float(post.loc[post["anio"] >= 2022, "n_trab_exp"].sum() / 3.0)
siniestros_evitados_total = float(post["siniestros_evitados_point"].sum())
valor_total_mean = float(post["valor_point_mean"].sum())
valor_total_median = float(post["valor_point_median"].sum())
valor_anual_pleno_mean = (-att / 100.0) * exp_pleno_anual * unit_costs["mean"]
valor_anual_pleno_median = (-att / 100.0) * exp_pleno_anual * unit_costs["median"]

# IC on value at mean unit cost (lo/hi in COP space)
valor_lo_mean = float(post["siniestros_evitados_valor_lo"].sum() * unit_costs["mean"])
valor_hi_mean = float(post["siniestros_evitados_valor_hi"].sum() * unit_costs["mean"])

# Robustez ATT → valor (mean cost)
rob_rows = []
for _, r in att_simple.loc[att_simple["yname"] == "frecuencia_x100"].iterrows():
    a = float(r["att"])
    avoided = (-a / 100.0) * post["n_trab_exp"].sum()
    rob_rows.append(
        {
            "spec": r["spec"],
            "att": a,
            "se": float(r["se"]),
            "siniestros_evitados_total": avoided,
            "valor_cop_mean": avoided * unit_costs["mean"],
            "valor_cop_median": avoided * unit_costs["median"],
            "valor_anual_pleno_mean": (-a / 100.0) * exp_pleno_anual * unit_costs["mean"],
        }
    )
robustez_val = pd.DataFrame(rob_rows)

# Inputs audit
inputs = pd.DataFrame(
    [
        {
            "att_simple": att,
            "att_se": att_se,
            "att_ci95_low": att_lo,
            "att_ci95_high": att_hi,
            "baseline_freq_pre": baseline,
            "att_pct_vs_baseline": float(resumen["att_pct_vs_baseline"]),
            "n_tratadas": int(resumen["n_tratadas"]),
            "n_firm_years_post": int(len(post)),
            "exposicion_trab_post_total": float(post["n_trab_exp"].sum()),
            "exposicion_trab_pleno_anual": exp_pleno_anual,
            "n_siniestros_unit_cost": int(len(sin_t)),
            "costo_p25": unit_costs["p25"],
            "costo_median": unit_costs["median"],
            "costo_mean": unit_costs["mean"],
            "costo_p75": unit_costs["p75"],
            "formula": "valor = (-ATT/100) * n_trabajadores * E[costo|siniestro]",
            "nota": (
                "Valor bruto de claims evitados; costo del programa no observado en COP. "
                "Severidad asumida constante (ATT costo/trab no significativo en 4.2)."
            ),
        }
    ]
)

# Supuestos / rupturas (para doc y staging)
supuestos = pd.DataFrame(
    [
        {
            "id": "S1",
            "supuesto": "Tendencias paralelas condicionales (CS)",
            "rol": "identificacion",
            "evidencia_a_favor": "Event-study pre-trends: 0/3 horizontes e<0 significativos",
            "como_se_rompe": "Shocks diferenciales no observados (cultura SST, selección) que cambien la trayectoria de tratadas vs controles",
            "impacto_en_valor": "Sesgo del ATT → sobre/subestima COP evitados en la misma proporción",
        },
        {
            "id": "S2",
            "supuesto": "No anticipación",
            "rol": "identificacion",
            "evidencia_a_favor": "ATT en e=-1 no significativo",
            "como_se_rompe": "Empresas cambian comportamiento antes de fecha_inicio",
            "impacto_en_valor": "Parte del efecto se atribuye mal al programa",
        },
        {
            "id": "S3",
            "supuesto": "SUTVA / no interferencia",
            "rol": "identificacion",
            "evidencia_a_favor": "Tratamiento a nivel empresa; sin spillover modelado",
            "como_se_rompe": "Difusión de prácticas entre empresas del mismo sector/ciudad",
            "impacto_en_valor": "Controles 'contaminados' → ATT atenuado → valor subestimado",
        },
        {
            "id": "S4",
            "supuesto": "Severidad/costo por siniestro constante (puente freq→COP)",
            "rol": "monetizacion",
            "evidencia_a_favor": "ATT sobre costo_por_trab no significativo (4.2); se usa E[costo] histórico",
            "como_se_rompe": "El programa cambia la composición de gravedad (más/menos siniestros caros)",
            "impacto_en_valor": "Valor en COP puede divergir del ATT de frecuencia; mean>>median por cola",
        },
        {
            "id": "S5",
            "supuesto": "ATT promedio aplicable a toda la exposición post",
            "rol": "monetizacion",
            "evidencia_a_favor": "ATT simple CS agregado; escala lineal en n_trabajadores",
            "como_se_rompe": "Heterogeneidad por cohorte (2022 débil) o decaimiento e≥4",
            "impacto_en_valor": "Extrapolación a años lejanos o cohorte 2022 puede sobreestimar",
        },
        {
            "id": "S6",
            "supuesto": "Valor bruto ≠ ROI neto",
            "rol": "interpretacion",
            "evidencia_a_favor": "No hay costo del programa en COP en raw/staging",
            "como_se_rompe": "Si el costo operativo del programa > claims evitados",
            "impacto_en_valor": "Conclusión de 'ahorro' puede volverse negativa en neto",
        },
    ]
)

credibilidad = pd.DataFrame(
    [
        {
            "conclusion": (
                "El programa reduce causalmente la frecuencia de siniestralidad "
                "de las tratadas (~−11.7% vs baseline pre); el valor económico "
                "reportado es la traducción lineal de ese ATT a COP vía E[costo|siniestro]."
            ),
            "nivel_causal_frecuencia": "moderado_alto",
            "nivel_causal_pesos": "moderado",
            "justificacion_frecuencia": (
                "CS DR + pre-trends OK + robustez COVID/NYT; adopción no aleatoria "
                "pero DiD bloquea confusores fijos y tendencias comunes."
            ),
            "justificacion_pesos": (
                "Monetización depende del puente de severidad constante; "
                "ATT directo de costo/trab no significativo → pesos son "
                "proyección actuarial del canal frecuencia, no un ATT en COP."
            ),
            "confianza_operativa": (
                "Usar IC95 del ATT y sensibilidad mean/median; no presentar "
                "el punto central como ROI neto del programa."
            ),
        }
    ]
)

resumen_val = pd.DataFrame(
    [
        {
            "att_frecuencia_x100": att,
            "att_pct_vs_baseline": float(resumen["att_pct_vs_baseline"]),
            "siniestros_evitados_total_post": siniestros_evitados_total,
            "siniestros_evitados_anual_pleno": (-att / 100.0) * exp_pleno_anual,
            "valor_total_mean_cop": valor_total_mean,
            "valor_total_median_cop": valor_total_median,
            "valor_total_mean_lo_cop": valor_lo_mean,
            "valor_total_mean_hi_cop": valor_hi_mean,
            "valor_anual_pleno_mean_cop": valor_anual_pleno_mean,
            "valor_anual_pleno_median_cop": valor_anual_pleno_median,
            "valor_anual_pleno_mean_lo_cop": (
                (-att_hi / 100.0) * exp_pleno_anual * unit_costs["mean"]
            ),
            "valor_anual_pleno_mean_hi_cop": (
                (-att_lo / 100.0) * exp_pleno_anual * unit_costs["mean"]
            ),
            "costo_medio_siniestro": unit_costs["mean"],
            "costo_mediano_siniestro": unit_costs["median"],
            "n_tratadas": int(resumen["n_tratadas"]),
            "n_firm_years_post": int(len(post)),
            "ventana_post": "2019-2024 (adopción escalonada)",
            "nivel_causal_frecuencia": "moderado_alto",
            "nivel_causal_pesos": "moderado",
            "es_roi_neto": 0,
            "random_seed": RANDOM_SEED,
        }
    ]
)

print(
    f"  Siniestros evitados (total post): {siniestros_evitados_total:,.1f}\n"
    f"  Valor total @ mean:   {fmt_b(valor_total_mean)} COP  "
    f"banda ATT → [{fmt_b(valor_lo_mean)}, {fmt_b(valor_hi_mean)}]\n"
    f"  Valor total @ median: {fmt_b(valor_total_median)} COP\n"
    f"  Run-rate anual pleno @ mean: {fmt_b(valor_anual_pleno_mean)} COP/año"
)

# ──────────────────────────────────────────────────
# 5. Staging + CSV
# ──────────────────────────────────────────────────
print("\n[STAGING] Persistiendo...")
save_parquet(inputs, "valor_economico_inputs.parquet")
save_parquet(empresa, "valor_economico_empresa.parquet")
save_parquet(anual, "valor_economico_anual.parquet")
save_parquet(escenarios, "valor_economico_escenarios.parquet")
save_parquet(robustez_val, "valor_economico_robustez.parquet")
save_parquet(supuestos, "valor_economico_supuestos.parquet")
save_parquet(credibilidad, "valor_economico_credibilidad.parquet")
save_parquet(resumen_val, "valor_economico_resumen.parquet")

for name, frame in [
    ("valor_economico_anual.csv", anual),
    ("valor_economico_escenarios.csv", escenarios),
    ("valor_economico_robustez.csv", robustez_val),
    ("valor_economico_resumen.csv", resumen_val),
]:
    frame.to_csv(RESULTS_DIR / name, index=False)

# ──────────────────────────────────────────────────
# 6. Figuras
# ──────────────────────────────────────────────────
print("\n[FIGS] Generando visualizaciones sura_brand...")

# 6.1 Valor anual (mean) con banda IC ATT
fig, ax = plt.subplots(figsize=(9, 5))
ax.fill_between(
    anual["anio"],
    anual["valor_mean_lo"] / 1e9,
    anual["valor_mean_hi"] / 1e9,
    color=sb.AQUA_SURA.hex,
    alpha=0.25,
    label="Banda ATT IC95 (costo medio)",
)
ax.plot(
    anual["anio"],
    anual["valor_mean_point"] / 1e9,
    color=sb.AZUL_SURA.hex,
    marker="o",
    lw=2,
    label="Punto (ATT × costo medio)",
)
ax.plot(
    anual["anio"],
    anual["valor_median_point"] / 1e9,
    color=sb.AZUL_PROFUNDO.hex,
    marker="s",
    ls="--",
    lw=1.5,
    label="Punto (ATT × costo mediano)",
)
ax.set_xlabel("Año")
ax.set_ylabel("COP evitados (miles de millones)")
ax.set_title("Valor económico bruto anual del programa (claims evitados)")
ax.legend(frameon=False, fontsize=8)
sb.add_sura_footer(fig, text="S04-4.3 | Puente: (−ATT/100)×exposición×E[costo]")
save_fig(fig, "01_valor_anual.png")

# 6.2 Tornado / escenarios ATT × costo
pivot = escenarios.pivot(
    index="cost_scenario", columns="att_scenario", values="valor_cop_total"
)
order = ["p25", "median", "mean", "p75"]
pivot = pivot.reindex(order)
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(order))
w = 0.25
ax.bar(
    x - w,
    pivot["att_efecto_menor"] / 1e9,
    width=w,
    color=sb.GRIS_MEDIO.hex,
    label="ATT efecto menor (IC)",
)
ax.bar(x, pivot["point"] / 1e9, width=w, color=sb.AZUL_SURA.hex, label="ATT punto")
ax.bar(
    x + w,
    pivot["att_efecto_mayor"] / 1e9,
    width=w,
    color=sb.AQUA_SURA.hex,
    label="ATT efecto mayor (IC)",
)
ax.set_xticks(x)
ax.set_xticklabels(["P25", "Mediana", "Media", "P75"])
ax.set_ylabel("Valor total post (B COP)")
ax.set_xlabel("Escenario de costo por siniestro")
ax.set_title("Sensibilidad: ATT (IC95) × costo unitario")
ax.legend(frameon=False, fontsize=8)
sb.add_sura_footer(fig, text="S04-4.3 | Acumulado firm-years post 2019–2024")
save_fig(fig, "01_valor_sensibilidad.png")

# 6.3 Distribución valor por empresa (mean)
fig, ax = plt.subplots(figsize=(8, 4.5))
vals = empresa["valor_cop_mean"] / 1e6  # millones
ax.hist(vals, bins=40, color=sb.AZUL_SURA.hex, alpha=0.85, edgecolor="white")
ax.axvline(vals.median(), color=sb.AMARILLO_SURA.hex, lw=2, label=f"Mediana={vals.median():.1f} M")
ax.axvline(vals.mean(), color=sb.AQUA_SURA.hex, lw=2, ls="--", label=f"Media={vals.mean():.1f} M")
ax.set_xlabel("Valor bruto por empresa (millones COP, acumulado post)")
ax.set_ylabel("Número de empresas")
ax.set_title("Distribución del valor atribuido por empresa tratada")
ax.legend(frameon=False)
sb.add_sura_footer(fig, text="S04-4.3 | Escala por exposición; ATT homogéneo")
save_fig(fig, "01_valor_empresa_hist.png")

# 6.4 Robustez ATT → valor anual pleno
fig, ax = plt.subplots(figsize=(8, 4.5))
lab_map = {
    "principal_never_treated": "Principal",
    "excluir_anio_2020": "Excluir 2020",
    "not_yet_treated": "Not-yet treated",
}
rob_plot = robustez_val.copy()
rob_plot["label"] = rob_plot["spec"].map(lab_map)
ax.bar(
    rob_plot["label"],
    rob_plot["valor_anual_pleno_mean"] / 1e9,
    color=sb.AZUL_SURA.hex,
    alpha=0.9,
)
ax.set_ylabel("B COP / año (run-rate pleno)")
ax.set_title("Robustez del valor anual (ATT freq × costo medio)")
for i, v in enumerate(rob_plot["valor_anual_pleno_mean"] / 1e9):
    ax.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=sb.AZUL_PROFUNDO.hex)
sb.add_sura_footer(fig, text="S04-4.3 | Exposición plena ≈ media 2022–2024")
save_fig(fig, "01_valor_robustez.png")

# 6.5 Cascada: exposición → siniestros → COP
fig, ax = plt.subplots(figsize=(8, 4.5))
steps = [
    "Exposición post\n(trab·año)",
    "× (−ATT/100)",
    "Siniestros\nevitados",
    "× E[costo]",
    "Valor bruto\n(B COP)",
]
# Visual cascade with key numbers as text annotations on bars of relative stages
cascade_vals = [
    post["n_trab_exp"].sum() / 1e5,  # scale for viz
    (-att),
    siniestros_evitados_total / 100,
    unit_costs["mean"] / 1e6,
    valor_total_mean / 1e9,
]
cascade_labels = [
    f"{post['n_trab_exp'].sum():,.0f}",
    f"{-att:.3f}",
    f"{siniestros_evitados_total:,.0f}",
    f"{unit_costs['mean']/1e6:.2f} M",
    f"{valor_total_mean/1e9:.2f} B",
]
colors = [sb.GRIS_MEDIO.hex, sb.AQUA_SURA.hex, sb.AZUL_SURA.hex, sb.AQUA_ALTERNO.hex, sb.AZUL_PROFUNDO.hex]
ax.bar(steps, cascade_vals, color=colors, alpha=0.9)
for i, (lab, val) in enumerate(zip(cascade_labels, cascade_vals)):
    ax.text(i, val * 1.02, lab, ha="center", va="bottom", fontsize=8, color=sb.AZUL_PROFUNDO.hex)
ax.set_ylabel("Escala ilustrativa (unidades distintas por barra)")
ax.set_title("Puente frecuencia → valor: pasos de la traducción")
ax.tick_params(axis="x", labelsize=8)
sb.add_sura_footer(fig, text="S04-4.3 | Barras no comparables entre sí — solo lectura del puente")
save_fig(fig, "01_valor_puente.png")

print("\n" + "=" * 70)
print("  RESUMEN VALOR ECONÓMICO")
print("=" * 70)
print(resumen_val.T.to_string(header=False))
print("\n[OK] Monetización 4.3.1 completada.")
