"""
Estimación causal DiD escalonado (Callaway–Sant’Anna)
=====================================================
Sección: S04 – Impacto e Inferencia Causal
Subsección: 4.2 – Implementación y estimación de efecto
Proceso: 4.2.1 – ATT del programa de prevención sobre siniestralidad

Descripción:
    Implementa la estrategia 4.1: DiD escalonado Callaway–Sant’Anna (CS)
    con estimador doubly robust, controles nunca tratados y errores
    estándar bootstrap (estructura panel empresa–año).

    Outcome principal: frecuencia_x100
    Outcome secundario (robustez): costo_total / n_trabajadores
    Robusteces: (1) event-study / pre-trends, (2) exclusión de 2020 (COVID),
                (3) control not-yet-treated, (4) outcome de costo.

Inputs:
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/raw/programas_prevencion.csv

Outputs:
    - data/staging/S04/causal_*.parquet
    - results/imgs/01_causal_*.png
    - results/estimacion_efecto.md (escrito aparte)

Uso:
    .venv/bin/python \\
      "sections/S04-Impacto_Inferencia_Causal/4_2_Implementacion y estamacion de efecto/code/01-estimacion/01-estimacion.py"
"""

from __future__ import annotations

import contextlib
import io
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from csdid.att_gt import ATTgt

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

BITERS = 500  # bootstrap CS (SE apropiados a panel / IF)
ALP = 0.05

ROOT = Path(__file__).resolve().parents[5]
DATA_RAW = ROOT / "data" / "raw"
DATA_S01 = ROOT / "data" / "staging" / "S01"
DATA_S04 = ROOT / "data" / "staging" / "S04"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_S04.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S04-4.2.1 | DiD escalonado Callaway–Sant’Anna → ATT programa")
print("=" * 70)


# ──────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────
@contextlib.contextmanager
def _suppress_stdout():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield


def _as_float(x) -> float:
    if isinstance(x, (list, tuple, np.ndarray, pd.Series)):
        return float(np.asarray(x).ravel()[0])
    return float(x)


def build_panel() -> pd.DataFrame:
    """Panel empresa–año con cohorte de adopción g y outcomes."""
    panel = pd.read_parquet(DATA_S01 / "temporal_empresa_anio.parquet")
    emp = pd.read_parquet(DATA_S01 / "empresa_siniestralidad_completa.parquet")
    prog = pd.read_csv(DATA_RAW / "programas_prevencion.csv")

    prog = prog.copy()
    prog["g"] = pd.to_datetime(prog["fecha_inicio"]).dt.year.astype(int)
    prog = prog[
        [
            "id_empresa",
            "g",
            "programa",
            "horas_intervencion",
            "cobertura_trabajadores",
            "fecha_inicio",
        ]
    ].drop_duplicates("id_empresa")

    attrs = emp[["id_empresa", "segmento", "prima_anual"]].copy()

    df = panel.merge(prog, on="id_empresa", how="left")
    df = df.merge(attrs, on="id_empresa", how="left")

    df["g"] = df["g"].fillna(0).astype(int)
    df["firm_id"] = df["id_empresa"].str.replace("E", "", regex=False).astype(int)
    df["anio"] = df["anio"].astype(int)
    df["treated_ever"] = (df["g"] > 0).astype(int)
    df["post"] = ((df["g"] > 0) & (df["anio"] >= df["g"])).astype(int)
    df["rel_year"] = np.where(df["g"] > 0, df["anio"] - df["g"], np.nan)
    df["n_trab_exp"] = df["n_trabajadores"].clip(lower=1).astype(float)
    df["costo_por_trab"] = df["costo_total"] / df["n_trab_exp"]
    df["horas_intervencion"] = df["horas_intervencion"].fillna(0.0)
    df["cobertura_trabajadores"] = df["cobertura_trabajadores"].fillna(0.0)

    return df.sort_values(["id_empresa", "anio"]).reset_index(drop=True)


def fit_cs(
    data: pd.DataFrame,
    yname: str,
    control_group: str = "nevertreated",
    biters: int = BITERS,
) -> ATTgt:
    """Ajusta ATTgt CS doubly robust."""
    np.random.seed(RANDOM_SEED)
    cs = ATTgt(
        yname=yname,
        tname="anio",
        idname="firm_id",
        gname="g",
        data=data,
        control_group=[control_group],
        panel=True,
        allow_unbalanced_panel=True,
        biters=biters,
        alp=ALP,
        print_details=False,
        compute_inffunc=True,
    )
    with _suppress_stdout():
        cs.fit(est_method="dr")
    return cs


def extract_att_gt(cs: ATTgt) -> pd.DataFrame:
    res = cs.results
    se = np.asarray(res["se"]).ravel()
    att = np.asarray(res["att"], dtype=float)
    z = att / np.where(se > 0, se, np.nan)
    return pd.DataFrame(
        {
            "cohort": np.asarray(res["group"], dtype=int),
            "year": np.asarray(res["year"], dtype=int),
            "att": att,
            "se": se,
            "post": np.asarray(res["post"], dtype=int),
            "ci_low": att - 1.96 * se,
            "ci_high": att + 1.96 * se,
            "z": z,
            "significant_95": (np.abs(z) >= 1.96).astype(int),
        }
    )


def extract_agg(cs: ATTgt, typec: str) -> tuple[pd.DataFrame, dict]:
    with _suppress_stdout():
        cs.aggte(typec=typec)
    atte = cs.atte
    overall = {
        "type": typec,
        "att": _as_float(atte["overall_att"]),
        "se": _as_float(atte["overall_se"]),
    }
    overall["ci_low"] = overall["att"] - 1.96 * overall["se"]
    overall["ci_high"] = overall["att"] + 1.96 * overall["se"]
    overall["z"] = overall["att"] / overall["se"] if overall["se"] else np.nan
    overall["significant_95"] = int(abs(overall["z"]) >= 1.96)

    rows = []
    egt = atte.get("egt")
    att_egt = atte.get("att_egt")
    se_egt = atte.get("se_egt")
    if egt is not None and att_egt is not None:
        egt = np.asarray(egt).ravel()
        att_egt = np.asarray(att_egt, dtype=float).ravel()
        se_egt = np.asarray(se_egt, dtype=float).ravel()
        for e, a, s in zip(egt, att_egt, se_egt):
            z = a / s if s else np.nan
            rows.append(
                {
                    "type": typec,
                    "egt": int(e) if typec != "dynamic" else int(e),
                    "att": float(a),
                    "se": float(s),
                    "ci_low": float(a - 1.96 * s),
                    "ci_high": float(a + 1.96 * s),
                    "z": float(z),
                    "significant_95": int(abs(z) >= 1.96) if np.isfinite(z) else 0,
                }
            )
    return pd.DataFrame(rows), overall


def run_spec(
    data: pd.DataFrame,
    label: str,
    yname: str = "frecuencia_x100",
    control_group: str = "nevertreated",
) -> dict:
    print(f"\n[CS] Especificación: {label} | y={yname} | control={control_group}")
    cs = fit_cs(data, yname=yname, control_group=control_group)
    att_gt = extract_att_gt(cs)
    dyn_df, dyn_ov = extract_agg(cs, "dynamic")
    grp_df, grp_ov = extract_agg(cs, "group")
    _, simple_ov = extract_agg(cs, "simple")
    print(
        f"  ATT simple={simple_ov['att']:.4f} (SE={simple_ov['se']:.4f}) "
        f"IC95=[{simple_ov['ci_low']:.4f}, {simple_ov['ci_high']:.4f}]"
    )
    return {
        "label": label,
        "yname": yname,
        "control_group": control_group,
        "cs": cs,
        "att_gt": att_gt,
        "dynamic": dyn_df,
        "group": grp_df,
        "overall_simple": simple_ov,
        "overall_group": grp_ov,
        "overall_dynamic": dyn_ov,
        "n_obs": len(data),
        "n_firms": data["firm_id"].nunique(),
        "n_treated": int((data.groupby("firm_id")["g"].first() > 0).sum()),
    }


def save_parquet(df: pd.DataFrame, name: str) -> Path:
    path = DATA_S04 / name
    df.to_parquet(path, index=False)
    print(f"  [staging] {path.relative_to(ROOT)}  ({df.shape[0]}×{df.shape[1]})")
    return path


def save_fig(fig: plt.Figure, name: str) -> None:
    path = IMGS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] {path.relative_to(ROOT)}")


# ──────────────────────────────────────────────────
# 1. Panel causal
# ──────────────────────────────────────────────────
print("\n[DATOS] Construyendo panel causal...")
panel = build_panel()
n_treated = panel.loc[panel["g"] > 0, "id_empresa"].nunique()
n_control = panel.loc[panel["g"] == 0, "id_empresa"].nunique()
print(f"  filas={len(panel):,} | empresas={panel['id_empresa'].nunique():,}")
print(f"  tratadas={n_treated:,} | nunca tratadas={n_control:,}")
print(f"  cohortes g: {sorted(panel.loc[panel['g'] > 0, 'g'].unique().tolist())}")

panel_out = panel[
    [
        "id_empresa",
        "firm_id",
        "anio",
        "g",
        "treated_ever",
        "post",
        "rel_year",
        "programa",
        "horas_intervencion",
        "cobertura_trabajadores",
        "fecha_inicio",
        "n_siniestros",
        "n_trabajadores",
        "frecuencia_x100",
        "costo_total",
        "costo_por_trab",
        "clase_riesgo",
        "sector",
        "segmento",
        "prima_anual",
    ]
].copy()
save_parquet(panel_out, "causal_panel.parquet")

# ──────────────────────────────────────────────────
# 2. Estimación principal + robusteces
# ──────────────────────────────────────────────────
main = run_spec(panel, label="principal_never_treated")

# Robustez 1: excluir observaciones del año 2020 (shock COVID)
panel_no2020 = panel.loc[panel["anio"] != 2020].copy()
# Drop cohort 2020 entirely (no base period clean within CS for that g if t=2020 gone)
# Keep other cohorts; CS needs pre-period — 2019 cohort still has 2018.
rob_covid = run_spec(panel_no2020, label="excluir_anio_2020")

# Robustez 2: control not-yet-treated
rob_nyt = run_spec(panel, label="not_yet_treated", control_group="notyettreated")

# Robustez 3: outcome de costo por trabajador
rob_cost = run_spec(panel, label="outcome_costo_por_trab", yname="costo_por_trab")

# ──────────────────────────────────────────────────
# 3. Staging de resultados
# ──────────────────────────────────────────────────
print("\n[STAGING] Persistiendo estimaciones...")

att_gt_main = main["att_gt"].assign(spec="principal_never_treated", yname="frecuencia_x100")
save_parquet(att_gt_main, "causal_att_gt.parquet")

dyn_main = main["dynamic"].assign(spec="principal_never_treated", yname="frecuencia_x100")
save_parquet(dyn_main, "causal_att_dynamic.parquet")

grp_main = main["group"].assign(spec="principal_never_treated", yname="frecuencia_x100")
save_parquet(grp_main, "causal_att_group.parquet")

simple_rows = []
for spec in (main, rob_covid, rob_nyt, rob_cost):
    ov = spec["overall_simple"].copy()
    ov["spec"] = spec["label"]
    ov["yname"] = spec["yname"]
    ov["control_group"] = spec["control_group"]
    ov["n_obs"] = spec["n_obs"]
    ov["n_firms"] = spec["n_firms"]
    ov["n_treated"] = spec["n_treated"]
    simple_rows.append(ov)
att_simple = pd.DataFrame(simple_rows)
save_parquet(att_simple, "causal_att_simple.parquet")

# Pre-trends summary from event study (e < 0)
pre = dyn_main.loc[dyn_main["egt"] < 0].copy()
pre_joint = {
    "n_pre_periods": int(len(pre)),
    "max_abs_pre_att": float(pre["att"].abs().max()) if len(pre) else np.nan,
    "n_pre_significant_95": int(pre["significant_95"].sum()) if len(pre) else 0,
    "pre_trends_ok": int(
        (pre["significant_95"].sum() == 0) if len(pre) else 0
    ),
}
pre_df = pd.DataFrame([{**pre_joint, "spec": "principal_never_treated"}])
save_parquet(pre_df, "causal_pretrends.parquet")

rob_tbl = att_simple.copy()
# Relative change vs main ATT for freq specs
main_att = float(main["overall_simple"]["att"])
rob_tbl["att_vs_main"] = np.where(
    rob_tbl["yname"] == "frecuencia_x100",
    rob_tbl["att"] - main_att,
    np.nan,
)
save_parquet(rob_tbl, "causal_robustez.parquet")

# Mean baseline treated pre-adoption for interpretation
treated_pre = panel.loc[(panel["g"] > 0) & (panel["anio"] < panel["g"]), "frecuencia_x100"]
base_mean = float(treated_pre.mean()) if len(treated_pre) else np.nan
att_pct = (main_att / base_mean * 100.0) if base_mean and np.isfinite(base_mean) else np.nan

resumen = pd.DataFrame(
    [
        {
            "estimador": "Callaway-SantAnna_DR",
            "outcome": "frecuencia_x100",
            "control_group": "nevertreated",
            "att_simple": main["overall_simple"]["att"],
            "se_bootstrap": main["overall_simple"]["se"],
            "ci95_low": main["overall_simple"]["ci_low"],
            "ci95_high": main["overall_simple"]["ci_high"],
            "z": main["overall_simple"]["z"],
            "significant_95": main["overall_simple"]["significant_95"],
            "att_group_weighted": main["overall_group"]["att"],
            "se_group": main["overall_group"]["se"],
            "baseline_freq_pre_treated": base_mean,
            "att_pct_vs_baseline": att_pct,
            "n_empresas": main["n_firms"],
            "n_tratadas": main["n_treated"],
            "n_obs": main["n_obs"],
            "biters": BITERS,
            "pre_trends_ok": pre_joint["pre_trends_ok"],
            "n_pre_significant_95": pre_joint["n_pre_significant_95"],
            "rob_excluir_2020_att": rob_covid["overall_simple"]["att"],
            "rob_notyet_att": rob_nyt["overall_simple"]["att"],
            "rob_costo_att": rob_cost["overall_simple"]["att"],
            "rob_costo_se": rob_cost["overall_simple"]["se"],
            "random_seed": RANDOM_SEED,
        }
    ]
)
save_parquet(resumen, "causal_resumen.parquet")

# CSV mirrors in results/
for name, frame in [
    ("causal_att_simple.csv", att_simple),
    ("causal_att_dynamic.csv", dyn_main),
    ("causal_att_group.csv", grp_main),
    ("causal_robustez.csv", rob_tbl),
    ("causal_resumen.csv", resumen),
]:
    frame.to_csv(RESULTS_DIR / name, index=False)

# ──────────────────────────────────────────────────
# 4. Figuras
# ──────────────────────────────────────────────────
print("\n[FIGS] Generando visualizaciones sura_brand...")

# 4.1 Event-study
dyn_plot = dyn_main.sort_values("egt")
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(0, color=sb.GRIS_MEDIO.hex, lw=1, zorder=0)
ax.axvline(-0.5, color=sb.GRIS_CLARO.hex, ls="--", lw=1, zorder=0)
ax.errorbar(
    dyn_plot["egt"],
    dyn_plot["att"],
    yerr=1.96 * dyn_plot["se"],
    fmt="o",
    color=sb.AZUL_SURA.hex,
    ecolor=sb.AQUA_SURA.hex,
    capsize=3,
    markersize=6,
)
ax.set_xlabel("Años relativos al inicio del programa (e)")
ax.set_ylabel("ATT sobre frecuencia ×100")
ax.set_title("Event-study Callaway–Sant’Anna (pre-trends + dinámica)")
sb.add_sura_footer(fig, text="S04-4.2 | DiD escalonado | Controles nunca tratados")
save_fig(fig, "01_causal_event_study.png")

# 4.2 ATT por cohorte
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.axhline(0, color=sb.GRIS_MEDIO.hex, lw=1)
ax.bar(
    grp_main["egt"].astype(str),
    grp_main["att"],
    color=sb.AZUL_SURA.hex,
    alpha=0.85,
    yerr=1.96 * grp_main["se"],
    capsize=4,
    ecolor=sb.AQUA_SURA.hex,
)
ax.set_xlabel("Cohorte de adopción (g)")
ax.set_ylabel("ATT sobre frecuencia ×100")
ax.set_title("ATT por cohorte de adopción")
sb.add_sura_footer(fig, text="S04-4.2 | Agregación group CS")
save_fig(fig, "01_causal_att_cohorte.png")

# 4.3 Trayectorias descriptivas tratado vs control
traj = (
    panel.groupby(["anio", "treated_ever"], as_index=False)["frecuencia_x100"]
    .mean()
    .pivot(index="anio", columns="treated_ever", values="frecuencia_x100")
)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(traj.index, traj[0], color=sb.GRIS_MEDIO.hex, marker="o", label="Nunca tratadas")
ax.plot(traj.index, traj[1], color=sb.AZUL_SURA.hex, marker="o", label="Alguna vez tratadas")
ax.set_xlabel("Año")
ax.set_ylabel("Frecuencia ×100 (media)")
ax.set_title("Trayectorias crudas: tratadas vs nunca tratadas")
ax.legend(frameon=False)
sb.add_sura_footer(fig, text="S04-4.2 | Descriptivo (no causal)")
save_fig(fig, "01_causal_trayectorias.png")

# 4.4 Robustez — ATT simple freq specs
rob_freq = rob_tbl.loc[rob_tbl["yname"] == "frecuencia_x100"].copy()
label_map = {
    "principal_never_treated": "Principal\n(never treated)",
    "excluir_anio_2020": "Excluir\n2020",
    "not_yet_treated": "Not-yet\ntreated",
}
rob_freq["label_plot"] = rob_freq["spec"].map(label_map)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.axhline(0, color=sb.GRIS_MEDIO.hex, lw=1)
ax.errorbar(
    range(len(rob_freq)),
    rob_freq["att"],
    yerr=1.96 * rob_freq["se"],
    fmt="o",
    color=sb.AZUL_SURA.hex,
    ecolor=sb.AQUA_SURA.hex,
    capsize=4,
    markersize=8,
)
ax.set_xticks(range(len(rob_freq)))
ax.set_xticklabels(rob_freq["label_plot"])
ax.set_ylabel("ATT sobre frecuencia ×100")
ax.set_title("Robustez: ATT simple bajo especificaciones alternativas")
sb.add_sura_footer(fig, text="S04-4.2 | Bootstrap SE, biters=500")
save_fig(fig, "01_causal_robustez.png")

# 4.5 Forest plot resumen principal vs costo
fig, ax = plt.subplots(figsize=(8, 3.5))
forest = pd.DataFrame(
    [
        {
            "label": "Frecuencia ×100\n(principal)",
            "att": main["overall_simple"]["att"],
            "se": main["overall_simple"]["se"],
        },
        {
            "label": "Costo / trabajador\n(robustez)",
            "att": rob_cost["overall_simple"]["att"],
            "se": rob_cost["overall_simple"]["se"],
        },
    ]
)
# Normalize costo to comparable visual? Keep separate panels mentally — show z-scores instead
forest["z"] = forest["att"] / forest["se"]
ax.axvline(0, color=sb.GRIS_MEDIO.hex, lw=1)
ax.axvline(-1.96, color=sb.GRIS_CLARO.hex, ls="--", lw=1)
ax.axvline(1.96, color=sb.GRIS_CLARO.hex, ls="--", lw=1)
ax.errorbar(
    forest["z"],
    range(len(forest)),
    xerr=1.96,
    fmt="o",
    color=sb.AZUL_SURA.hex,
    ecolor=sb.AQUA_SURA.hex,
    capsize=4,
    markersize=8,
)
ax.set_yticks(range(len(forest)))
ax.set_yticklabels(forest["label"])
ax.set_xlabel("Estadístico z = ATT / SE")
ax.set_title("Significancia del ATT: frecuencia vs costo/trabajador")
sb.add_sura_footer(fig, text="S04-4.2 | Escalas distintas → se reporta z")
save_fig(fig, "01_causal_forest_z.png")

print("\n" + "=" * 70)
print("  RESUMEN PRINCIPAL")
print("=" * 70)
print(resumen.T.to_string(header=False))
print("\n[OK] Estimación causal 4.2.1 completada.")
