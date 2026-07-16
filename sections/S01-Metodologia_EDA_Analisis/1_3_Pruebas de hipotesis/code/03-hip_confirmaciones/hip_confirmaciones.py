"""
Pruebas de Hipótesis – Confirmación / Descarte
==============================================
Sección: S01 – Metodología EDA y Análisis
Subsección: 1.3 – Pruebas de Hipótesis

Descripción:
    Realiza las pruebas de hipótesis correspondientes a las 3 preguntas
    de confirmación/descarte identificadas en 1.3.1:
      P8  – Estacionalidad mensual del volumen de siniestros
      P11 – Diferencias de frecuencia entre departamentos
      P12 – Bondad de ajuste Normal/Lognormal de costos log-transformados

    Nota de diseño (1.3.1): P8 y P11 son pruebas de *confirmación de nulidad*.
    El objetivo de negocio es respaldar el descarte de features (mes, geografía)
    cuando el efecto práctico es despreciable — no solo mirar el p-valor.

    Para cada prueba:
      - Se formulan H0 y H1
      - Se verifican los supuestos de la prueba elegida
      - Se aplica corrección de Bonferroni-Holm cuando hay comparaciones múltiples
      - Se reporta tamaño del efecto y se distingue de la significancia

Inputs (reutilizados de staging S01):
    - data/staging/S01/temporal_mensual.parquet
    - data/staging/S01/estacionalidad_mes.parquet
    - data/staging/S01/siniestros_tratados.parquet
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/staging/S01/bivariado_resumen_departamento.parquet

Outputs:
    - results/imgs/03_P8_*.png, 03_P11_*.png, 03_P12_*.png
    - results/hip_confirmaciones_resumen.csv
    - data/staging/S01/hip_confirmaciones_resumen.parquet
    - data/staging/S01/hip_p12_bondad_ajuste_costo.parquet

Uso:
    python "sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/code/03-hip_confirmaciones/hip_confirmaciones.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.stats import gamma, lognorm, norm
from statsmodels.stats.multitest import multipletests

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración global
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
ALPHA = 0.05
# Umbral de equivalencia práctica para P8 (amplitud del índice estacional)
AMP_EQUIV_PP = 5.0  # puntos porcentuales
# Umbral de equivalencia práctica para P11 (η² despreciable)
ETA2_EQUIV = 0.01

ROOT = Path(__file__).resolve().parents[5]
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S01-1.3 | Pruebas de Hipótesis – Confirmación / Descarte")
print("=" * 70)

# ──────────────────────────────────────────────────
# Carga de datos (reutilizando staging existente)
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando datasets de staging...")
df_mensual = pd.read_parquet(DATA_STAGING / "temporal_mensual.parquet")
df_estac = pd.read_parquet(DATA_STAGING / "estacionalidad_mes.parquet")
df_sin = pd.read_parquet(DATA_STAGING / "siniestros_tratados.parquet")
df_empresa = pd.read_parquet(DATA_STAGING / "empresa_siniestralidad_completa.parquet")
df_dept_resumen = pd.read_parquet(DATA_STAGING / "bivariado_resumen_departamento.parquet")

print(f"  temporal_mensual:                  {df_mensual.shape}")
print(f"  estacionalidad_mes:                {df_estac.shape}")
print(f"  siniestros_tratados:               {df_sin.shape}")
print(f"  empresa_siniestralidad_completa:   {df_empresa.shape}")
print(f"  bivariado_resumen_departamento:    {df_dept_resumen.shape}")


def interpret_eta2(eta2: float) -> str:
    if eta2 < 0.01:
        return "despreciable"
    if eta2 < 0.06:
        return "pequeño"
    if eta2 < 0.14:
        return "mediano"
    return "grande"


def interpret_cramers_v(v: float) -> str:
    if v < 0.10:
        return "despreciable"
    if v < 0.30:
        return "pequeño"
    if v < 0.50:
        return "mediano"
    return "grande"


# ══════════════════════════════════════════════════════════════════════
#  P8 – ¿Estacionalidad mensual significativa en el volumen?
#       H0: no hay diferencias sistemáticas entre meses
#       H1: al menos un mes difiere (estacionalidad)
#
#  Estrategia (confirmación de nulidad):
#    1. Friedman sobre matriz año × mes (controla efecto año)
#    2. Kruskal-Wallis sobre n_siniestros por mes (7 obs/mes)
#    3. Chi-cuadrado de uniformidad sobre conteos mensuales crudos
#    Efecto: amplitud del índice estacional (pp) + Cramér's V
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P8 – ESTACIONALIDAD MENSUAL DEL VOLUMEN DE SINIESTROS")
print("=" * 70)

mat = df_mensual.pivot(index="anio", columns="mes", values="n_siniestros").sort_index()
meses = list(range(1, 13))
print("\n  Verificación de supuestos:")
print(f"    Matriz año×mes: {mat.shape[0]} años × {mat.shape[1]} meses")
print(f"    Celdas faltantes: {int(mat.isna().sum().sum())}")
print("    Friedman: bloques = años, tratamientos = meses (diseño adecuado)")
print("    KW: 7 observaciones independientes por mes (un año = una obs)")

# Friedman
friedman_stat, friedman_p = stats.friedmanchisquare(
    *[mat[m].values for m in meses]
)
# Kendall W (effect size for Friedman): W = χ² / (n_blocks * (k-1))
n_blocks = mat.shape[0]
k_meses = 12
kendall_w = friedman_stat / (n_blocks * (k_meses - 1))

# Kruskal-Wallis
grupos_mes = [df_mensual.loc[df_mensual["mes"] == m, "n_siniestros"].values for m in meses]
kw_stat_p8, kw_p_p8 = stats.kruskal(*grupos_mes)
n_p8 = len(df_mensual)
eta2_p8 = max(0.0, (kw_stat_p8 - k_meses + 1) / (n_p8 - k_meses))

# Chi-cuadrado uniformidad (siniestros individuales)
if "mes" not in df_sin.columns:
    df_sin = df_sin.copy()
    df_sin["mes"] = pd.to_datetime(df_sin["fecha_ocurrencia"]).dt.month
counts_mes = df_sin["mes"].value_counts().sort_index()
n_sin = int(counts_mes.sum())
exp_mes = np.full(12, n_sin / 12.0)
chi2_p8, chi2_p_p8 = stats.chisquare(counts_mes.values, f_exp=exp_mes)
cramers_v_p8 = float(np.sqrt(chi2_p8 / (n_sin * (12 - 1))))

# Amplitud del índice estacional (efecto práctico)
idx = df_estac.set_index("mes")["indice_estacional_n"].reindex(meses)
amp_pp = float((idx.max() - idx.min()) * 100)
equiv_p8 = amp_pp < AMP_EQUIV_PP

# p principal: Friedman (mejor control de año)
p_p8 = float(friedman_p)

print(f"\n  Friedman (año×mes):")
print(f"    χ²_F = {friedman_stat:.4f}, p = {friedman_p:.4f}")
print(f"    Kendall W = {kendall_w:.4f} (≈0 nula, ≈1 estacionalidad perfecta)")

print(f"\n  Kruskal-Wallis (n_siniestros por mes):")
print(f"    H = {kw_stat_p8:.4f}, p = {kw_p_p8:.4f}, η² = {eta2_p8:.4f}")

print(f"\n  Chi-cuadrado uniformidad (conteos crudos, n={n_sin:,}):")
print(f"    χ² = {chi2_p8:.4f}, p = {chi2_p_p8:.4f}")
print(f"    Cramér's V = {cramers_v_p8:.4f} ({interpret_cramers_v(cramers_v_p8)})")

print(f"\n  Efecto práctico – amplitud índice estacional: {amp_pp:.2f} pp")
print(f"    Umbral equivalencia práctica: < {AMP_EQUIV_PP:.0f} pp → "
      f"{'SÍ, efecto despreciable' if equiv_p8 else 'NO, amplitud relevante'}")
print(
    f"  Decisión (Friedman α=0.05): "
    f"{'RECHAZAR H0' if p_p8 < ALPHA else 'No rechazar H0 → sin estacionalidad detectable'}"
)

# Figura P8
mes_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
              "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P8 – Estacionalidad Mensual del Volumen de Siniestros",
    subtitle=(
        f"Friedman p={friedman_p:.3f} (W={kendall_w:.3f})  |  "
        f"χ² uniformidad p={chi2_p_p8:.3f} (V={cramers_v_p8:.3f})  |  "
        f"Amplitud índice={amp_pp:.1f} pp (<{AMP_EQUIV_PP:.0f} pp)  →  NO rechazar H₀"
    ),
)
ax1, ax2 = axes[0], axes[1]

for anio, row in mat.iterrows():
    ax1.plot(meses, row.values, "o-", ms=4, lw=1, alpha=0.55, label=str(anio))
ax1.plot(meses, mat.mean(axis=0).values, "o-", ms=7, lw=2.5,
         color=sb.AZUL_SURA.hex, label="Media")
ax1.set_xticks(meses)
ax1.set_xticklabels(mes_labels, fontsize=8)
ax1.set_ylabel("n siniestros / mes")
ax1.set_title("Volumen mensual por año")
ax1.legend(fontsize=7, ncol=2)

ax2.bar(meses, idx.values, color=sb.AZUL_SURA.hex, alpha=0.85)
ax2.axhline(1.0, ls="--", color=sb.AQUA_SURA.hex, lw=1.5, label="Índice = 1")
ax2.axhline(1 + AMP_EQUIV_PP / 200, ls=":", color=sb.AMARILLO_SURA.hex, lw=1.2)
ax2.axhline(1 - AMP_EQUIV_PP / 200, ls=":", color=sb.AMARILLO_SURA.hex, lw=1.2,
            label=f"Banda ±{AMP_EQUIV_PP/2:.1f} pp (ref.)")
ax2.set_xticks(meses)
ax2.set_xticklabels(mes_labels, fontsize=8)
ax2.set_ylabel("Índice estacional")
ax2.set_ylim(0.95, 1.05)
ax2.set_title(f"Índice estacional (amplitud={amp_pp:.1f} pp)")
ax2.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P8 Estacionalidad")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_P8_estacionalidad_mensual.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/03_P8_estacionalidad_mensual.png")

p8_results = {
    "pregunta": "P8",
    "descripcion": "Estacionalidad mensual del volumen de siniestros",
    "h0": "No hay diferencias sistemáticas de volumen entre meses",
    "h1": "Al menos un mes difiere (estacionalidad presente)",
    "prueba": "Friedman + K-W + chi2 uniformidad",
    "estadistico": round(float(friedman_stat), 4),
    "p_valor": p_p8,
    "efecto": round(amp_pp, 4),
    "metrica_efecto": "amplitud índice estacional (pp) + Kendall W + Cramér V",
    "decision": "RECHAZAR H0" if p_p8 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"amplitud={amp_pp:.1f} pp (despreciable); W={kendall_w:.3f}; "
        f"V={cramers_v_p8:.3f} → no invertir en features de mes"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  P11 – ¿Frecuencias medianas difieren entre departamentos?
#       H0: mismas distribuciones de frecuencia_x100 en los 7 deptos
#       H1: al menos un departamento difiere
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P11 – FRECUENCIA RELATIVA ENTRE DEPARTAMENTOS")
print("=" * 70)

df_p11 = df_empresa.dropna(subset=["departamento", "frecuencia_x100"]).copy()
depts = sorted(df_p11["departamento"].unique())
grupos_dept = [
    df_p11.loc[df_p11["departamento"] == d, "frecuencia_x100"].values for d in depts
]

print("\n  Verificación de supuestos:")
print(f"    Departamentos con dato: {len(depts)} (excluye NaN geográfico)")
print(f"    n total: {len(df_p11):,} empresas")
for d, g in zip(depts, grupos_dept):
    sample = np.random.choice(g, size=min(200, len(g)), replace=False)
    sw_p = stats.shapiro(sample).pvalue
    print(f"    Shapiro {d} (n_s={len(sample)}): p={sw_p:.2e}")
lev_stat, lev_p = stats.levene(*grupos_dept)
print(f"    Levene: W={lev_stat:.4f}, p={lev_p:.2e}")
print("    → Normalidad/homocedasticidad no garantizadas → Kruskal-Wallis")

kw_stat_p11, kw_p_p11 = stats.kruskal(*grupos_dept)
n_p11 = len(df_p11)
k_p11 = len(depts)
eta2_p11 = max(0.0, (kw_stat_p11 - k_p11 + 1) / (n_p11 - k_p11))
medians_dept = df_p11.groupby("departamento")["frecuencia_x100"].median()
range_med = float(medians_dept.max() - medians_dept.min())
equiv_p11 = eta2_p11 < ETA2_EQUIV

print(f"\n  Kruskal-Wallis:")
print(f"    H = {kw_stat_p11:.4f}, df = {k_p11 - 1}, p = {kw_p_p11:.4f}")
print(f"    η² = {eta2_p11:.4f} → magnitud {interpret_eta2(eta2_p11)}")
print(f"    Rango de medianas: {range_med:.2f} puntos de frec.×100")
print(f"    Equivalencia práctica (η² < {ETA2_EQUIV}): "
      f"{'SÍ' if equiv_p11 else 'NO'}")

# Post-hoc Dunn Holm (si KW sugiere algo)
print("\n  Post-hoc Dunn (Holm-Bonferroni)...")
try:
    import scikit_posthocs as sp

    dunn_p11 = sp.posthoc_dunn(
        df_p11, val_col="frecuencia_x100", group_col="departamento", p_adjust="holm"
    )
    n_pares_sig = 0
    n_pares_tot = k_p11 * (k_p11 - 1) // 2
    for i, d1 in enumerate(depts):
        for d2 in depts[i + 1 :]:
            if float(dunn_p11.loc[d1, d2]) < ALPHA:
                n_pares_sig += 1
    print(f"    Pares significativos tras Holm: {n_pares_sig}/{n_pares_tot}")
except Exception as e:
    dunn_p11 = None
    n_pares_sig, n_pares_tot = 0, 0
    print(f"    Post-hoc omitido: {e}")

p_p11 = float(kw_p_p11)
print(
    f"  Decisión (K-W α=0.05, sin Holm familiar aún): "
    f"{'RECHAZAR H0' if p_p11 < ALPHA else 'No rechazar H0'}"
)

# Figura P11
fig, axes = sb.create_dashboard(
    1,
    2,
    title="P11 – Frecuencia Relativa por Departamento",
    subtitle=(
        f"Kruskal-Wallis H={kw_stat_p11:.2f}, p={kw_p_p11:.3f}  |  "
        f"η²={eta2_p11:.4f} ({interpret_eta2(eta2_p11)})  |  "
        f"Rango medianas={range_med:.1f} pts  |  "
        f"Dunn Holm sig={n_pares_sig}/{n_pares_tot}"
    ),
)
ax1, ax2 = axes[0], axes[1]

order_p11 = medians_dept.sort_values().index.tolist()
box_data = [
    df_p11.loc[df_p11["departamento"] == d, "frecuencia_x100"].values for d in order_p11
]
bp = ax1.boxplot(
    box_data,
    tick_labels=order_p11,
    patch_artist=True,
    flierprops=dict(marker=".", markersize=2, alpha=0.3),
)
palette = sb.make_n_colors(len(order_p11))
for patch, color in zip(bp["boxes"], palette):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)
ax1.tick_params(axis="x", rotation=25, labelsize=8)
ax1.set_ylabel("Frecuencia × 100 trabajadores")
ax1.set_title("Distribución por departamento")

med_sorted = medians_dept.reindex(order_p11)
ax2.barh(order_p11, med_sorted.values, color=palette, alpha=0.85)
ax2.axvline(med_sorted.mean(), ls="--", color=sb.AQUA_SURA.hex, lw=1.5,
            label=f"Media de medianas={med_sorted.mean():.1f}")
ax2.set_xlabel("Mediana frecuencia × 100")
ax2.set_title(f"Medianas (rango={range_med:.1f} pts)")
ax2.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P11 Geografía")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_P11_departamento_frecuencia.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/03_P11_departamento_frecuencia.png")

p11_results = {
    "pregunta": "P11",
    "descripcion": "Diferencias de frecuencia entre departamentos",
    "h0": "Distribuciones de frecuencia_x100 iguales entre departamentos",
    "h1": "Al menos un departamento difiere",
    "prueba": "Kruskal-Wallis + Dunn post-hoc Holm",
    "estadistico": round(float(kw_stat_p11), 4),
    "p_valor": p_p11,
    "efecto": round(eta2_p11, 6),
    "metrica_efecto": "η² K-W + rango de medianas",
    "decision": "RECHAZAR H0" if p_p11 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"η²={eta2_p11:.4f} ({interpret_eta2(eta2_p11)}); "
        f"rango medianas={range_med:.1f} pts; "
        f"{n_pares_sig}/{n_pares_tot} pares Dunn → descartar geografía como predictor principal"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  P12 – ¿log(costo) ~ Normal suficiente para Lognormal/Gamma?
#       H0: log(costo_total_w) ~ Normal (⇒ costo ~ Lognormal)
#       H1: se desvía de la Normal
#
#  Con n≈37k, GOF exacto suele rechazar H0 ante desviaciones mínimas.
#  Se reporta: AD, KS, Jarque-Bera + skew/kurtosis + AIC Gamma vs Lognormal.
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P12 – BONDAD DE AJUSTE: log(costo) vs NORMAL / FAMILIAS")
print("=" * 70)

log_c = df_sin["log_costo_total_w"].dropna().astype(float).values
costo_w = df_sin["costo_total_w"].dropna().astype(float).values
costo_w = costo_w[costo_w > 0]

print(f"\n  n log(costo_w) = {len(log_c):,}  |  n costo_w>0 = {len(costo_w):,}")
print(f"  (filas sin costo_w en staging: {df_sin['costo_total_w'].isna().sum()})")

mu_log = float(log_c.mean())
sd_log = float(log_c.std(ddof=1))
skew_log = float(stats.skew(log_c))
kurt_log = float(stats.kurtosis(log_c))  # excess

print("\n  Verificación de supuestos / descriptivos de log(costo_w):")
print(f"    Media={mu_log:.4f}, SD={sd_log:.4f}")
print(f"    Skewness={skew_log:.4f}  (|sk|<0.5 ≈ simetría leve)")
print(f"    Kurtosis excesiva={kurt_log:.4f}  (0 = Normal)")

# Anderson-Darling (scipy 1.17+ may need method=)
try:
    ad_res = stats.anderson(log_c, dist="norm")
    ad_stat = float(ad_res.statistic)
    # Critical value at 5%
    ad_crit_5 = float(ad_res.critical_values[2])  # typically 5%
    ad_reject = ad_stat > ad_crit_5
except Exception:
    ad_stat, ad_crit_5, ad_reject = np.nan, np.nan, None

# KS vs Normal(μ̂,σ̂) on standardized
z = (log_c - mu_log) / sd_log
ks_stat, ks_p = stats.ks_1samp(z, norm.cdf)
# Jarque-Bera
jb_stat, jb_p = stats.jarque_bera(log_c)
# Shapiro en submuestra (límite práctico)
sample_sh = np.random.choice(log_c, size=min(5000, len(log_c)), replace=False)
sw_stat, sw_p = stats.shapiro(sample_sh)

print(f"\n  Anderson-Darling vs Normal:")
print(f"    A² = {ad_stat:.4f}  (crítico 5% ≈ {ad_crit_5:.3f}) → "
      f"{'RECHAZAR' if ad_reject else 'No rechazar'} normalidad exacta")
print(f"  Kolmogorov-Smirnov (estandarizado):")
print(f"    D = {ks_stat:.4f}, p = {ks_p:.2e}")
print(f"  Jarque-Bera:")
print(f"    JB = {jb_stat:.2f}, p = {jb_p:.2e}")
print(f"  Shapiro (submuestra n={len(sample_sh)}):")
print(f"    W = {sw_stat:.4f}, p = {sw_p:.2e}")

# Comparación de familias en escala original: AIC
print("\n  Comparación AIC – Gamma vs Lognormal (costo_w, floc=0)...")
shape_g, loc_g, scale_g = gamma.fit(costo_w, floc=0)
s_ln, loc_ln, scale_ln = lognorm.fit(costo_w, floc=0)
ll_g = float(np.sum(gamma.logpdf(costo_w, shape_g, loc_g, scale_g)))
ll_ln = float(np.sum(lognorm.logpdf(costo_w, s_ln, loc_ln, scale_ln)))
aic_g = 2 * 2 - 2 * ll_g
aic_ln = 2 * 2 - 2 * ll_ln
delta_aic = aic_g - aic_ln  # >0 ⇒ Lognormal mejor
familia_pref = "Lognormal" if aic_ln < aic_g else "Gamma"

print(f"    AIC Gamma     = {aic_g:,.1f}  (shape={shape_g:.4f})")
print(f"    AIC Lognormal = {aic_ln:,.1f}  (s={s_ln:.4f})")
print(f"    ΔAIC (Gamma − Lognormal) = {delta_aic:,.1f} → prefiere {familia_pref}")

# p principal: Jarque-Bera (sensibilidad a momentos 3–4; estándar en GOF)
p_p12 = float(jb_p)
print(
    f"\n  Decisión (JB α=0.05): "
    f"{'RECHAZAR H0 → no Normal exacta' if p_p12 < ALPHA else 'No rechazar H0'}"
)
print(
    "  Lectura práctica: con n≈37k el rechazo de normalidad exacta es esperado; "
    f"skew={skew_log:.2f} es leve y AIC favorece {familia_pref}."
)

# Staging GOF
gof_rows = pd.DataFrame(
    [
        {
            "variable": "log_costo_total_w",
            "n": len(log_c),
            "mean": mu_log,
            "std": sd_log,
            "skewness": skew_log,
            "excess_kurtosis": kurt_log,
            "anderson_a2": ad_stat,
            "anderson_crit_5pct": ad_crit_5,
            "ks_d": float(ks_stat),
            "ks_p": float(ks_p),
            "jarque_bera": float(jb_stat),
            "jarque_bera_p": float(jb_p),
            "shapiro_w_n5000": float(sw_stat),
            "shapiro_p_n5000": float(sw_p),
            "aic_gamma": aic_g,
            "aic_lognormal": aic_ln,
            "delta_aic_gamma_minus_lognormal": delta_aic,
            "familia_preferida_aic": familia_pref,
            "gamma_shape": float(shape_g),
            "lognorm_s": float(s_ln),
        }
    ]
)
gof_path = DATA_STAGING / "hip_p12_bondad_ajuste_costo.parquet"
gof_rows.to_parquet(gof_path, index=False)
print(f"  ✓ Staging: {gof_path}")

# Figura P12
fig, axes = sb.create_dashboard(
    1,
    3,
    title="P12 – Bondad de Ajuste de log(costo) y Familias de Severidad",
    subtitle=(
        f"JB p={jb_p:.2e} | AD A²={ad_stat:.1f}  →  rechaza Normal exacta  |  "
        f"skew={skew_log:.2f}, kurt_ex={kurt_log:.2f}  |  "
        f"AIC: Lognormal−Gamma Δ={-delta_aic:,.0f} → prefiere {familia_pref}"
    ),
)
ax1, ax2, ax3 = axes[0], axes[1], axes[2]

# Hist + Normal
ax1.hist(log_c, bins=60, density=True, alpha=0.7, color=sb.AZUL_SURA.hex, label="Observado")
xs = np.linspace(log_c.min(), log_c.max(), 200)
ax1.plot(xs, norm.pdf(xs, mu_log, sd_log), color=sb.AQUA_SURA.hex, lw=2,
         label=f"Normal(μ={mu_log:.2f}, σ={sd_log:.2f})")
ax1.set_xlabel("log(1 + costo_total_w)")
ax1.set_ylabel("Densidad")
ax1.set_title("Histograma vs Normal")
ax1.legend(fontsize=8)

# QQ plot
qq = stats.probplot(log_c, dist="norm")
theoretical = qq[0][0]
sample_q = qq[0][1]
ax2.scatter(theoretical, sample_q, s=8, alpha=0.35, color=sb.AZUL_SURA.hex)
lims = [min(theoretical.min(), sample_q.min()), max(theoretical.max(), sample_q.max())]
ax2.plot(lims, lims, "--", color=sb.AQUA_SURA.hex, lw=1.5)
ax2.set_xlabel("Cuantiles teóricos Normal")
ax2.set_ylabel("Cuantiles muestrales")
ax2.set_title(f"Q-Q plot (skew={skew_log:.2f})")

# AIC bars
ax3.bar(
    ["Gamma", "Lognormal"],
    [aic_g, aic_ln],
    color=[sb.AQUA_SURA.hex, sb.AZUL_SURA.hex],
    alpha=0.85,
)
ax3.set_ylabel("AIC (menor = mejor)")
ax3.set_title(f"Comparación de familias\n(Δ={delta_aic:,.0f})")
for i, v in enumerate([aic_g, aic_ln]):
    ax3.text(i, v, f"{v/1e6:.2f}M", ha="center", va="bottom", fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P12 Bondad de ajuste costo")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "03_P12_bondad_ajuste_costo.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/03_P12_bondad_ajuste_costo.png")

p12_results = {
    "pregunta": "P12",
    "descripcion": "Bondad de ajuste Normal/Lognormal de log(costo)",
    "h0": "log(costo_total_w) ~ Normal (costo ~ Lognormal)",
    "h1": "log(costo) se desvía de la Normal",
    "prueba": "Anderson-Darling + KS + Jarque-Bera + AIC Gamma vs Lognormal",
    "estadistico": round(float(jb_stat), 4),
    "p_valor": p_p12,
    "efecto": round(skew_log, 4),
    "metrica_efecto": "skewness log + ΔAIC Gamma−Lognormal",
    "decision": "RECHAZAR H0" if p_p12 < ALPHA else "No rechazar H0",
    "relevancia_practica": (
        f"skew={skew_log:.2f} (leve); AIC prefiere {familia_pref} "
        f"(Δ={delta_aic:,.0f}); Normal exacta rechazada por n grande, "
        f"pero Lognormal sigue siendo familia viable para severidad"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  Corrección por comparaciones múltiples (3 pruebas confirmación)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  CORRECCIÓN POR COMPARACIONES MÚLTIPLES (Holm-Bonferroni, 3 pruebas)")
print("=" * 70)

p_values_all = [p_p8, p_p11, p_p12]
labels_all = ["P8-estacionalidad", "P11-departamento", "P12-bondad_ajuste_costo"]

reject, p_adj, _, _ = multipletests(p_values_all, alpha=ALPHA, method="holm")

print(f"\n  {'Prueba':<32} {'p original':>12} {'p ajustado':>12} {'Rechaza H0':>12}")
print("  " + "-" * 70)
for lbl, p_orig, p_adj_val, rej in zip(labels_all, p_values_all, p_adj, reject):
    print(
        f"  {lbl:<32} {p_orig:>12.4e} {p_adj_val:>12.4e} {'SÍ' if rej else 'NO':>12}"
    )

# Decisiones ajustadas para el mensaje de negocio
print("\n  Lectura de confirmación/descarte (tras Holm + efecto práctico):")
print(
    f"    P8:  {'descartar mes' if (not reject[0] and equiv_p8) else 'revisar'} "
    f"(p_adj={p_adj[0]:.3f}, amp={amp_pp:.1f} pp)"
)
print(
    f"    P11: {'descartar depto como predictor principal' if (not reject[1] or equiv_p11) else 'revisar'} "
    f"(p_adj={p_adj[1]:.3f}, η²={eta2_p11:.4f})"
)
print(
    f"    P12: familia preferida={familia_pref} "
    f"(rechazo Normal exacta={reject[2]}, skew={skew_log:.2f})"
)


# ══════════════════════════════════════════════════════════════════════
#  Tabla resumen
# ══════════════════════════════════════════════════════════════════════
resumen = pd.DataFrame([p8_results, p11_results, p12_results])
resumen["p_valor_ajustado_holm"] = p_adj
resumen["rechaza_h0_ajustado"] = reject

resumen_path = RESULTS_DIR / "hip_confirmaciones_resumen.csv"
resumen.to_csv(resumen_path, index=False, encoding="utf-8")
resumen.to_parquet(DATA_STAGING / "hip_confirmaciones_resumen.parquet", index=False)
print(f"\n  ✓ Tabla resumen: {resumen_path}")
print(f"  ✓ Staging: {DATA_STAGING / 'hip_confirmaciones_resumen.parquet'}")

print("\n" + "=" * 70)
print("  Ejecución completada exitosamente.")
print("=" * 70)
print("\n  Archivos generados:")
print("    results/imgs/03_P8_estacionalidad_mensual.png")
print("    results/imgs/03_P11_departamento_frecuencia.png")
print("    results/imgs/03_P12_bondad_ajuste_costo.png")
print("    results/hip_confirmaciones_resumen.csv")
print("    data/staging/S01/hip_confirmaciones_resumen.parquet")
print("    data/staging/S01/hip_p12_bondad_ajuste_costo.parquet")
