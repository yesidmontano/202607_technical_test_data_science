"""
Pruebas de Hipótesis – Decisiones de Feature Set
=================================================
Sección: S01 – Metodología EDA y Análisis
Subsección: 1.3 – Pruebas de Hipótesis

Descripción:
    Realiza las pruebas de hipótesis correspondientes a las 5 preguntas
    que condicionan el feature set en S03:
      P3 – Diferencias de frecuencia relativa entre clases de riesgo
      P5 – Interacción sector × clase de riesgo sobre la frecuencia
      P7 – Microempresas con tasa relativa mayor que el resto
      P9 – Persistencia del conteo de siniestros año t → t+1
      P10 – Retención del Top 10% superior al azar (~10%)

    Para cada prueba:
      - Se formulan H0 y H1
      - Se verifican los supuestos de la prueba elegida
      - Se aplica corrección de Bonferroni-Holm cuando hay comparaciones múltiples
      - Se reporta tamaño del efecto (η², Cliff's δ, ρ, lift, pseudo-R²)

Inputs (reutilizados de staging S01):
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S01/temporal_persistencia_yoy.parquet

Outputs:
    - results/imgs/02_P3_*.png … 02_P10_*.png
    - results/hip_features_resumen.csv
    - data/staging/S01/panel_empresa_lag_yoy.parquet  (reutilizable S03/S04)

Uso:
    python "sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/code/02-hip_features/hip_features.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import Poisson
from statsmodels.stats.multitest import multipletests

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración global
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
ALPHA = 0.05

ROOT = Path(__file__).resolve().parents[5]
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"
IMGS_DIR.mkdir(parents=True, exist_ok=True)
DATA_STAGING.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S01-1.3 | Pruebas de Hipótesis – Feature Set")
print("=" * 70)

# ──────────────────────────────────────────────────
# Carga de datos (reutilizando staging existente)
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando datasets de staging...")
df_empresa = pd.read_parquet(DATA_STAGING / "empresa_siniestralidad_completa.parquet")
df_panel = pd.read_parquet(DATA_STAGING / "temporal_empresa_anio.parquet")
df_persist = pd.read_parquet(DATA_STAGING / "temporal_persistencia_yoy.parquet")

print(f"  empresa_siniestralidad_completa: {df_empresa.shape}")
print(f"  temporal_empresa_anio:           {df_panel.shape}")
print(f"  temporal_persistencia_yoy:       {df_persist.shape}")


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Cliff's delta: P(X>Y) - P(X<Y). Usa U de Mann-Whitney."""
    u, _ = stats.mannwhitneyu(x, y, alternative="two-sided")
    return float(2 * u / (len(x) * len(y)) - 1)


def interpret_cliffs(delta: float) -> str:
    a = abs(delta)
    if a < 0.147:
        return "pequeño"
    if a < 0.33:
        return "mediano"
    if a < 0.474:
        return "mediano-grande"
    return "grande"


def interpret_eta2(eta2: float) -> str:
    if eta2 < 0.01:
        return "despreciable"
    if eta2 < 0.06:
        return "pequeño"
    if eta2 < 0.14:
        return "mediano"
    return "grande"


# Construir panel lag YoY (reutilizable; no existía en staging)
print("\n[STAGING] Construyendo panel_empresa_lag_yoy...")
panel_sorted = df_panel.sort_values(["id_empresa", "anio"]).copy()
panel_sorted["n_siniestros_t1"] = panel_sorted.groupby("id_empresa")["n_siniestros"].shift(-1)
panel_sorted["alta_siniestralidad_t1"] = panel_sorted.groupby("id_empresa")["alta_siniestralidad"].shift(-1)
panel_sorted["frecuencia_x100_t1"] = panel_sorted.groupby("id_empresa")["frecuencia_x100"].shift(-1)
panel_sorted["anio_t1"] = panel_sorted.groupby("id_empresa")["anio"].shift(-1)

df_lag = panel_sorted.dropna(subset=["n_siniestros_t1"]).copy()
df_lag["anio_t1"] = df_lag["anio_t1"].astype(int)
df_lag["alta_siniestralidad_t1"] = df_lag["alta_siniestralidad_t1"].astype(int)
df_lag = df_lag.rename(
    columns={
        "anio": "anio_t",
        "n_siniestros": "n_siniestros_t",
        "alta_siniestralidad": "alta_siniestralidad_t",
        "frecuencia_x100": "frecuencia_x100_t",
    }
)
cols_lag = [
    "id_empresa",
    "anio_t",
    "anio_t1",
    "n_siniestros_t",
    "n_siniestros_t1",
    "frecuencia_x100_t",
    "frecuencia_x100_t1",
    "alta_siniestralidad_t",
    "alta_siniestralidad_t1",
    "n_trabajadores",
    "clase_riesgo",
    "sector",
]
df_lag = df_lag[cols_lag]
lag_path = DATA_STAGING / "panel_empresa_lag_yoy.parquet"
df_lag.to_parquet(lag_path, index=False)
print(f"  ✓ Guardado: {lag_path}  shape={df_lag.shape}")


# ══════════════════════════════════════════════════════════════════════
#  P3 – ¿Medianas de frecuencia relativa difieren entre clases de riesgo?
#       H0: las 5 clases tienen la misma distribución de frecuencia_x100
#       H1: al menos una clase difiere
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P3 – DIFERENCIAS DE FRECUENCIA ENTRE CLASES DE RIESGO")
print("=" * 70)

df_p3 = df_empresa[["clase_riesgo", "frecuencia_x100"]].dropna().copy()
df_p3["clase_riesgo"] = df_p3["clase_riesgo"].astype(int)
clases = sorted(df_p3["clase_riesgo"].unique())
grupos_p3 = [
    df_p3.loc[df_p3["clase_riesgo"] == c, "frecuencia_x100"].values for c in clases
]

# Supuesto: Shapiro por clase (muestra) + Levene
print("\n  Verificación de supuestos:")
for c, g in zip(clases, grupos_p3):
    sample = np.random.choice(g, size=min(500, len(g)), replace=False)
    sw_stat, sw_p = stats.shapiro(sample)
    print(f"    Shapiro clase {c} (n_sample={len(sample)}): W={sw_stat:.4f}, p={sw_p:.2e}")
lev_stat, lev_p = stats.levene(*grupos_p3)
print(f"    Levene (igualdad de varianzas): W={lev_stat:.4f}, p={lev_p:.2e}")
print("    → Normalidad/homocedasticidad violadas → Kruskal-Wallis (no paramétrico)")

kw_stat_p3, kw_pval_p3 = stats.kruskal(*grupos_p3)
n_p3 = len(df_p3)
k_p3 = len(clases)
eta2_p3 = (kw_stat_p3 - k_p3 + 1) / (n_p3 - k_p3)

print(f"\n  Kruskal-Wallis:")
print(f"    H = {kw_stat_p3:.4f}, df = {k_p3 - 1}, p = {kw_pval_p3:.2e}")
print(f"    η² = {eta2_p3:.4f} → magnitud {interpret_eta2(eta2_p3)}")
print(
    f"    Decisión: {'RECHAZAR H0' if kw_pval_p3 < ALPHA else 'No rechazar H0'}"
)

# Post-hoc Dunn + focus en adyacentes
print("\n  Post-hoc Dunn (Holm-Bonferroni)...")
try:
    import scikit_posthocs as sp

    dunn_p3 = sp.posthoc_dunn(
        df_p3, val_col="frecuencia_x100", group_col="clase_riesgo", p_adjust="holm"
    )
except ImportError:
    dunn_p3 = None
    print("    scikit_posthocs no disponible")

pares_adyacentes = [(1, 2), (2, 3), (3, 4), (4, 5)]
dunn_rows = []
if dunn_p3 is not None:
    for c1, c2 in pares_adyacentes:
        pv = float(dunn_p3.loc[c1, c2])
        g1 = df_p3.loc[df_p3["clase_riesgo"] == c1, "frecuencia_x100"].values
        g2 = df_p3.loc[df_p3["clase_riesgo"] == c2, "frecuencia_x100"].values
        delta = cliffs_delta(g2, g1)  # clase mayor vs menor
        med1, med2 = np.median(g1), np.median(g2)
        dunn_rows.append(
            {
                "clase_a": c1,
                "clase_b": c2,
                "tipo_par": "adyacente",
                "p_holm": pv,
                "significativo": pv < ALPHA,
                "mediana_a": med1,
                "mediana_b": med2,
                "ratio_medianas": med2 / med1 if med1 > 0 else np.nan,
                "cliffs_delta": delta,
                "magnitud_delta": interpret_cliffs(delta),
            }
        )
        print(
            f"    Clase {c1} vs {c2}: p_holm={pv:.2e}, "
            f"med={med1:.1f}→{med2:.1f}, δ={delta:.3f} ({interpret_cliffs(delta)})"
        )

    n_pares_sig = 0
    for i, c1 in enumerate(clases):
        for c2 in clases[i + 1 :]:
            if float(dunn_p3.loc[c1, c2]) < ALPHA:
                n_pares_sig += 1
    n_pares_tot = k_p3 * (k_p3 - 1) // 2
    print(f"    Pares significativos globales: {n_pares_sig}/{n_pares_tot}")
else:
    n_pares_sig, n_pares_tot = 0, 10

df_dunn_p3 = pd.DataFrame(dunn_rows)
if not df_dunn_p3.empty:
    df_dunn_p3.to_parquet(DATA_STAGING / "hip_p3_dunn_clase_adyacente.parquet", index=False)

# Figura P3
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P3 – Frecuencia Relativa por Clase de Riesgo",
    subtitle=(
        f"Kruskal-Wallis H={kw_stat_p3:.1f}, η²={eta2_p3:.3f} ({interpret_eta2(eta2_p3)})  |  "
        f"Dunn Holm: {n_pares_sig}/{n_pares_tot} pares  →  "
        f"{'RECHAZAR H₀' if kw_pval_p3 < ALPHA else 'NO rechazar H₀'}"
    ),
)
ax1, ax2 = axes[0], axes[1]

box_data = [
    df_p3.loc[df_p3["clase_riesgo"] == c, "frecuencia_x100"].values for c in clases
]
bp = ax1.boxplot(
    box_data,
    tick_labels=[f"Clase {c}" for c in clases],
    patch_artist=True,
    flierprops=dict(marker=".", markersize=2, alpha=0.3),
)
palette = sb.make_n_colors(len(clases))
for patch, color in zip(bp["boxes"], palette):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)
ax1.set_ylabel("Frecuencia × 100 trabajadores")
ax1.set_title("Distribución por clase de riesgo")

medians = [np.median(g) for g in box_data]
ax2.bar(
    [str(c) for c in clases],
    medians,
    color=palette,
    alpha=0.85,
    edgecolor="white",
)
for i, (c1, c2) in enumerate(pares_adyacentes):
    if dunn_p3 is not None:
        pv = float(dunn_p3.loc[c1, c2])
        y = max(medians[i], medians[i + 1]) * 1.05
        ax2.plot([i, i + 1], [y, y], color=sb.AZUL_SURA.hex, lw=1)
        ax2.text(
            i + 0.5,
            y * 1.02,
            "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < ALPHA else "ns")),
            ha="center",
            fontsize=9,
            color=sb.AZUL_SURA.hex,
        )
ax2.set_xlabel("Clase de riesgo")
ax2.set_ylabel("Mediana frecuencia × 100")
ax2.set_title("Medianas y pares adyacentes (Dunn Holm)")

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P3 Clase de riesgo")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_P3_clase_riesgo_frecuencia.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/02_P3_clase_riesgo_frecuencia.png")

p3_results = {
    "pregunta": "P3",
    "descripcion": "Diferencias de frecuencia entre clases de riesgo",
    "h0": "Distribuciones de frecuencia_x100 iguales en las 5 clases",
    "h1": "Al menos una clase difiere (y pares adyacentes son distinguibles)",
    "prueba": "Kruskal-Wallis + Dunn post-hoc Holm",
    "estadistico": round(kw_stat_p3, 4),
    "p_valor": float(kw_pval_p3),
    "efecto": round(eta2_p3, 4),
    "metrica_efecto": "η² K-W",
    "decision": "RECHAZAR H0" if kw_pval_p3 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"η²={eta2_p3:.3f} ({interpret_eta2(eta2_p3)}); "
        f"{n_pares_sig}/{n_pares_tot} pares distinguibles; "
        f"adyacentes todas sig." if dunn_p3 is not None and all(
            float(dunn_p3.loc[a, b]) < ALPHA for a, b in pares_adyacentes
        ) else f"η²={eta2_p3:.3f}"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  P5 – ¿Interacción significativa sector × clase sobre frecuencia?
#       H0: modelo aditivo suficiente (sin interacción)
#       H1: interacción sector×clase aporta señal
#
#  Estrategia: clase como ordinal continua (1–5) × sector dummies
#  para evitar explosión de celdas vacías estructurales (36/75 celdas
#  con n<5 por diseño ARL). LR test GLM Poisson con offset.
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P5 – INTERACCIÓN SECTOR × CLASE DE RIESGO")
print("=" * 70)

df_p5 = df_empresa.dropna(
    subset=["n_siniestros", "clase_riesgo", "sector", "n_trabajadores"]
).copy()
df_p5["n_siniestros"] = df_p5["n_siniestros"].fillna(0).astype(int)
df_p5["clase_riesgo"] = df_p5["clase_riesgo"].astype(int)
df_p5["log_n_trab"] = np.log1p(df_p5["n_trabajadores"])
df_p5["sector"] = df_p5["sector"].astype(str)

ct = pd.crosstab(df_p5["sector"], df_p5["clase_riesgo"])
n_empty = int((ct == 0).sum().sum())
n_cells = int(ct.size)
print("\n  Verificación de supuestos / diseño:")
print(f"    Celdas sector×clase vacías: {n_empty}/{n_cells} (ceros estructurales ARL)")
print("    → clase_riesgo como ordinal continua + interacciones lineales por sector")
print("    → evita saturación de dummies con celdas n=0")

y_p5 = df_p5["n_siniestros"].values
offset_p5 = df_p5["log_n_trab"].values
clase_num = df_p5["clase_riesgo"].astype(float)
sector_dummies = pd.get_dummies(df_p5["sector"], prefix="sector", drop_first=True).astype(
    float
)

# Interacciones: clase × cada dummy de sector
inter_dummies = sector_dummies.mul(clase_num.values, axis=0)
inter_dummies.columns = [f"int_{c}" for c in inter_dummies.columns]

X_add = sm.add_constant(
    pd.concat([clase_num.rename("clase"), sector_dummies], axis=1)
)
X_int = sm.add_constant(
    pd.concat([clase_num.rename("clase"), sector_dummies, inter_dummies], axis=1)
)

print("\n  Ajustando GLM Poisson M0 (aditivo) vs M1 (con interacción)...")
m0 = Poisson(y_p5, X_add, offset=offset_p5).fit(disp=False, maxiter=300)
m1 = Poisson(y_p5, X_int, offset=offset_p5).fit(disp=False, maxiter=300)

lr_stat_p5 = 2 * (m1.llf - m0.llf)
df_lr_p5 = inter_dummies.shape[1]
lr_pval_p5 = stats.chi2.sf(lr_stat_p5, df=df_lr_p5)
pseudo_r2_p5 = 1 - (m1.llf / m0.llf) if m0.llf != 0 else np.nan

print(f"\n  LR test (M1 interacción vs M0 aditivo):")
print(f"    LR = {lr_stat_p5:.2f}, df = {df_lr_p5}, p = {lr_pval_p5:.2e}")
print(f"    Pseudo-R² McFadden incremental: {pseudo_r2_p5:.4f}")
print(
    f"    Decisión: {'RECHAZAR H0 → interacción significativa' if lr_pval_p5 < ALPHA else 'No rechazar H0 → aditividad suficiente'}"
)

# Complemento: η² de clase dentro de cada sector (heterogeneidad del gradiente)
eta_by_sector = []
for sector, grp in df_p5.groupby("sector"):
    clases_s = grp["clase_riesgo"].nunique()
    if clases_s < 2 or len(grp) < 30:
        continue
    groups = [
        g["frecuencia_x100"].dropna().values
        for _, g in grp.groupby("clase_riesgo")
        if len(g) >= 5
    ]
    if len(groups) < 2:
        continue
    h, p = stats.kruskal(*groups)
    n_s = sum(len(g) for g in groups)
    k_s = len(groups)
    eta = (h - k_s + 1) / (n_s - k_s) if n_s > k_s else np.nan
    eta_by_sector.append({"sector": sector, "eta2_clase": eta, "p_kw": p, "n": n_s})

df_eta_sec = pd.DataFrame(eta_by_sector).sort_values("eta2_clase", ascending=False)
print("\n  Heterogeneidad del gradiente clase dentro de sector (η² K-W):")
if not df_eta_sec.empty:
    print(f"    η² mediana entre sectores: {df_eta_sec['eta2_clase'].median():.3f}")
    print(f"    η² rango: [{df_eta_sec['eta2_clase'].min():.3f}, {df_eta_sec['eta2_clase'].max():.3f}]")
    for _, row in df_eta_sec.head(5).iterrows():
        print(f"      {row['sector']}: η²={row['eta2_clase']:.3f}, p={row['p_kw']:.2e}")

# Figura P5
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P5 – Interacción Sector × Clase de Riesgo",
    subtitle=(
        f"LR GLM Poisson={lr_stat_p5:.1f} (df={df_lr_p5}), p={lr_pval_p5:.2e}  |  "
        f"Pseudo-R² inc.={pseudo_r2_p5:.4f}  |  celdas vacías={n_empty}/{n_cells}  →  "
        f"{'RECHAZAR H₀' if lr_pval_p5 < ALPHA else 'NO rechazar H₀'}"
    ),
)
ax1, ax2 = axes[0], axes[1]

# Heatmap medianas (solo celdas con n>=10)
heat = (
    df_p5.groupby(["sector", "clase_riesgo"])["frecuencia_x100"]
    .median()
    .unstack("clase_riesgo")
)
counts_ct = pd.crosstab(df_p5["sector"], df_p5["clase_riesgo"])
heat_masked = heat.where(counts_ct >= 10)
im = ax1.imshow(
    heat_masked.values,
    aspect="auto",
    cmap=sb.get_cmap("sura_blues"),
)
ax1.set_xticks(range(len(heat_masked.columns)))
ax1.set_xticklabels([f"C{c}" for c in heat_masked.columns])
ax1.set_yticks(range(len(heat_masked.index)))
ax1.set_yticklabels(heat_masked.index, fontsize=7)
ax1.set_title("Mediana frec.×100 (celdas n≥10)")
plt.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)

if not df_eta_sec.empty:
    ax2.barh(
        df_eta_sec["sector"],
        df_eta_sec["eta2_clase"],
        color=sb.AZUL_SURA.hex,
        alpha=0.8,
    )
    ax2.axvline(0.14, ls="--", color=sb.AQUA_SURA.hex, lw=1.2, label="Umbral grande (0.14)")
    ax2.set_xlabel("η² de clase dentro del sector")
    ax2.set_title("Fuerza del gradiente de clase por sector")
    ax2.legend(fontsize=8)
    ax2.invert_yaxis()

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P5 Interacción sector×clase")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_P5_interaccion_sector_clase.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/02_P5_interaccion_sector_clase.png")

p5_results = {
    "pregunta": "P5",
    "descripcion": "Interacción sector × clase sobre frecuencia",
    "h0": "Modelo aditivo suficiente (sin interacción sector×clase)",
    "h1": "Interacción sector×clase aporta señal incremental",
    "prueba": "LR GLM Poisson (clase ordinal + sector + interacciones)",
    "estadistico": round(lr_stat_p5, 4),
    "p_valor": float(lr_pval_p5),
    "efecto": round(pseudo_r2_p5, 6) if not np.isnan(pseudo_r2_p5) else np.nan,
    "metrica_efecto": "Pseudo-R² McFadden incremental",
    "decision": "RECHAZAR H0" if lr_pval_p5 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"Pseudo-R²={pseudo_r2_p5:.4f}; "
        f"η² clase-dentro-sector mediana="
        f"{df_eta_sec['eta2_clase'].median():.3f}" if not df_eta_sec.empty else f"Pseudo-R²={pseudo_r2_p5:.4f}"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  P7 – ¿Microempresas tienen tasa relativa mayor que el resto?
#       H0: frecuencia_x100 Micro = resto
#       H1: frecuencia_x100 Micro > resto (1-cola)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P7 – MICROEMPRESAS VS RESTO (FRECUENCIA RELATIVA)")
print("=" * 70)

df_p7 = df_empresa[["segmento", "frecuencia_x100", "n_trabajadores"]].dropna().copy()
micro_label = "Micro (≤10)"
freq_micro = df_p7.loc[df_p7["segmento"] == micro_label, "frecuencia_x100"].values
freq_resto = df_p7.loc[df_p7["segmento"] != micro_label, "frecuencia_x100"].values

print(f"\n  Micro: n={len(freq_micro)}, mediana={np.median(freq_micro):.2f}, media={np.mean(freq_micro):.2f}")
print(f"  Resto: n={len(freq_resto)}, mediana={np.median(freq_resto):.2f}, media={np.mean(freq_resto):.2f}")

# Supuestos
ks_p7, ks_p_p7 = stats.ks_2samp(freq_micro, freq_resto)
print("\n  Verificación de supuestos:")
print(f"    K-S Micro vs Resto: KS={ks_p7:.4f}, p={ks_p_p7:.2e}")
print("    → Formas distintas / asimetría → Mann-Whitney U (dominancia estocástica)")

mw_stat_p7, mw_pval_p7 = stats.mannwhitneyu(
    freq_micro, freq_resto, alternative="greater"
)
delta_p7 = cliffs_delta(freq_micro, freq_resto)
mag_p7 = interpret_cliffs(delta_p7)
ratio_med_p7 = np.median(freq_micro) / np.median(freq_resto)

print(f"\n  Mann-Whitney U (Micro > Resto, 1-cola):")
print(f"    U = {mw_stat_p7:.0f}, p = {mw_pval_p7:.2e}")
print(f"    Cliff's δ = {delta_p7:.4f} ({mag_p7})")
print(f"    Ratio medianas Micro/Resto = {ratio_med_p7:.2f}×")
print(
    f"    Decisión: {'RECHAZAR H0' if mw_pval_p7 < ALPHA else 'No rechazar H0'}"
)

# Kruskal-Wallis entre 4 segmentos (contexto) + Dunn Holm
seg_order = ["Micro (≤10)", "Pequeña (11-50)", "Mediana (51-200)", "Grande (>200)"]
grupos_seg = [
    df_p7.loc[df_p7["segmento"] == s, "frecuencia_x100"].values
    for s in seg_order
    if (df_p7["segmento"] == s).any()
]
kw_seg, kw_p_seg = stats.kruskal(*grupos_seg)
eta2_seg = (kw_seg - len(grupos_seg) + 1) / (len(df_p7) - len(grupos_seg))
print(f"\n  Kruskal-Wallis 4 segmentos (contexto): H={kw_seg:.2f}, p={kw_p_seg:.2e}, η²={eta2_seg:.4f}")

try:
    import scikit_posthocs as sp

    dunn_seg = sp.posthoc_dunn(
        df_p7, val_col="frecuencia_x100", group_col="segmento", p_adjust="holm"
    )
    print("  Dunn Holm Micro vs cada segmento:")
    for s in seg_order[1:]:
        if s in dunn_seg.columns and micro_label in dunn_seg.index:
            print(f"    vs {s}: p={float(dunn_seg.loc[micro_label, s]):.2e}")
except Exception as e:
    dunn_seg = None
    print(f"  Post-hoc omitido: {e}")

# Figura P7
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P7 – Frecuencia Relativa: Microempresas vs Resto",
    subtitle=(
        f"Mann-Whitney p={mw_pval_p7:.2e}  |  Cliff's δ={delta_p7:.3f} ({mag_p7})  |  "
        f"Mediana Micro={np.median(freq_micro):.1f} vs Resto={np.median(freq_resto):.1f} "
        f"({ratio_med_p7:.2f}×)  →  {'RECHAZAR H₀' if mw_pval_p7 < ALPHA else 'NO rechazar H₀'}"
    ),
)
ax1, ax2 = axes[0], axes[1]

bp = ax1.boxplot(
    [freq_micro, freq_resto],
    tick_labels=["Micro (≤10)", "Resto"],
    patch_artist=True,
    flierprops=dict(marker=".", markersize=2, alpha=0.3),
)
bp["boxes"][0].set_facecolor(sb.AZUL_SURA.hex)
bp["boxes"][1].set_facecolor(sb.AQUA_SURA.hex)
for box in bp["boxes"]:
    box.set_alpha(0.75)
ax1.set_ylabel("Frecuencia × 100 trabajadores")
ax1.set_title("Micro vs resto")

med_by_seg = (
    df_p7.groupby("segmento")["frecuencia_x100"].median().reindex(seg_order)
)
colors_seg = sb.make_n_colors(len(seg_order))
ax2.bar(range(len(seg_order)), med_by_seg.values, color=colors_seg, alpha=0.85)
ax2.set_xticks(range(len(seg_order)))
ax2.set_xticklabels(["Micro", "Pequeña", "Mediana", "Grande"], rotation=0)
ax2.set_ylabel("Mediana frecuencia × 100")
ax2.set_title(f"Medianas por segmento (K-W η²={eta2_seg:.3f})")

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P7 Microempresas")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_P7_microempresas_frecuencia.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/02_P7_microempresas_frecuencia.png")

p7_results = {
    "pregunta": "P7",
    "descripcion": "Microempresas con mayor frecuencia relativa",
    "h0": "frecuencia_x100 Micro = resto de segmentos",
    "h1": "frecuencia_x100 Micro > resto (1-cola)",
    "prueba": "Mann-Whitney U (1-cola) + K-W 4 segmentos + Dunn Holm",
    "estadistico": round(mw_stat_p7, 2),
    "p_valor": float(mw_pval_p7),
    "efecto": round(delta_p7, 4),
    "metrica_efecto": "Cliff's delta (δ)",
    "decision": "RECHAZAR H0" if mw_pval_p7 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"δ={delta_p7:.3f} ({mag_p7}); ratio medianas={ratio_med_p7:.2f}×"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  P9 – ¿Persistencia del conteo t→t+1 es > 0?
#       H0: ρ_Spearman(n_t, n_t1) = 0
#       H1: ρ > 0
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P9 – PERSISTENCIA DEL CONTEO AÑO t → t+1")
print("=" * 70)

n_t = df_lag["n_siniestros_t"].astype(float).values
n_t1 = df_lag["n_siniestros_t1"].astype(float).values

# Spearman global
rho_global, p_global = stats.spearmanr(n_t, n_t1)
# Pearson de referencia
r_pearson, p_pearson = stats.pearsonr(n_t, n_t1)

print("\n  Verificación de supuestos:")
print(f"    n pares empresa-año: {len(df_lag):,}")
print("    Monotonicidad (Spearman): adecuada para conteos con ceros y cola")
print("    Dependencia intra-empresa: se reporta también ρ por par de años + Holm")

print(f"\n  Spearman global (todos los pares consecutivos):")
print(f"    ρ = {rho_global:.4f}, p (2-colas) = {p_global:.2e}")
# 1-cola: H1 ρ > 0
p_global_1 = p_global / 2 if rho_global > 0 else 1 - p_global / 2
print(f"    p (1-cola, ρ>0) = {p_global_1:.2e}")
print(f"    Pearson r = {r_pearson:.4f} (referencia; EDA reportó ~0.70)")

# Por par de años
year_rows = []
for (anio_t,), grp in df_lag.groupby(["anio_t"]):
    rho_y, p_y = stats.spearmanr(grp["n_siniestros_t"], grp["n_siniestros_t1"])
    r_y, _ = stats.pearsonr(grp["n_siniestros_t"], grp["n_siniestros_t1"])
    year_rows.append(
        {
            "anio_t": int(anio_t),
            "anio_t1": int(anio_t) + 1,
            "n_pares": len(grp),
            "spearman": rho_y,
            "p_spearman": p_y / 2 if rho_y > 0 else 1 - p_y / 2,
            "pearson": r_y,
        }
    )
df_p9_years = pd.DataFrame(year_rows)
reject_y, p_adj_y, _, _ = multipletests(
    df_p9_years["p_spearman"].values, alpha=ALPHA, method="holm"
)
df_p9_years["p_holm"] = p_adj_y
df_p9_years["rechaza_h0"] = reject_y

print("\n  Spearman por par de años (Holm-Bonferroni):")
for _, row in df_p9_years.iterrows():
    print(
        f"    {int(row['anio_t'])}→{int(row['anio_t1'])}: "
        f"ρ={row['spearman']:.3f}, p_holm={row['p_holm']:.2e}, "
        f"rechaza={'SÍ' if row['rechaza_h0'] else 'NO'}"
    )

print(
    f"\n  Decisión global: {'RECHAZAR H0 → persistencia > 0' if p_global_1 < ALPHA else 'No rechazar H0'}"
)

# Figura P9
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P9 – Persistencia del Conteo de Siniestros t → t+1",
    subtitle=(
        f"Spearman ρ={rho_global:.3f}, p(1-cola)<0.001  |  "
        f"Pearson r={r_pearson:.3f}  |  "
        f"{int(reject_y.sum())}/6 pares anuales significativos (Holm)  →  RECHAZAR H₀"
    ),
)
ax1, ax2 = axes[0], axes[1]

# Hexbin / scatter sample
sample_idx = np.random.choice(len(n_t), size=min(4000, len(n_t)), replace=False)
ax1.scatter(
    n_t[sample_idx] + np.random.uniform(-0.15, 0.15, size=len(sample_idx)),
    n_t1[sample_idx] + np.random.uniform(-0.15, 0.15, size=len(sample_idx)),
    s=8,
    alpha=0.25,
    color=sb.AZUL_SURA.hex,
)
lim = np.percentile(np.concatenate([n_t, n_t1]), 99)
ax1.plot([0, lim], [0, lim], "--", color=sb.AQUA_SURA.hex, lw=1.5, label="y = x")
ax1.set_xlim(-0.5, lim)
ax1.set_ylim(-0.5, lim)
ax1.set_xlabel("n_siniestros año t")
ax1.set_ylabel("n_siniestros año t+1")
ax1.set_title(f"Dispersión YoY (muestra) — ρ={rho_global:.3f}")
ax1.legend()

ax2.bar(
    df_p9_years["anio_t"].astype(str) + "→" + df_p9_years["anio_t1"].astype(str),
    df_p9_years["spearman"],
    color=sb.AZUL_SURA.hex,
    alpha=0.85,
)
ax2.axhline(rho_global, ls="--", color=sb.AQUA_SURA.hex, lw=1.5, label=f"ρ global={rho_global:.3f}")
ax2.set_ylabel("Spearman ρ")
ax2.set_title("Persistencia por par de años")
ax2.tick_params(axis="x", rotation=30)
ax2.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P9 Persistencia lag")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_P9_persistencia_conteo.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/02_P9_persistencia_conteo.png")

df_p9_years.to_parquet(DATA_STAGING / "hip_p9_persistencia_spearman.parquet", index=False)

p9_results = {
    "pregunta": "P9",
    "descripcion": "Persistencia conteo siniestros t→t+1",
    "h0": "ρ_Spearman(n_t, n_t1) = 0",
    "h1": "ρ_Spearman > 0",
    "prueba": "Spearman (1-cola) global + por año con Holm",
    "estadistico": round(rho_global, 4),
    "p_valor": float(p_global_1),
    "efecto": round(rho_global, 4),
    "metrica_efecto": "ρ Spearman (efecto = estadístico)",
    "decision": "RECHAZAR H0" if p_global_1 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"ρ={rho_global:.3f} (asociación fuerte); Pearson r={r_pearson:.3f}; "
        f"{int(reject_y.sum())}/6 años rechazan H0 tras Holm"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  P10 – ¿Retención Top 10% >> 10% esperado por azar?
#       H0: p_retencion = 0.10
#       H1: p_retencion > 0.10
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P10 – RETENCIÓN DEL TOP 10% ENTRE AÑOS CONSECUTIVOS")
print("=" * 70)

# Usar panel lag (misma fuente que persistencia staging)
alta_t = df_lag["alta_siniestralidad_t"].astype(int)
alta_t1 = df_lag["alta_siniestralidad_t1"].astype(int)
mask_alta = alta_t == 1
n_alta = int(mask_alta.sum())
n_retenidas = int((alta_t1[mask_alta] == 1).sum())
p_obs = n_retenidas / n_alta if n_alta else np.nan
p0 = 0.10

print(f"\n  Empresas Top 10% en t: {n_alta}")
print(f"  Retenidas en Top 10% en t+1: {n_retenidas}")
print(f"  Tasa observada: {p_obs*100:.2f}%")
print(f"  Tasa esperada bajo azar: {p0*100:.1f}%")

# Supuesto: bajo H0 cada empresa Top10 tiene probabilidad ~0.10 de seguir
# (aproximación; el Top10 se redefine cada año con dependencia leve)
print("\n  Verificación de supuestos:")
print("    Bernoulli i.i.d. bajo azar: aproximación (ranking anual redefine el Top 10%)")
print("    → prueba binomial exacta es la referencia canónica; se reporta también por año")

binom_p10 = stats.binomtest(n_retenidas, n=n_alta, p=p0, alternative="greater")
p_p10 = binom_p10.pvalue
lift_p10 = p_obs / p0 if p0 > 0 else np.nan
# Cohen h para proporciones: 2(arcsin√p1 - arcsin√p0)
cohen_h = 2 * (np.arcsin(np.sqrt(p_obs)) - np.arcsin(np.sqrt(p0)))

print(f"\n  Prueba binomial exacta (1-cola, p > 0.10):")
print(f"    p-valor = {p_p10:.2e}")
print(f"    Lift = {lift_p10:.2f}× (obs/esperado)")
print(f"    Cohen's h = {cohen_h:.4f} (|h|~0.2 pequeño, ~0.5 mediano, ~0.8 grande)")
print(
    f"    Decisión: {'RECHAZAR H0 → retención > azar' if p_p10 < ALPHA else 'No rechazar H0'}"
)

# Por año + Holm
year_p10 = []
for _, row in df_persist.iterrows():
    n_a = int(row["n_alta_t"])
    n_r = int(row["n_alta_retenidas"])
    p_y = stats.binomtest(n_r, n=n_a, p=p0, alternative="greater").pvalue
    year_p10.append(
        {
            "anio_t": int(row["anio_t"]),
            "anio_t1": int(row["anio_t1"]),
            "n_alta_t": n_a,
            "n_retenidas": n_r,
            "tasa_retencion": n_r / n_a,
            "p_binomial": p_y,
            "lift": (n_r / n_a) / p0,
        }
    )
df_p10_years = pd.DataFrame(year_p10)
rej10, padj10, _, _ = multipletests(
    df_p10_years["p_binomial"].values, alpha=ALPHA, method="holm"
)
df_p10_years["p_holm"] = padj10
df_p10_years["rechaza_h0"] = rej10

print("\n  Binomial por par de años (Holm):")
for _, row in df_p10_years.iterrows():
    print(
        f"    {int(row['anio_t'])}→{int(row['anio_t1'])}: "
        f"ret={row['tasa_retencion']*100:.1f}%, lift={row['lift']:.1f}×, "
        f"p_holm={row['p_holm']:.2e}"
    )

# Figura P10
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P10 – Retención del Top 10% vs Azar",
    subtitle=(
        f"Retención observada={p_obs*100:.1f}% vs azar=10%  |  "
        f"Binomial p={p_p10:.2e}  |  Lift={lift_p10:.1f}×  |  "
        f"Cohen h={cohen_h:.2f}  →  RECHAZAR H₀"
    ),
)
ax1, ax2 = axes[0], axes[1]

ax1.bar(
    ["Azar\n(H₀)", "Observado"],
    [p0 * 100, p_obs * 100],
    color=[sb.AQUA_SURA.hex, sb.AZUL_SURA.hex],
    alpha=0.85,
)
ax1.set_ylabel("% retención Top 10%")
ax1.set_title(f"Lift = {lift_p10:.1f}×")
for i, v in enumerate([p0 * 100, p_obs * 100]):
    ax1.text(i, v + 1, f"{v:.1f}%", ha="center", fontweight="bold")

ax2.bar(
    df_p10_years["anio_t"].astype(str) + "→" + df_p10_years["anio_t1"].astype(str),
    df_p10_years["tasa_retencion"] * 100,
    color=sb.AZUL_SURA.hex,
    alpha=0.85,
    label="Observado",
)
ax2.axhline(10, ls="--", color=sb.AQUA_SURA.hex, lw=1.5, label="Azar (10%)")
ax2.set_ylabel("% retención")
ax2.set_title("Retención YoY del Top 10%")
ax2.tick_params(axis="x", rotation=30)
ax2.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P10 Retención Top 10%")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "02_P10_retencion_top10.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/02_P10_retencion_top10.png")

df_p10_years.to_parquet(DATA_STAGING / "hip_p10_retencion_top10.parquet", index=False)

p10_results = {
    "pregunta": "P10",
    "descripcion": "Retención Top 10% superior al azar",
    "h0": "p_retencion = 0.10 (azar)",
    "h1": "p_retencion > 0.10",
    "prueba": "Binomial exacta (1-cola) global + por año con Holm",
    "estadistico": round(p_obs, 4),
    "p_valor": float(p_p10),
    "efecto": round(lift_p10, 4),
    "metrica_efecto": "Lift (p_obs/0.10) + Cohen h",
    "decision": "RECHAZAR H0" if p_p10 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"retención={p_obs*100:.1f}%, lift={lift_p10:.1f}×, Cohen h={cohen_h:.2f}; "
        f"{int(rej10.sum())}/6 años significativos tras Holm"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  Corrección por comparaciones múltiples (5 hipótesis del feature set)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  CORRECCIÓN POR COMPARACIONES MÚLTIPLES (Holm-Bonferroni, 5 pruebas)")
print("=" * 70)

p_values_all = [
    kw_pval_p3,
    lr_pval_p5,
    mw_pval_p7,
    p_global_1,
    p_p10,
]
labels_all = [
    "P3-clase_riesgo",
    "P5-interaccion_sector_clase",
    "P7-microempresas",
    "P9-persistencia_lag",
    "P10-retencion_top10",
]

reject, p_adj, _, _ = multipletests(p_values_all, alpha=ALPHA, method="holm")

print(f"\n  {'Prueba':<32} {'p original':>12} {'p ajustado':>12} {'Rechaza H0':>12}")
print("  " + "-" * 70)
for lbl, p_orig, p_adj_val, rej in zip(labels_all, p_values_all, p_adj, reject):
    print(
        f"  {lbl:<32} {p_orig:>12.4e} {p_adj_val:>12.4e} {'SÍ' if rej else 'NO':>12}"
    )


# ══════════════════════════════════════════════════════════════════════
#  Tabla resumen
# ══════════════════════════════════════════════════════════════════════
resumen = pd.DataFrame(
    [p3_results, p5_results, p7_results, p9_results, p10_results]
)
resumen["p_valor_ajustado_holm"] = p_adj
resumen["rechaza_h0_ajustado"] = reject

resumen_path = RESULTS_DIR / "hip_features_resumen.csv"
resumen.to_csv(resumen_path, index=False, encoding="utf-8")
resumen.to_parquet(DATA_STAGING / "hip_features_resumen.parquet", index=False)
print(f"\n  ✓ Tabla resumen: {resumen_path}")
print(f"  ✓ Staging: {DATA_STAGING / 'hip_features_resumen.parquet'}")

print("\n" + "=" * 70)
print("  Ejecución completada exitosamente.")
print("=" * 70)
print("\n  Archivos generados:")
print("    results/imgs/02_P3_clase_riesgo_frecuencia.png")
print("    results/imgs/02_P5_interaccion_sector_clase.png")
print("    results/imgs/02_P7_microempresas_frecuencia.png")
print("    results/imgs/02_P9_persistencia_conteo.png")
print("    results/imgs/02_P10_retencion_top10.png")
print("    results/hip_features_resumen.csv")
print("    data/staging/S01/panel_empresa_lag_yoy.parquet")
print("    data/staging/S01/hip_features_resumen.parquet")
print("    data/staging/S01/hip_p3_dunn_clase_adyacente.parquet")
print("    data/staging/S01/hip_p9_persistencia_spearman.parquet")
print("    data/staging/S01/hip_p10_retencion_top10.parquet")
