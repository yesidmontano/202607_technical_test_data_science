"""
Proyección del resultado técnico del portafolio
===============================================
Sección: S03 – Reto de Negocio
Subsección: 3.3 – Proyección de portafolio
Proceso: 3.3.1 – Siniestralidad vs primas, combined ratio e incertidumbre

Descripción:
    A partir de las predicciones de 3.2.1 (`modelo_pred_empresa`, horizonte
    `proximo_anio`), proyecta el resultado técnico del próximo año:

      · Siniestralidad esperada E[Costo] vs primas devengadas (proxy: prima_anual)
      · Loss ratio y Combined ratio = LR + Expense Ratio
      · Escenario base (punto del modelo) y adverso (shock YoY histórico máx.)
      · Incertidumbre: bootstrap de residuos holdout 2024 + volatilidad YoY
        histórica del costo agregado (IC 80% / 95%)

    Expense ratio: supuesto operativo documentado (no hay gastos en raw).
    Sensibilidad ±5 pp reportada en staging.

Inputs (reutilizados):
    - data/staging/S03/modelo_pred_empresa.parquet
    - data/staging/S03/modelo_pred_clase.parquet
    - data/staging/S03/modelo_resumen.parquet
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S03/supuestos_mix_estabilidad.parquet  (trazabilidad S2)

Outputs:
    - results/imgs/01_proyeccion_*.png
    - results/proyeccion_*.csv
    - data/staging/S03/proyeccion_*.parquet
    - results/proyeccion_portafolio.md

Uso:
    .venv/bin/python "sections/S03-Reto_de_Negocio/3_3_Proyeccion de portafolio/code/01-proyeccion/01-proyeccion.py"
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
rng = np.random.default_rng(RANDOM_SEED)

# Gasto operativo / adquisición como % de prima (supuesto documentado)
EXPENSE_RATIO_BASE = 0.25
EXPENSE_RATIO_LO = 0.20
EXPENSE_RATIO_HI = 0.30

N_BOOT = 5_000
ANIO_PROYECCION = 2025  # features 2024 → próximo año

ROOT = Path(__file__).resolve().parents[5]
DATA_S01 = ROOT / "data" / "staging" / "S01"
DATA_S03 = ROOT / "data" / "staging" / "S03"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_S03.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S03-3.3.1 | Proyección resultado técnico del portafolio")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando predicciones 3.2.1 y series históricas...")
pred = pd.read_parquet(DATA_S03 / "modelo_pred_empresa.parquet")
pred_clase = pd.read_parquet(DATA_S03 / "modelo_pred_clase.parquet")
resumen_mod = pd.read_parquet(DATA_S03 / "modelo_resumen.parquet")
panel = pd.read_parquet(DATA_S01 / "temporal_empresa_anio.parquet")
estab = pd.read_parquet(DATA_S03 / "supuestos_mix_estabilidad.parquet")

fwd = pred.loc[pred["horizonte"] == "proximo_anio"].copy()
hold = pred.loc[pred["horizonte"] == "holdout_2024"].copy()
fwd = fwd.loc[fwd["prima_anual"] > 0].copy()

print(f"  Empresas proyección: {len(fwd):,}")
print(f"  Holdout residuos:    {len(hold):,}")

# ──────────────────────────────────────────────────
# 2. Escenario base
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  ESCENARIO BASE")
print("=" * 70)

prima_total = float(fwd["prima_anual"].sum())
costo_base = float(fwd["costo_pred"].sum())
freq_base = float(fwd["freq_pred"].sum())
lr_base = costo_base / prima_total
cr_base = lr_base + EXPENSE_RATIO_BASE
resultado_base = prima_total - costo_base - EXPENSE_RATIO_BASE * prima_total
# = prima * (1 - CR)

print(f"  Primas devengadas (proxy):     {prima_total/1e9:.2f} B COP")
print(f"  Siniestralidad esperada:       {costo_base/1e9:.2f} B COP")
print(f"  E[N] agregado:                 {freq_base:,.0f}")
print(f"  Loss ratio:                    {lr_base:.1%}")
print(f"  Expense ratio (supuesto):      {EXPENSE_RATIO_BASE:.1%}")
print(f"  Combined ratio:                {cr_base:.1%}")
print(f"  Resultado técnico (aprox.):    {resultado_base/1e9:.2f} B COP")

# Por clase
clase_fwd = pred_clase.loc[pred_clase["horizonte"] == "proximo_anio"].copy()
clase_fwd["expense"] = EXPENSE_RATIO_BASE * clase_fwd["prima_suma"]
clase_fwd["combined_ratio"] = (
    clase_fwd["costo_pred_suma"] / clase_fwd["prima_suma"] + EXPENSE_RATIO_BASE
)
clase_fwd["resultado_tecnico"] = (
    clase_fwd["prima_suma"] - clase_fwd["costo_pred_suma"] - clase_fwd["expense"]
)
clase_fwd["escenario"] = "base"

# ──────────────────────────────────────────────────
# 3. Volatilidad histórica y escenario adverso
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  ESCENARIO ADVERSO + VOLATILIDAD HISTÓRICA")
print("=" * 70)

# Costo agregado histórico (misma prima estática por empresa → LR histórico)
ann = (
    panel.groupby("anio", as_index=False)
    .agg(costo_total=("costo_total", "sum"), n_siniestros=("n_siniestros", "sum"))
)
ann["prima_proxy"] = prima_total  # portafolio de empresas fijo
ann["loss_ratio"] = ann["costo_total"] / ann["prima_proxy"]
ann["yoy_costo_pct"] = ann["costo_total"].pct_change()

yoy = ann["yoy_costo_pct"].dropna()
shock_adverso = float(yoy.max())          # peor alza interanual observada
shock_p90 = float(yoy.quantile(0.90)) if len(yoy) >= 4 else shock_adverso
vol_yoy = float(yoy.std(ddof=1))

print(f"  YoY costo histórico: {yoy.round(3).tolist()}")
print(f"  Shock adverso (máx YoY): {shock_adverso:.1%}")
print(f"  σ YoY:                   {vol_yoy:.1%}")

# Adverso: estrés de siniestralidad por shock histórico máximo
# + sobrecosto leve de gastos (+2 pp) por presión operativa en mala racha
EXPENSE_RATIO_ADVERSO = EXPENSE_RATIO_BASE + 0.02
costo_adverso = costo_base * (1.0 + shock_adverso)
lr_adverso = costo_adverso / prima_total
cr_adverso = lr_adverso + EXPENSE_RATIO_ADVERSO
resultado_adverso = prima_total - costo_adverso - EXPENSE_RATIO_ADVERSO * prima_total

print(f"  Siniestralidad adversa:        {costo_adverso/1e9:.2f} B COP")
print(f"  Loss ratio adverso:            {lr_adverso:.1%}")
print(f"  Combined ratio adverso:        {cr_adverso:.1%}")
print(f"  Resultado técnico adverso:     {resultado_adverso/1e9:.2f} B COP")

# Adverso por clase: mismo factor de shock (uniforme) — conservador y trazable
clase_adv = clase_fwd.copy()
clase_adv["costo_pred_suma"] = clase_adv["costo_pred_suma"] * (1.0 + shock_adverso)
clase_adv["expense"] = EXPENSE_RATIO_ADVERSO * clase_adv["prima_suma"]
clase_adv["loss_ratio_pred"] = clase_adv["costo_pred_suma"] / clase_adv["prima_suma"]
clase_adv["combined_ratio"] = clase_adv["loss_ratio_pred"] + EXPENSE_RATIO_ADVERSO
clase_adv["resultado_tecnico"] = (
    clase_adv["prima_suma"] - clase_adv["costo_pred_suma"] - clase_adv["expense"]
)
clase_adv["escenario"] = "adverso"
clase_adv["freq_pred_suma"] = clase_adv["freq_pred_suma"]  # freq no reescalada explícitamente
clase_adv["share_costo_pred_pct"] = (
    100 * clase_adv["costo_pred_suma"] / clase_adv["costo_pred_suma"].sum()
).round(2)

# ──────────────────────────────────────────────────
# 4. Incertidumbre (bootstrap residuos + proceso YoY)
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  INCERTIDUMBRE")
print("=" * 70)

resid = (hold["costo_total"] - hold["costo_pred"]).astype(float).values

# A) Bootstrap de residuos del holdout → incertidumbre de modelo
boot_cost_model = np.empty(N_BOOT)
for b in range(N_BOOT):
    draw = rng.choice(resid, size=len(fwd), replace=True)
    boot_cost_model[b] = costo_base + draw.sum()

# B) Proceso: shocks YoY ~ N(0, σ_hist) truncados (simulación paramétrica)
#    anclados a la media del modelo
shocks_proc = rng.normal(loc=0.0, scale=vol_yoy, size=N_BOOT)
boot_cost_process = costo_base * (1.0 + shocks_proc)

# C) Combinada (aprox. independiente): modelo + proceso en log-espacio suave
boot_cost_comb = boot_cost_model * (1.0 + shocks_proc)

def _pcts(arr: np.ndarray) -> dict:
    q = np.percentile(arr, [5, 10, 50, 90, 95])
    return {
        "p05": float(q[0]),
        "p10": float(q[1]),
        "p50": float(q[2]),
        "p90": float(q[3]),
        "p95": float(q[4]),
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)),
    }


stats_model = _pcts(boot_cost_model)
stats_proc = _pcts(boot_cost_process)
stats_comb = _pcts(boot_cost_comb)

print(f"  Modelo  IC90 [{stats_model['p05']/1e9:.2f}, {stats_model['p95']/1e9:.2f}] B")
print(f"  Proceso IC90 [{stats_proc['p05']/1e9:.2f}, {stats_proc['p95']/1e9:.2f}] B")
print(f"  Combin. IC90 [{stats_comb['p05']/1e9:.2f}, {stats_comb['p95']/1e9:.2f}] B")

# Distribuciones de LR y CR (combinada)
boot_lr = boot_cost_comb / prima_total
boot_cr = boot_lr + EXPENSE_RATIO_BASE
stats_lr = _pcts(boot_lr)
stats_cr = _pcts(boot_cr)

print(f"  LR  IC90 [{stats_lr['p05']:.1%}, {stats_lr['p95']:.1%}]  "
      f"mediana {stats_lr['p50']:.1%}")
print(f"  CR  IC90 [{stats_cr['p05']:.1%}, {stats_cr['p95']:.1%}]  "
      f"mediana {stats_cr['p50']:.1%}")
print(f"  P(CR>1) = {(boot_cr > 1.0).mean():.1%}")

# ──────────────────────────────────────────────────
# 5. Tablas de escenarios y sensibilidad ER
# ──────────────────────────────────────────────────
escenarios = pd.DataFrame([
    {
        "escenario": "base",
        "anio_proyeccion": ANIO_PROYECCION,
        "primas_devengadas": prima_total,
        "siniestralidad_esperada": costo_base,
        "n_siniestros_esperados": freq_base,
        "loss_ratio": lr_base,
        "expense_ratio": EXPENSE_RATIO_BASE,
        "combined_ratio": cr_base,
        "resultado_tecnico": resultado_base,
        "shock_siniestralidad": 0.0,
        "descripcion": (
            "Punto del modelo 3.2.1 (pure premium) + ER operativo 25%"
        ),
    },
    {
        "escenario": "adverso",
        "anio_proyeccion": ANIO_PROYECCION,
        "primas_devengadas": prima_total,
        "siniestralidad_esperada": costo_adverso,
        "n_siniestros_esperados": freq_base,  # shock vía severidad/agregado
        "loss_ratio": lr_adverso,
        "expense_ratio": EXPENSE_RATIO_ADVERSO,
        "combined_ratio": cr_adverso,
        "resultado_tecnico": resultado_adverso,
        "shock_siniestralidad": shock_adverso,
        "descripcion": (
            f"Siniestralidad ×(1+máx YoY histórico={shock_adverso:.1%}); "
            f"ER={EXPENSE_RATIO_ADVERSO:.0%}"
        ),
    },
])

# Sensibilidad expense ratio (base siniestralidad fija)
sens_er = pd.DataFrame([
    {
        "expense_ratio": er,
        "loss_ratio": lr_base,
        "combined_ratio": lr_base + er,
        "resultado_tecnico": prima_total * (1 - lr_base - er),
        "escenario_siniestralidad": "base",
    }
    for er in [EXPENSE_RATIO_LO, EXPENSE_RATIO_BASE, EXPENSE_RATIO_HI]
] + [
    {
        "expense_ratio": er,
        "loss_ratio": lr_adverso,
        "combined_ratio": lr_adverso + er,
        "resultado_tecnico": prima_total * (1 - lr_adverso - er),
        "escenario_siniestralidad": "adverso",
    }
    for er in [EXPENSE_RATIO_LO, EXPENSE_RATIO_BASE, EXPENSE_RATIO_HI]
])

# Empresa-nivel con escenarios
emp_base = fwd[[
    "id_empresa", "clase_riesgo", "sector", "segmento",
    "prima_anual", "freq_pred", "sev_pred", "costo_pred", "loss_ratio_pred",
    "insuficiente_pred",
]].copy()
emp_base["escenario"] = "base"
emp_base["expense"] = EXPENSE_RATIO_BASE * emp_base["prima_anual"]
emp_base["combined_ratio"] = emp_base["loss_ratio_pred"] + EXPENSE_RATIO_BASE
emp_base["resultado_tecnico"] = (
    emp_base["prima_anual"] - emp_base["costo_pred"] - emp_base["expense"]
)

emp_adv = emp_base.copy()
emp_adv["escenario"] = "adverso"
emp_adv["costo_pred"] = emp_adv["costo_pred"] * (1.0 + shock_adverso)
emp_adv["sev_pred"] = emp_adv["sev_pred"] * (1.0 + shock_adverso)
emp_adv["loss_ratio_pred"] = emp_adv["costo_pred"] / emp_adv["prima_anual"]
emp_adv["expense"] = EXPENSE_RATIO_ADVERSO * emp_adv["prima_anual"]
emp_adv["combined_ratio"] = emp_adv["loss_ratio_pred"] + EXPENSE_RATIO_ADVERSO
emp_adv["resultado_tecnico"] = (
    emp_adv["prima_anual"] - emp_adv["costo_pred"] - emp_adv["expense"]
)
emp_adv["insuficiente_pred"] = (emp_adv["loss_ratio_pred"] > 1.0).astype(int)

proy_empresa = pd.concat([emp_base, emp_adv], ignore_index=True)
proy_clase = pd.concat([clase_fwd, clase_adv], ignore_index=True)

# Incertidumbre staging
incertidumbre = pd.DataFrame([
    {
        "fuente": "modelo_bootstrap_residuos",
        "n_boot": N_BOOT,
        "metrica": "siniestralidad",
        **{k: stats_model[k] for k in ("p05", "p10", "p50", "p90", "p95", "mean", "std")},
    },
    {
        "fuente": "proceso_yoy_historico",
        "n_boot": N_BOOT,
        "metrica": "siniestralidad",
        **{k: stats_proc[k] for k in ("p05", "p10", "p50", "p90", "p95", "mean", "std")},
    },
    {
        "fuente": "combinada_modelo_proceso",
        "n_boot": N_BOOT,
        "metrica": "siniestralidad",
        **{k: stats_comb[k] for k in ("p05", "p10", "p50", "p90", "p95", "mean", "std")},
    },
    {
        "fuente": "combinada_modelo_proceso",
        "n_boot": N_BOOT,
        "metrica": "loss_ratio",
        **{k: stats_lr[k] for k in ("p05", "p10", "p50", "p90", "p95", "mean", "std")},
    },
    {
        "fuente": "combinada_modelo_proceso",
        "n_boot": N_BOOT,
        "metrica": "combined_ratio",
        **{k: stats_cr[k] for k in ("p05", "p10", "p50", "p90", "p95", "mean", "std")},
    },
])

# Serie histórica para gráficos / staging
hist_out = ann.copy()
hist_out["combined_ratio_er25"] = hist_out["loss_ratio"] + EXPENSE_RATIO_BASE

resumen = pd.DataFrame([{
    "anio_proyeccion": ANIO_PROYECCION,
    "n_empresas": len(fwd),
    "primas_devengadas": prima_total,
    "siniestralidad_base": costo_base,
    "siniestralidad_adversa": costo_adverso,
    "loss_ratio_base": lr_base,
    "loss_ratio_adverso": lr_adverso,
    "expense_ratio_base": EXPENSE_RATIO_BASE,
    "expense_ratio_adverso": EXPENSE_RATIO_ADVERSO,
    "combined_ratio_base": cr_base,
    "combined_ratio_adverso": cr_adverso,
    "resultado_tecnico_base": resultado_base,
    "resultado_tecnico_adverso": resultado_adverso,
    "shock_adverso_yoy": shock_adverso,
    "sigma_yoy_historico": vol_yoy,
    "siniestralidad_ic90_lo": stats_comb["p05"],
    "siniestralidad_ic90_hi": stats_comb["p95"],
    "combined_ratio_ic90_lo": stats_cr["p05"],
    "combined_ratio_ic90_hi": stats_cr["p95"],
    "prob_cr_gt_1": float((boot_cr > 1.0).mean()),
    "prob_cr_adverso_gt_1": float(cr_adverso > 1.0),
    "js_sector_costo_yoy": float(
        estab.query("dimension == 'sector' and metrica == 'costo_total'")[
            "js_yoy_media"
        ].iloc[0]
    ),
    "n_boot": N_BOOT,
    "fuente_modelo": "modelo_pred_empresa / horizonte=proximo_anio",
}])

# ──────────────────────────────────────────────────
# 6. Figuras
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  FIGURAS")
print("=" * 70)

# 6.1 Agua / barras: primas vs siniestros vs gastos (base vs adverso)
fig, axes = sb.create_dashboard(
    1, 2,
    title="Resultado técnico del portafolio – próximo año",
    subtitle=(
        f"Base CR={cr_base:.1%} · Adverso CR={cr_adverso:.1%} "
        f"(shock YoY={shock_adverso:.1%}) · ER base={EXPENSE_RATIO_BASE:.0%}"
    ),
)
for ax, esc, costo, er, titulo in [
    (axes[0], "base", costo_base, EXPENSE_RATIO_BASE, "Escenario base"),
    (axes[1], "adverso", costo_adverso, EXPENSE_RATIO_ADVERSO, "Escenario adverso"),
]:
    gasto = er * prima_total
    resultado = prima_total - costo - gasto
    vals = [prima_total / 1e9, costo / 1e9, gasto / 1e9, resultado / 1e9]
    labels = ["Primas", "Siniestros", "Gastos", "Resultado"]
    colors = [sb.AZUL_SURA.hex, "#C62828", sb.AQUA_SURA.hex,
              "#2E7D32" if resultado >= 0 else "#C62828"]
    bars = ax.bar(labels, vals, color=colors)
    ax.axhline(0, color="#666", lw=0.8)
    ax.set_ylabel("B COP")
    ax.set_title(titulo)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.15 if v >= 0 else -0.35),
                f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
sb.add_sura_footer(fig, text="S03-3.3.1 | Resultado técnico base vs adverso")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_proyeccion_resultado_tecnico.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_proyeccion_resultado_tecnico.png")

# 6.2 Combined ratio base vs adverso + umbral 100%
fig, ax = plt.subplots(figsize=(7.5, 4.5))
x = np.arange(2)
crs = [cr_base, cr_adverso]
lrs = [lr_base, lr_adverso]
ers = [EXPENSE_RATIO_BASE, EXPENSE_RATIO_ADVERSO]
ax.bar(x, lrs, 0.55, label="Loss ratio", color=sb.AZUL_SURA.hex)
ax.bar(x, ers, 0.55, bottom=lrs, label="Expense ratio", color=sb.AQUA_SURA.hex)
ax.axhline(1.0, color="#C62828", ls="--", lw=1.4, label="CR = 100%")
ax.set_xticks(x)
ax.set_xticklabels(["Base", "Adverso"])
ax.set_ylabel("Combined ratio")
ax.set_ylim(0, max(1.15, max(crs) * 1.1))
ax.set_title("Combined ratio – descomposición LR + ER")
for i, cr in enumerate(crs):
    ax.text(i, cr + 0.02, f"{cr:.1%}", ha="center", fontsize=10, fontweight="bold")
ax.legend(fontsize=8, loc="upper left")
sb.add_sura_footer(fig, text="S03-3.3.1 | Combined ratio")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_proyeccion_combined_ratio.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_proyeccion_combined_ratio.png")

# 6.3 CR por clase (base)
fig, ax = plt.subplots(figsize=(8, 4.5))
cf = clase_fwd.sort_values("clase_riesgo")
cols = ["#C62828" if v >= 1 else sb.AZUL_SURA.hex for v in cf["combined_ratio"]]
ax.bar(cf["clase_riesgo"].astype(str), cf["combined_ratio"], color=cols)
ax.axhline(1.0, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.3, label="CR = 100%")
ax.axhline(cr_base, color=sb.AQUA_SURA.hex, ls=":", lw=1.3, label=f"CR portafolio={cr_base:.1%}")
ax.set_xlabel("Clase de riesgo")
ax.set_ylabel("Combined ratio (base)")
ax.set_title("Combined ratio por clase de riesgo – escenario base")
ax.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.3.1 | CR por clase")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_proyeccion_cr_por_clase.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_proyeccion_cr_por_clase.png")

# 6.4 Distribución bootstrap siniestralidad
fig, axes = sb.create_dashboard(
    1, 2,
    title="Incertidumbre de la siniestralidad proyectada",
    subtitle=(
        f"IC90 combinada [{stats_comb['p05']/1e9:.2f}, {stats_comb['p95']/1e9:.2f}] B · "
        f"P(CR>1)={(boot_cr > 1).mean():.1%}"
    ),
)
ax1, ax2 = axes[0], axes[1]
ax1.hist(boot_cost_comb / 1e9, bins=40, color=sb.AZUL_SURA.hex, alpha=0.85)
ax1.axvline(costo_base / 1e9, color=sb.AQUA_SURA.hex, ls="--", lw=1.4, label="Base")
ax1.axvline(costo_adverso / 1e9, color="#C62828", ls="--", lw=1.4, label="Adverso")
ax1.axvline(stats_comb["p05"] / 1e9, color=sb.AMARILLO_SURA.hex, ls=":", lw=1.2, label="P5/P95")
ax1.axvline(stats_comb["p95"] / 1e9, color=sb.AMARILLO_SURA.hex, ls=":", lw=1.2)
ax1.set_xlabel("Siniestralidad (B COP)")
ax1.set_ylabel("Frecuencia bootstrap")
ax1.set_title("Distribución combinada (modelo + proceso)")
ax1.legend(fontsize=7)

ax2.hist(boot_cr, bins=40, color=sb.AZUL_SURA.hex, alpha=0.85)
ax2.axvline(cr_base, color=sb.AQUA_SURA.hex, ls="--", lw=1.4, label="CR base")
ax2.axvline(1.0, color="#C62828", ls="--", lw=1.4, label="CR=100%")
ax2.axvline(stats_cr["p05"], color=sb.AMARILLO_SURA.hex, ls=":", lw=1.2)
ax2.axvline(stats_cr["p95"], color=sb.AMARILLO_SURA.hex, ls=":", lw=1.2, label="IC90")
ax2.set_xlabel("Combined ratio")
ax2.set_ylabel("Frecuencia bootstrap")
ax2.set_title("Distribución del combined ratio")
ax2.legend(fontsize=7)
sb.add_sura_footer(fig, text="S03-3.3.1 | Bootstrap incertidumbre")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_proyeccion_incertidumbre.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_proyeccion_incertidumbre.png")

# 6.5 Serie histórica LR vs proyección
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(hist_out["anio"], hist_out["loss_ratio"], "o-", color=sb.AZUL_SURA.hex,
        lw=1.8, label="LR histórico")
ax.axhline(lr_base, color=sb.AQUA_SURA.hex, ls="--", lw=1.4, label=f"LR base {ANIO_PROYECCION}={lr_base:.1%}")
ax.axhline(lr_adverso, color="#C62828", ls="--", lw=1.4, label=f"LR adverso={lr_adverso:.1%}")
ax.fill_between(
    [ANIO_PROYECCION - 0.3, ANIO_PROYECCION + 0.3],
    stats_lr["p05"], stats_lr["p95"],
    color=sb.AQUA_SURA.hex, alpha=0.25, label="IC90 LR proyectado",
)
ax.scatter([ANIO_PROYECCION], [lr_base], s=80, color=sb.AQUA_SURA.hex, zorder=5)
ax.set_xlabel("Año")
ax.set_ylabel("Loss ratio")
ax.set_title("Loss ratio histórico y proyección próximo año")
ax.legend(fontsize=8, loc="upper right")
sb.add_sura_footer(fig, text="S03-3.3.1 | LR histórico vs proyección")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_proyeccion_lr_historico.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_proyeccion_lr_historico.png")

# 6.6 Tornado / sensibilidad ER
fig, ax = plt.subplots(figsize=(8, 4.5))
sens_b = sens_er.query("escenario_siniestralidad == 'base'")
sens_a = sens_er.query("escenario_siniestralidad == 'adverso'")
ax.plot(sens_b["expense_ratio"], sens_b["combined_ratio"], "o-",
        color=sb.AZUL_SURA.hex, label="Base")
ax.plot(sens_a["expense_ratio"], sens_a["combined_ratio"], "s-",
        color="#C62828", label="Adverso")
ax.axhline(1.0, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.2)
ax.set_xlabel("Expense ratio")
ax.set_ylabel("Combined ratio")
ax.set_title("Sensibilidad del CR al expense ratio (±5 pp)")
ax.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.3.1 | Sensibilidad ER")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_proyeccion_sensibilidad_er.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_proyeccion_sensibilidad_er.png")

# ──────────────────────────────────────────────────
# 7. Persistencia
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  PERSISTENCIA")
print("=" * 70)

# Muestra de trayectorias bootstrap (para reuso / auditoría)
boot_sample = pd.DataFrame({
    "draw": np.arange(N_BOOT),
    "siniestralidad_modelo": boot_cost_model,
    "siniestralidad_proceso": boot_cost_process,
    "siniestralidad_combinada": boot_cost_comb,
    "loss_ratio": boot_lr,
    "combined_ratio": boot_cr,
})

staging = {
    "proyeccion_escenarios.parquet": escenarios,
    "proyeccion_empresa.parquet": proy_empresa,
    "proyeccion_clase.parquet": proy_clase,
    "proyeccion_incertidumbre.parquet": incertidumbre,
    "proyeccion_sensibilidad_er.parquet": sens_er,
    "proyeccion_historico_anual.parquet": hist_out,
    "proyeccion_bootstrap_draws.parquet": boot_sample,
    "proyeccion_resumen.parquet": resumen,
}

for name, frame in staging.items():
    path = DATA_S03 / name
    frame.to_parquet(path, index=False)
    print(f"  ✓ {path.relative_to(ROOT)}  ({frame.shape[0]} × {frame.shape[1]})")

for name, frame in {
    "proyeccion_escenarios.csv": escenarios,
    "proyeccion_clase.csv": proy_clase,
    "proyeccion_incertidumbre.csv": incertidumbre,
    "proyeccion_sensibilidad_er.csv": sens_er,
    "proyeccion_resumen.csv": resumen,
}.items():
    frame.to_csv(RESULTS_DIR / name, index=False)

print("\n✓ Proyección de portafolio completada.")
print(escenarios[["escenario", "loss_ratio", "combined_ratio", "resultado_tecnico"]].to_string(index=False))
