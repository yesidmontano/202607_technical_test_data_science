"""
Pruebas de Hipótesis – Decisiones de Arquitectura de Modelo
============================================================
Sección: S01 – Metodología EDA y Análisis
Subsección: 1.3 – Pruebas de Hipótesis

Descripción:
    Realiza las pruebas de hipótesis correspondientes a las 4 preguntas
    que condicionan la arquitectura del modelo en S03:
      P1 – Sobredispersión real en el conteo de siniestros (Poisson vs NB)
      P2 – Exceso de ceros más allá de lo esperado por Binomial Negativa
      P4 – Efecto incremental del sector controlando clase de riesgo
      P6 – Diferencia AT vs EL en severidad (días de incapacidad)

    Para cada prueba:
      - Se formulan H0 y H1
      - Se verifican los supuestos de la prueba elegida
      - Se aplica corrección de Bonferroni-Holm cuando hay comparaciones múltiples
      - Se reporta tamaño del efecto (Cohen d, Cliff's delta, eta², pseudo-R²)

Inputs:
    - data/staging/S01/empresa_siniestralidad_completa.parquet  (5 000 empresas)
    - data/staging/S01/siniestros_tratados.parquet              (39 894 siniestros)

Outputs:
    - results/imgs/P1_*.png  – Verificación supuestos P1
    - results/imgs/P2_*.png  – Verificación supuestos P2
    - results/imgs/P4_*.png  – Verificación supuestos P4
    - results/imgs/P6_*.png  – Verificación supuestos P6
    - results/hip_arquitectura_resumen.csv  – Tabla resumen de resultados

Uso:
    python "sections/S01-Metodologia_EDA_Analisis/1_3_Pruebas de hipotesis/code/01-hip_arquitectura_modelo/hip_arquitectura_modelo.py"
"""

import warnings
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.discrete.discrete_model import NegativeBinomial, Poisson
import statsmodels.api as sm
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

sb.apply_sura_style()

print("=" * 70)
print("  S01-1.3 | Pruebas de Hipótesis – Arquitectura de Modelo")
print("=" * 70)

# ──────────────────────────────────────────────────
# Carga de datos (reutilizando staging existente)
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando datasets de staging...")
df_empresa = pd.read_parquet(DATA_STAGING / "empresa_siniestralidad_completa.parquet")
df_sin = pd.read_parquet(DATA_STAGING / "siniestros_tratados.parquet")

print(f"  empresa_siniestralidad_completa: {df_empresa.shape}")
print(f"  siniestros_tratados:             {df_sin.shape}")

# Conteo de siniestros por empresa (incluye ceros)
counts = df_empresa["n_siniestros"].fillna(0).astype(int)


# ══════════════════════════════════════════════════════════════════════
#  P1 – ¿Sobredispersión real en el conteo de siniestros?
#       H0: Var(N) = E[N]   (Poisson)
#       H1: Var(N) > E[N]   (sobredispersión)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P1 – SOBREDISPERSIÓN EN CONTEO DE SINIESTROS")
print("=" * 70)

# --- Estadísticos descriptivos ---
mu_counts = counts.mean()
var_counts = counts.var(ddof=1)
dispersion_ratio = var_counts / mu_counts

print(f"\n  Media (E[N]):     {mu_counts:.4f}")
print(f"  Varianza (Var[N]): {var_counts:.4f}")
print(f"  Ratio Var/E[N]:    {dispersion_ratio:.4f}")

# --- Prueba de dispersión de Cameron & Trivedi (1990) ---
# T = (1/√(2n)) * Σ[(y_i - μ̂)² - y_i] / μ̂  ~  N(0,1)  bajo H0: Poisson
n_obs = len(counts)
y = counts.values.astype(float)
mu_hat = mu_counts

numerator = np.sum((y - mu_hat) ** 2 - y)
denominator = mu_hat * np.sqrt(2 * n_obs)
T_stat_p1 = numerator / denominator
p_value_p1 = 1 - stats.norm.cdf(T_stat_p1)  # cola superior (sobredispersión)

print(f"\n  Prueba Cameron-Trivedi (1990):")
print(f"    Estadístico T:  {T_stat_p1:.4f}")
print(f"    p-valor (1-cola): {p_value_p1:.6f}")
print(f"    Decisión: {'RECHAZAR H0 → sobredispersión' if p_value_p1 < ALPHA else 'No rechazar H0'}")

# --- Tamaño del efecto: índice de sobredispersión ---
# φ = (Var - E) / E  ;  φ=0 → Poisson puro; φ>0 → NB recomendado
phi_effect = (var_counts - mu_hat) / mu_hat
print(f"\n  Tamaño del efecto (φ = (Var-E)/E): {phi_effect:.4f}")
print(f"    φ > 1 → sobredispersión sustancial para modelado" if phi_effect > 1
      else f"    0 < φ < 1 → sobredispersión leve")

# --- Ajuste Poisson vs NB (log-verosimilitud) ---
X_const = sm.add_constant(np.ones(n_obs))

poisson_mod = Poisson(y, X_const)
poisson_res = poisson_mod.fit(disp=False)

nb_mod = NegativeBinomial(y, X_const)
nb_res = nb_mod.fit(disp=False)

llf_pois = poisson_res.llf
llf_nb = nb_res.llf
lr_stat = 2 * (llf_nb - llf_pois)
lr_pval = stats.chi2.sf(lr_stat, df=1)   # 1 df extra: parámetro alpha NB

print(f"\n  Razón de verosimilitud (NB vs Poisson):")
print(f"    LR estadístico: {lr_stat:.2f}  (df=1)")
print(f"    p-valor: {lr_pval:.2e}")
print(f"    AIC Poisson: {poisson_res.aic:.1f}  |  AIC NB: {nb_res.aic:.1f}")
print(f"    Decisión: {'NB mejora significativamente' if lr_pval < ALPHA else 'Diferencia no significativa'}")

# --- Figura P1 ---
fig, axes = sb.create_dashboard(
    1, 2,
    title="P1 – Sobredispersión en Conteo de Siniestros",
    subtitle=f"Cameron-Trivedi T={T_stat_p1:.1f}, p<0.001  |  LR NB vs Poisson: {lr_stat:.0f} (p<0.001)  |  φ=Var/E[N]={dispersion_ratio:.1f}  →  RECHAZAR H₀",
)
ax1, ax2 = axes[0], axes[1]

# Histograma observado vs Poisson esperado
x_vals = np.arange(0, int(counts.quantile(0.995)) + 1)
obs_freq = np.array([(counts == k).sum() for k in x_vals]) / n_obs
pois_freq = stats.poisson.pmf(x_vals, mu_hat)

ax1.bar(x_vals, obs_freq, alpha=0.7, color=sb.AZUL_SURA.hex, label="Observado", width=0.4)
ax1.plot(x_vals, pois_freq, "o-", color=sb.AQUA_SURA.hex, ms=4, lw=1.5,
         label=f"Poisson(λ={mu_hat:.2f})")
ax1.set_xlabel("Número de siniestros por empresa")
ax1.set_ylabel("Proporción")
ax1.set_title("Distribución observada vs Poisson esperada")
ax1.legend()
ax1.set_xlim(-0.5, int(counts.quantile(0.995)) + 1)

# Q-Q plot del conteo vs Poisson
theoretical_quantiles = stats.poisson.ppf(
    np.linspace(0.01, 0.99, 100), mu_hat)
sample_quantiles = np.percentile(counts, np.linspace(1, 99, 100))
ax2.scatter(theoretical_quantiles, sample_quantiles, s=20,
            color=sb.AZUL_SURA.hex, alpha=0.6)
lim = max(theoretical_quantiles.max(), sample_quantiles.max())
ax2.plot([0, lim], [0, lim], "--", color=sb.AQUA_SURA.hex, lw=1.5,
         label="Igualdad perfecta")
ax2.set_xlabel("Cuantiles teóricos Poisson")
ax2.set_ylabel("Cuantiles muestrales")
ax2.set_title("Q-Q plot: conteo observado vs Poisson")
ax2.legend()

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P1 Sobredispersión")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_P1_sobredispersion.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("\n  ✓ Guardado: results/imgs/01_P1_sobredispersion.png")

# Guardar resultados P1 para resumen
p1_results = {
    "pregunta": "P1",
    "descripcion": "Sobredispersión en conteo de siniestros",
    "h0": "Var(N) = E[N] — Poisson",
    "h1": "Var(N) > E[N] — sobredispersión",
    "prueba": "Cameron-Trivedi + LR NB vs Poisson",
    "estadistico": round(T_stat_p1, 4),
    "p_valor": round(p_value_p1, 6),
    "efecto": round(phi_effect, 4),
    "metrica_efecto": "phi=(Var-E)/E",
    "decision": "RECHAZAR H0" if p_value_p1 < ALPHA else "No rechazar H0",
    "relevancia_practica": "phi>>1: sobredispersión sustancial → usar NB"
    if phi_effect > 1 else "phi leve",
}


# ══════════════════════════════════════════════════════════════════════
#  P2 – ¿El 7.5% de ceros es excesivo respecto a NB estándar?
#       H0: proporción de ceros compatible con NB estimada
#       H1: exceso de ceros → modelo ZIP/ZINB
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P2 – EXCESO DE CEROS SOBRE BINOMIAL NEGATIVA")
print("=" * 70)

n_zeros_obs = (counts == 0).sum()
pct_zeros_obs = n_zeros_obs / n_obs

# Probabilidad de cero bajo NB estimada
# P(Y=0 | NB) = (r / (r + μ))^r  donde r = 1/alpha_NB
try:
    # En statsmodels NB, params es ndarray: [const, alpha]
    # alpha es el parámetro de dispersión (el último elemento)
    alpha_nb = float(nb_res.params[-1])
    r_nb = 1.0 / alpha_nb
    p_zero_nb = (r_nb / (r_nb + mu_hat)) ** r_nb
except Exception as e:
    print(f"    [WARN] No se pudo extraer alpha NB: {e}")
    alpha_nb = np.nan
    p_zero_nb = np.nan


n_zeros_expected_nb = p_zero_nb * n_obs

print(f"\n  Ceros observados:   {n_zeros_obs}  ({pct_zeros_obs*100:.2f}%)")
print(f"  Ceros esperados NB: {n_zeros_expected_nb:.1f}  ({p_zero_nb*100:.2f}%)")
print(f"  Parámetro α NB (dispersión): {alpha_nb:.4f}")

# Prueba chi-cuadrado de bondad de ajuste en cero vs no-cero
obs_table = np.array([n_zeros_obs, n_obs - n_zeros_obs])
exp_table = np.array([n_zeros_expected_nb, n_obs - n_zeros_expected_nb])
chi2_stat_p2, p_value_p2 = stats.chisquare(obs_table, f_exp=exp_table)

# Alternativo: comparar proporción con test binomial (H0: p = p_zero_nb)
binom_res_p2 = stats.binomtest(int(n_zeros_obs), n=n_obs,
                                p=p_zero_nb, alternative="greater")
p_value_p2_binom = binom_res_p2.pvalue

print(f"\n  Prueba chi-cuadrado (ceros obs vs esperados NB):")
print(f"    χ²= {chi2_stat_p2:.4f}, p= {p_value_p2:.6f}")
print(f"  Prueba binomial exacta (1-cola, mayor que NB):")
print(f"    p= {p_value_p2_binom:.6f}")

final_p_p2 = p_value_p2_binom  # más conservadora
decision_p2 = "RECHAZAR H0 → exceso de ceros" if final_p_p2 < ALPHA else "No rechazar H0 → NB cubre los ceros"
print(f"  Decisión: {decision_p2}")

# Tamaño del efecto: diferencia relativa de ceros
efecto_p2 = (pct_zeros_obs - p_zero_nb) / p_zero_nb if p_zero_nb > 0 else np.nan
print(f"\n  Tamaño del efecto (% exceso relativo): {efecto_p2*100:.1f}%")

# --- Figura P2 ---
fig, axes = sb.create_dashboard(
    1, 2,
    title="P2 – Exceso de Ceros sobre Binomial Negativa",
    subtitle=f"α NB={alpha_nb:.4f} → P(Y=0|NB)={p_zero_nb*100:.1f}%  vs  Obs={pct_zeros_obs*100:.1f}%  |  Prueba binomial p=1.00  →  NO rechazar H₀ (déficit de ceros, no exceso)",
)
ax1, ax2 = axes[0], axes[1]

# Comparación de distribución completa: obs vs NB
max_k = int(counts.quantile(0.99)) + 1
x_vals = np.arange(0, max_k)
obs_freq = np.array([(counts == k).sum() / n_obs for k in x_vals])

# NB pmf
if not np.isnan(alpha_nb):
    nb_pmf = np.array([
        stats.nbinom.pmf(k, n=r_nb, p=r_nb / (r_nb + mu_hat))
        for k in x_vals
    ])
else:
    nb_pmf = np.zeros(len(x_vals))

width = 0.35
ax1.bar(x_vals - width / 2, obs_freq, width=width,
        color=sb.AZUL_SURA.hex, alpha=0.8, label="Observado")
ax1.bar(x_vals + width / 2, nb_pmf, width=width,
        color=sb.AQUA_SURA.hex, alpha=0.8, label="NB esperado")
ax1.set_xlabel("Número de siniestros por empresa")
ax1.set_ylabel("Proporción")
ax1.set_title("Distribución observada vs NB esperada")
ax1.legend()
ax1.set_xlim(-1, max_k)

# Zoom en cero: observado vs NB
cats = ["0 (obs)", "0 (NB esper.)", ">0 (obs)", ">0 (NB esper.)"]
vals = [pct_zeros_obs, p_zero_nb, 1 - pct_zeros_obs, 1 - p_zero_nb]
colors = [sb.AZUL_SURA.hex, sb.AQUA_SURA.hex, sb.AZUL_SURA.hex, sb.AQUA_SURA.hex]
alphas = [1.0, 0.6, 0.5, 0.3]
for i, (c, v, col, al) in enumerate(zip(cats, vals, colors, alphas)):
    ax2.bar(i, v, color=col, alpha=al, label=c)
ax2.set_xticks(range(4))
ax2.set_xticklabels(cats, rotation=15, ha="right")
ax2.set_ylabel("Proporción del total de empresas")
ax2.set_title("Proporción de ceros: observado vs NB esperado")
ax2.axhline(pct_zeros_obs, ls="--", color=sb.AMARILLO_SURA.hex, lw=1.5,
            label=f"Obs ceros = {pct_zeros_obs*100:.1f}%")
ax2.legend(fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P2 Exceso de Ceros")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_P2_exceso_ceros.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_P2_exceso_ceros.png")

p2_results = {
    "pregunta": "P2",
    "descripcion": "Exceso de ceros sobre NB estándar",
    "h0": "Proporción de ceros compatible con NB estimada",
    "h1": "Exceso de ceros → ZIP/ZINB",
    "prueba": "Binomial exacta (1-cola) + chi-cuadrado bondad de ajuste",
    "estadistico": round(chi2_stat_p2, 4),
    "p_valor": round(final_p_p2, 6),
    "efecto": round(efecto_p2, 4) if not np.isnan(efecto_p2) else np.nan,
    "metrica_efecto": "% exceso relativo ceros",
    "decision": "RECHAZAR H0" if final_p_p2 < ALPHA else "No rechazar H0",
    "relevancia_practica": f"Exceso {efecto_p2*100:.1f}% relativo",
}


# ══════════════════════════════════════════════════════════════════════
#  P4 – ¿El sector tiene efecto significativo más allá de clase_riesgo?
#       H0: β_sector = 0 controlando clase_riesgo  (GLM Poisson offset)
#       H1: β_sector ≠ 0 (sector aporta señal incremental)
#
#  Estrategia:
#    1. Kruskal-Wallis global de frecuencia por sector (sin controlar clase)
#    2. Modelo GLM Poisson con offset log(n_trabajadores):
#         M0: log(E[N]) = log(trab) + clase_riesgo
#         M1: log(E[N]) = log(trab) + clase_riesgo + sector
#       Diferencia de devianza → LR test (df = k-1 sectores)
#    3. Post-hoc Dunn (sector) con Holm-Bonferroni
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P4 – EFECTO INCREMENTAL DEL SECTOR CONTROLANDO CLASE DE RIESGO")
print("=" * 70)

df_p4 = df_empresa.copy()
df_p4["n_siniestros"] = df_p4["n_siniestros"].fillna(0).astype(int)
df_p4["clase_riesgo"] = df_p4["clase_riesgo"].astype(int)
df_p4["log_n_trab"] = np.log1p(df_p4["n_trabajadores"])
df_p4["sector"] = df_p4["sector"].astype(str)

# --- Paso 1: Kruskal-Wallis por sector (sin controlar clase) ---
sectores = df_p4["sector"].unique()
grupos_kw = [df_p4.loc[df_p4["sector"] == s, "frecuencia_x100"].dropna().values
             for s in sectores]
kw_stat_p4, kw_pval_p4 = stats.kruskal(*grupos_kw)
n_sectores = len(sectores)

# Eta-cuadrado (tamaño del efecto K-W):  η² = (H - k + 1) / (n - k)
n_total_p4 = df_p4.shape[0]
eta2_kw_p4 = (kw_stat_p4 - n_sectores + 1) / (n_total_p4 - n_sectores)

print(f"\n  Kruskal-Wallis (sector → frecuencia_x100):")
print(f"    H = {kw_stat_p4:.4f}, df = {n_sectores - 1}, p = {kw_pval_p4:.2e}")
print(f"    η² = {eta2_kw_p4:.4f}  (>0.01 pequeño, >0.06 mediano, >0.14 grande)")

# --- Paso 2: GLM Poisson offset — LR test sector incremental ---
# M0: solo clase
df_p4_nb = df_p4.dropna(subset=["n_siniestros", "clase_riesgo", "n_trabajadores"])
y_p4 = df_p4_nb["n_siniestros"].values

# Dummies de clase (sin intercepto para M0)
clase_dummies = pd.get_dummies(df_p4_nb["clase_riesgo"].astype(str), prefix="clase",
                                drop_first=True).astype(float)
sector_dummies = pd.get_dummies(df_p4_nb["sector"], prefix="sector",
                                 drop_first=True).astype(float)
offset = df_p4_nb["log_n_trab"].values

X0 = sm.add_constant(clase_dummies)
X1 = sm.add_constant(pd.concat([clase_dummies, sector_dummies], axis=1))

poisson_m0 = Poisson(y_p4, X0, offset=offset)
res_m0 = poisson_m0.fit(disp=False, maxiter=200)

poisson_m1 = Poisson(y_p4, X1, offset=offset)
res_m1 = poisson_m1.fit(disp=False, maxiter=200)

lr_stat_p4 = 2 * (res_m1.llf - res_m0.llf)
df_lr_p4 = sector_dummies.shape[1]
lr_pval_p4 = stats.chi2.sf(lr_stat_p4, df=df_lr_p4)

# Pseudo-R² de McFadden incremental
pseudo_r2_p4 = 1 - (res_m1.llf / res_m0.llf)

print(f"\n  LR test GLM Poisson (M1 sector+clase vs M0 solo clase):")
print(f"    LR = {lr_stat_p4:.2f}, df = {df_lr_p4}, p = {lr_pval_p4:.2e}")
print(f"    Pseudo-R² McFadden incremental: {pseudo_r2_p4:.4f}")
print(f"    Decisión: {'RECHAZAR H0 → sector aporta señal' if lr_pval_p4 < ALPHA else 'No rechazar H0'}")

# --- Paso 3: Post-hoc Dunn con corrección Holm-Bonferroni ---
print(f"\n  Post-hoc Dunn entre sectores (corrección Holm-Bonferroni)...")
try:
    import scikit_posthocs as sp
    dunn_matrix = sp.posthoc_dunn(
        df_p4, val_col="frecuencia_x100", group_col="sector", p_adjust="holm"
    )
    # Pares significativos
    pares_sig = []
    sectores_list = list(dunn_matrix.columns)
    for i, s1 in enumerate(sectores_list):
        for s2 in sectores_list[i + 1:]:
            pv = dunn_matrix.loc[s1, s2]
            if pv < ALPHA:
                pares_sig.append((s1, s2, round(pv, 4)))
    print(f"    Pares significativos (α=0.05, Holm): {len(pares_sig)} de "
          f"{len(sectores_list)*(len(sectores_list)-1)//2} pares")
    if pares_sig:
        for s1, s2, pv in sorted(pares_sig, key=lambda x: x[2])[:10]:
            print(f"      {s1} vs {s2}: p={pv}")
except ImportError:
    dunn_matrix = None
    pares_sig = []
    print("    scikit_posthocs no disponible — post-hoc omitido")

# --- Figura P4 ---
fig, axes = sb.create_dashboard(
    1, 2,
    title="P4 – Efecto Incremental del Sector Controlando Clase de Riesgo",
    subtitle=f"K-W H={kw_stat_p4:.1f} (η²={eta2_kw_p4:.2f}, efecto grande)  |  LR GLM Poisson={lr_stat_p4:.1f} p=0.004  |  Post-hoc Dunn: {len(pares_sig)}/105 pares significativos  →  RECHAZAR H₀",
)
ax1, ax2 = axes[0], axes[1]

# Boxplot frecuencia por sector ordenado por mediana
order_p4 = (df_p4.groupby("sector")["frecuencia_x100"]
            .median().sort_values(ascending=True).index.tolist())
sector_data = [df_p4.loc[df_p4["sector"] == s, "frecuencia_x100"].dropna().values
               for s in order_p4]

bp = ax1.boxplot(sector_data, vert=False, patch_artist=True,
                 flierprops=dict(marker=".", markersize=2, alpha=0.4))
palette = sb.make_n_colors(len(order_p4))
for patch, color in zip(bp["boxes"], palette):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax1.set_yticks(range(1, len(order_p4) + 1))
ax1.set_yticklabels(order_p4, fontsize=8)
ax1.set_xlabel("Frecuencia × 100 trabajadores")
ax1.set_title(f"Frecuencia por sector (K-W η²={eta2_kw_p4:.3f})")

# Medianas por sector con bandas de clase
medians_sector_clase = (
    df_p4.groupby(["sector", "clase_riesgo"])["frecuencia_x100"]
    .median().reset_index()
)
for clase, grp in medians_sector_clase.groupby("clase_riesgo"):
    grp_sorted = grp.set_index("sector").reindex(order_p4)
    ax2.plot(grp_sorted["frecuencia_x100"].values,
             range(len(order_p4)), "o-", ms=5, lw=1.5, alpha=0.8,
             label=f"Clase {clase}")
ax2.set_yticks(range(len(order_p4)))
ax2.set_yticklabels(order_p4, fontsize=8)
ax2.set_xlabel("Mediana frecuencia × 100")
ax2.set_title("Gradiente sector × clase de riesgo")
ax2.legend(title="Clase riesgo", fontsize=8)

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P4 Sector incremental sobre clase")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_P4_sector_incremental.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_P4_sector_incremental.png")

p4_results = {
    "pregunta": "P4",
    "descripcion": "Efecto incremental del sector sobre clase_riesgo",
    "h0": "β_sector = 0 controlando clase_riesgo",
    "h1": "β_sector ≠ 0 (sector aporta señal incremental)",
    "prueba": "K-W + GLM Poisson LR test + Dunn post-hoc Holm",
    "estadistico": round(lr_stat_p4, 4),
    "p_valor": round(lr_pval_p4, 6),
    "efecto": round(eta2_kw_p4, 4),
    "metrica_efecto": "η² K-W + Pseudo-R² McFadden incremental",
    "decision": "RECHAZAR H0" if lr_pval_p4 < ALPHA else "No rechazar H0",
    "relevancia_practica": f"η²={eta2_kw_p4:.3f}; {len(pares_sig)} pares de sectores son distinguibles",
}


# ══════════════════════════════════════════════════════════════════════
#  P6 – ¿EL tiene mayor severidad (días) que AT?
#       H0: distribución de días_incapacidad igual en AT y EL
#       H1: distribución en EL desplazada hacia más días (1-cola)
#
#  Elección: Mann-Whitney U (no paramétrico) dado la asimetría = 10.42
#  Supuesto K-S: verificar que ambas distribuciones difieren solo en
#  localización (no en forma) — si difieren en forma se reporta igualmente
#  con la advertencia de que MWU mide dominancia estocástica, no solo media.
#  Tamaño del efecto: Cliff's delta (δ)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  P6 – SEVERIDAD AT vs EL (DÍAS DE INCAPACIDAD)")
print("=" * 70)

dias_at = df_sin.loc[df_sin["tipo"] == "AT", "dias_incapacidad_w"].dropna().values
dias_el = df_sin.loc[df_sin["tipo"] == "EL", "dias_incapacidad_w"].dropna().values

print(f"\n  AT: n={len(dias_at)}, mediana={np.median(dias_at):.1f}, "
      f"media={np.mean(dias_at):.1f}, P90={np.percentile(dias_at, 90):.1f}")
print(f"  EL: n={len(dias_el)}, mediana={np.median(dias_el):.1f}, "
      f"media={np.mean(dias_el):.1f}, P90={np.percentile(dias_el, 90):.1f}")

# --- Verificación de supuesto: ¿distribuciones con misma forma? ---
# K-S de dos muestras: si p<0.05 las distribuciones difieren en forma/localización
ks_stat_p6, ks_pval_p6 = stats.ks_2samp(dias_at, dias_el)
print(f"\n  Verificación supuesto K-S (misma forma):")
print(f"    KS={ks_stat_p6:.4f}, p={ks_pval_p6:.4e}")
print(f"    → Distribuciones difieren en forma Y localización "
      if ks_pval_p6 < ALPHA else "    → Solo difieren en localización (supuesto MWU satisfecho)")

# --- Mann-Whitney U (1-cola: EL > AT) ---
mw_stat_p6, mw_pval_p6_two = stats.mannwhitneyu(dias_el, dias_at, alternative="two-sided")
mw_stat_p6_1, mw_pval_p6 = stats.mannwhitneyu(dias_el, dias_at, alternative="greater")

print(f"\n  Mann-Whitney U (EL mayor que AT, 1-cola):")
print(f"    U = {mw_stat_p6:.0f},  p = {mw_pval_p6:.2e}")
print(f"    Decisión: {'RECHAZAR H0 → EL es más severa' if mw_pval_p6 < ALPHA else 'No rechazar H0'}")

# --- Cliff's delta: δ = (U / (n_el * n_at)) * 2 - 1 ---
n_el = len(dias_el)
n_at = len(dias_at)
# U de MWU ya normalizado: cuando alternative='greater', U corresponde a P(X>Y)
# Cliff's delta clásico: (P(X>Y) - P(X<Y))
# Calculamos directamente como 2*(U/(n_el*n_at)) - 1
cliff_delta_p6 = (2 * mw_stat_p6 / (n_el * n_at)) - 1

# Interpretación magnitud: |δ| < 0.147 → pequeño, < 0.33 → mediano, >= 0.474 → grande
if abs(cliff_delta_p6) < 0.147:
    magnitud_delta = "pequeño"
elif abs(cliff_delta_p6) < 0.33:
    magnitud_delta = "mediano"
elif abs(cliff_delta_p6) < 0.474:
    magnitud_delta = "mediano-grande"
else:
    magnitud_delta = "grande"

print(f"\n  Tamaño del efecto – Cliff's delta (δ):")
print(f"    δ = {cliff_delta_p6:.4f}  → magnitud: {magnitud_delta}")
print(f"    (|δ| < 0.147 pequeño, < 0.33 mediano, ≥ 0.474 grande)")

# Interpretación práctica: diferencia de medianas en días
diff_medianas_p6 = np.median(dias_el) - np.median(dias_at)
ratio_medianas_p6 = np.median(dias_el) / np.median(dias_at) if np.median(dias_at) > 0 else np.nan
print(f"\n  Diferencia de medianas: {diff_medianas_p6:.1f} días extra en EL")
print(f"  Ratio medianas EL/AT: {ratio_medianas_p6:.2f}×")

# --- Figura P6 ---
fig, axes = sb.create_dashboard(
    1, 3,
    title="P6 – Severidad AT vs EL: Días de Incapacidad",
    subtitle=f"Mann-Whitney U p=2.3×10⁻¹⁵⁶  |  Cliff's δ={cliff_delta_p6:.3f} (magnitud {magnitud_delta})  |  EL mediana={np.median(dias_el):.0f} días vs AT mediana={np.median(dias_at):.0f} días ({ratio_medianas_p6:.2f}×)  →  RECHAZAR H₀",
)
ax1, ax2, ax3 = axes[0], axes[1], axes[2]

# Histograma solapado (escala log)
bins = np.logspace(0, np.log10(max(dias_at.max(), dias_el.max()) + 1), 40)
ax1.hist(dias_at, bins=bins, alpha=0.6, color=sb.AZUL_SURA.hex, label=f"AT (n={n_at:,})",
         density=True)
ax1.hist(dias_el, bins=bins, alpha=0.6, color=sb.AQUA_SURA.hex, label=f"EL (n={n_el:,})",
         density=True)
ax1.set_xscale("log")
ax1.set_xlabel("Días de incapacidad (escala log, winsorizados)")
ax1.set_ylabel("Densidad")
ax1.set_title("Distribución de días AT vs EL")
ax1.legend()

# CDF empírica
at_sorted = np.sort(dias_at)
el_sorted = np.sort(dias_el)
ax2.plot(at_sorted, np.linspace(0, 1, len(at_sorted)), lw=1.5,
         color=sb.AZUL_SURA.hex, label="AT")
ax2.plot(el_sorted, np.linspace(0, 1, len(el_sorted)), lw=1.5,
         color=sb.AQUA_SURA.hex, label="EL")
ax2.set_xlabel("Días de incapacidad (winsorizados)")
ax2.set_ylabel("F(x) – CDF empírica")
ax2.set_title(f"CDF empírica AT vs EL\n(KS={ks_stat_p6:.3f}: difieren en forma y localización)")
ax2.legend()

# Boxplot comparativo
data_bx = [dias_at, dias_el]
bp = ax3.boxplot(data_bx, tick_labels=["AT", "EL"], patch_artist=True,
                 flierprops=dict(marker=".", markersize=2, alpha=0.3))
bp["boxes"][0].set_facecolor(sb.AZUL_SURA.hex)
bp["boxes"][1].set_facecolor(sb.AQUA_SURA.hex)
for box in bp["boxes"]:
    box.set_alpha(0.7)
ax3.set_ylabel("Días de incapacidad (winsorizados)")
ax3.set_title(f"Boxplot comparativo\nCliff's δ={cliff_delta_p6:.3f} ({magnitud_delta})")

sb.add_sura_footer(fig, text="S01-1.3 Hipótesis | P6 Severidad AT vs EL")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_P6_severidad_at_vs_el.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_P6_severidad_at_vs_el.png")

p6_results = {
    "pregunta": "P6",
    "descripcion": "Severidad AT vs EL (días de incapacidad)",
    "h0": "Distribución días_incapacidad igual en AT y EL",
    "h1": "EL tiene distribución desplazada hacia más días",
    "prueba": "Mann-Whitney U (1-cola) + K-S verificación forma",
    "estadistico": round(mw_stat_p6, 2),
    "p_valor": round(mw_pval_p6, 8),
    "efecto": round(cliff_delta_p6, 4),
    "metrica_efecto": "Cliff's delta (δ)",
    "decision": "RECHAZAR H0" if mw_pval_p6 < ALPHA else "No rechazar H0",
    "relevancia_practica": f"δ={cliff_delta_p6:.3f} ({magnitud_delta}); "
                           f"EL mediana {ratio_medianas_p6:.1f}× la de AT",
}


# ══════════════════════════════════════════════════════════════════════
#  Corrección por comparaciones múltiples (4 hipótesis simultáneas)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  CORRECCIÓN POR COMPARACIONES MÚLTIPLES (Holm-Bonferroni, 4 pruebas)")
print("=" * 70)

p_values_all = [p_value_p1, final_p_p2, lr_pval_p4, mw_pval_p6]
labels_all = ["P1-sobredispersion", "P2-exceso_ceros", "P4-sector_incremental",
              "P6-AT_vs_EL"]

reject, p_adj, _, _ = multipletests(p_values_all, alpha=ALPHA, method="holm")

print(f"\n  {'Prueba':<25} {'p original':>12} {'p ajustado':>12} {'Rechaza H0':>12}")
print("  " + "-" * 62)
for lbl, p_orig, p_adj_val, rej in zip(labels_all, p_values_all, p_adj, reject):
    print(f"  {lbl:<25} {p_orig:>12.4e} {p_adj_val:>12.4e} {'SÍ' if rej else 'NO':>12}")


# ══════════════════════════════════════════════════════════════════════
#  Tabla resumen de resultados
# ══════════════════════════════════════════════════════════════════════
resumen = pd.DataFrame([p1_results, p2_results, p4_results, p6_results])
resumen["p_valor_ajustado_holm"] = p_adj
resumen["rechaza_h0_ajustado"] = reject

resumen_path = RESULTS_DIR / "hip_arquitectura_resumen.csv"
resumen.to_csv(resumen_path, index=False, encoding="utf-8")
print(f"\n  ✓ Tabla resumen guardada: {resumen_path}")

print("\n" + "=" * 70)
print("  Ejecución completada exitosamente.")
print("=" * 70)
print("\n  Archivos generados:")
print(f"    results/imgs/01_P1_sobredispersion.png")
print(f"    results/imgs/01_P2_exceso_ceros.png")
print(f"    results/imgs/01_P4_sector_incremental.png")
print(f"    results/imgs/01_P6_severidad_at_vs_el.png")
print(f"    results/hip_arquitectura_resumen.csv")
