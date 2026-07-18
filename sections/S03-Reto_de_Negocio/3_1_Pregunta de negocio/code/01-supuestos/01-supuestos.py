"""
Validación de supuestos – Pregunta de negocio
=============================================
Sección: S03 – Reto de Negocio
Subsección: 3.1 – Pregunta de negocio
Proceso: 3.1.1 / 3.1.2 – Validación de supuestos

Descripción:
    Valida empíricamente los tres supuestos enunciados en 3.1.1:

      S1 – Independencia (o débil dependencia) frecuencia–severidad
           → correlación Spearman/Pearson a nivel empresa y panel anual;
             si la dependencia es material, el modelo de S03 debe condicionar
             severidad (o costo medio) a la frecuencia / segmento.

      S2 – Estabilidad del portafolio (mix sector / clase / tamaño)
           → comparación de shares de empresas, siniestros y costo por año;
             distancia Jensen–Shannon (JS) YoY y vs. año más reciente.

      S3 – La prima refleja el riesgo (prima vs. costo esperado histórico)
           → loss ratio (costo anual medio / prima) por segmento
             clase_riesgo × sector × tamaño; flag de insuficiencia (LR > 1).

Inputs (reutilizados — no se regeneran):
    - data/staging/S01/empresa_siniestralidad_completa.parquet
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S01/siniestros_imputados.parquet   (trazabilidad)

Outputs:
    - results/imgs/01_S1_*.png … 01_S3_*.png
    - results/supuestos_*.csv                         (espejo de staging)
    - data/staging/S03/supuestos_freq_sev_empresa.parquet
    - data/staging/S03/supuestos_freq_sev_correlacion.parquet
    - data/staging/S03/supuestos_mix_anual.parquet
    - data/staging/S03/supuestos_mix_estabilidad.parquet
    - data/staging/S03/supuestos_prima_vs_costo_segmento.parquet
    - data/staging/S03/supuestos_prima_vs_costo_empresa.parquet
    - data/staging/S03/supuestos_veredicto.parquet

Uso:
    .venv/bin/python "sections/S03-Reto_de_Negocio/3_1_Pregunta de negocio/code/01-supuestos/01-supuestos.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.spatial.distance import jensenshannon

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
ALPHA = 0.05
# Umbrales de interpretación (documentados en veredicto)
RHO_DEBIL = 0.20          # |ρ| < 0.20 → dependencia débil / independencia práctica
RHO_MODERADO = 0.40       # 0.20–0.40 moderada; ≥0.40 material
JS_ESTABLE = 0.10         # JS (base 2) media YoY < 0.10 → mix estable
LR_INSUFICIENTE = 1.0     # Loss ratio > 1 → prima no cubre costo histórico

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
print("  S03-3.1.2 | Validación de supuestos – Pregunta de negocio")
print("=" * 70)

# ──────────────────────────────────────────────────
# Carga
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando staging S01...")
emp = pd.read_parquet(DATA_S01 / "empresa_siniestralidad_completa.parquet")
panel = pd.read_parquet(DATA_S01 / "temporal_empresa_anio.parquet")
sin = pd.read_parquet(DATA_S01 / "siniestros_imputados.parquet")

print(f"  empresa_siniestralidad_completa: {emp.shape}")
print(f"  temporal_empresa_anio:           {panel.shape}")
print(f"  siniestros_imputados:            {sin.shape}")

# Atributos de tamaño / prima al panel anual
panel = panel.merge(
    emp[["id_empresa", "segmento", "prima_anual"]],
    on="id_empresa",
    how="left",
)

# Tipos categóricos ordenados
SEG_ORDER = ["Micro (≤10)", "Pequeña (11-50)", "Mediana (51-200)", "Grande (>200)"]
panel["segmento"] = pd.Categorical(panel["segmento"], categories=SEG_ORDER, ordered=True)
emp["segmento"] = pd.Categorical(emp["segmento"], categories=SEG_ORDER, ordered=True)
emp["clase_riesgo"] = emp["clase_riesgo"].astype(int)
panel["clase_riesgo"] = panel["clase_riesgo"].astype(int)

anios = sorted(panel["anio"].unique())
anio_ref = max(anios)


# ══════════════════════════════════════════════════════════════════════
#  S1 – Independencia frecuencia–severidad
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  S1 – INDEPENDENCIA FRECUENCIA–SEVERIDAD")
print("=" * 70)

# --- Nivel empresa (acumulado; solo con siniestros para severidad) ---
emp_pos = emp.loc[emp["n_siniestros"] > 0].copy()

pares_empresa = [
    ("n_siniestros", "severidad_media"),
    ("frecuencia_x100", "severidad_media"),
    ("n_siniestros", "costo_medio_siniestro"),
    ("frecuencia_x100", "costo_medio_siniestro"),
]

# --- Nivel panel anual ---
panel_pos = panel.loc[panel["n_siniestros"] > 0].copy()
pares_panel = [
    ("n_siniestros", "severidad_media"),
    ("frecuencia_x100", "severidad_media"),
]


def _corr_row(df: pd.DataFrame, x: str, y: str, nivel: str, estrato: str = "global") -> dict:
    sub = df[[x, y]].dropna()
    n = len(sub)
    if n < 10:
        return {
            "nivel": nivel, "estrato": estrato, "x": x, "y": y, "n": n,
            "spearman_rho": np.nan, "spearman_p": np.nan,
            "pearson_r": np.nan, "pearson_p": np.nan,
            "dependencia": "insuficiente_n",
        }
    rho, p_sp = stats.spearmanr(sub[x], sub[y])
    r, p_pe = stats.pearsonr(sub[x], sub[y])
    abs_rho = abs(float(rho))
    if abs_rho < RHO_DEBIL:
        dep = "independencia_practica"
    elif abs_rho < RHO_MODERADO:
        dep = "dependencia_debil_moderada"
    else:
        dep = "dependencia_material"
    return {
        "nivel": nivel,
        "estrato": estrato,
        "x": x,
        "y": y,
        "n": n,
        "spearman_rho": round(float(rho), 4),
        "spearman_p": float(p_sp),
        "pearson_r": round(float(r), 4),
        "pearson_p": float(p_pe),
        "dependencia": dep,
    }


corr_rows: list[dict] = []
for x, y in pares_empresa:
    corr_rows.append(_corr_row(emp_pos, x, y, nivel="empresa_acumulado"))
for x, y in pares_panel:
    corr_rows.append(_corr_row(panel_pos, x, y, nivel="panel_anual"))

# Correlación por clase de riesgo (empresa)
for clase, g in emp_pos.groupby("clase_riesgo"):
    corr_rows.append(
        _corr_row(g, "frecuencia_x100", "severidad_media",
                  nivel="empresa_acumulado", estrato=f"clase_{clase}")
    )
    corr_rows.append(
        _corr_row(g, "frecuencia_x100", "costo_medio_siniestro",
                  nivel="empresa_acumulado", estrato=f"clase_{clase}")
    )

# Correlación por segmento de tamaño
for seg, g in emp_pos.groupby("segmento", observed=True):
    corr_rows.append(
        _corr_row(g, "frecuencia_x100", "severidad_media",
                  nivel="empresa_acumulado", estrato=f"segmento_{seg}")
    )

df_corr = pd.DataFrame(corr_rows)

# Dataset empresa para reuso (freq + sev + costo medio)
df_freq_sev = emp_pos[[
    "id_empresa", "clase_riesgo", "sector", "segmento", "n_trabajadores",
    "n_siniestros", "frecuencia_x100", "severidad_media",
    "costo_medio_siniestro", "costo_total_empresa", "prima_anual",
]].copy()
df_freq_sev["log_frecuencia_x100"] = np.log1p(df_freq_sev["frecuencia_x100"])
df_freq_sev["log_severidad_media"] = np.log1p(df_freq_sev["severidad_media"])
df_freq_sev["log_costo_medio"] = np.log1p(df_freq_sev["costo_medio_siniestro"])

# Veredicto S1 (anclar en frecuencia_x100 vs severidad y vs costo medio)
ref_sev = df_corr.query(
    "nivel == 'empresa_acumulado' and estrato == 'global' "
    "and x == 'frecuencia_x100' and y == 'severidad_media'"
).iloc[0]
ref_cost = df_corr.query(
    "nivel == 'empresa_acumulado' and estrato == 'global' "
    "and x == 'frecuencia_x100' and y == 'costo_medio_siniestro'"
).iloc[0]

rho_s1 = max(abs(ref_sev["spearman_rho"]), abs(ref_cost["spearman_rho"]))
if rho_s1 < RHO_DEBIL:
    veredicto_s1 = "SOSTENIDO"
    accion_s1 = "Modelar frecuencia y severidad de forma separada (independencia práctica)."
elif rho_s1 < RHO_MODERADO:
    veredicto_s1 = "PARCIALMENTE_SOSTENIDO"
    accion_s1 = (
        "Dependencia débil–moderada: preferir severidad condicionada a segmento "
        "(clase/tamaño) y diagnosticar residuos freq–sev en el modelo."
    )
else:
    veredicto_s1 = "RECHAZADO"
    accion_s1 = (
        "Dependencia material: modelar severidad/costo medio condicionado a "
        "frecuencia o a factores comunes (clase × tamaño); no asumir independencia."
    )

print(f"\n  Spearman frecuencia_x100 ↔ severidad_media: "
      f"ρ={ref_sev['spearman_rho']:.3f} (p={ref_sev['spearman_p']:.2e})")
print(f"  Spearman frecuencia_x100 ↔ costo_medio:     "
      f"ρ={ref_cost['spearman_rho']:.3f} (p={ref_cost['spearman_p']:.2e})")
print(f"  Veredicto S1: {veredicto_s1}")
print(f"  Acción: {accion_s1}")

# --- Plots S1 ---
fig, axes = sb.create_dashboard(
    1, 2,
    title="S1 – Frecuencia vs severidad (empresas con siniestros)",
    subtitle=(
        f"Spearman ρ(freq, sev)={ref_sev['spearman_rho']:.2f} · "
        f"ρ(freq, costo medio)={ref_cost['spearman_rho']:.2f} → {veredicto_s1}"
    ),
)
ax1, ax2 = axes[0], axes[1]

sample = df_freq_sev.sample(n=min(2000, len(df_freq_sev)), random_state=RANDOM_SEED)
ax1.scatter(
    sample["frecuencia_x100"], sample["severidad_media"],
    s=12, alpha=0.35, color=sb.AZUL_SURA.hex, edgecolors="none",
)
ax1.set_xlabel("Frecuencia × 100 trabajadores")
ax1.set_ylabel("Severidad media (días)")
ax1.set_title(f"ρ Spearman = {ref_sev['spearman_rho']:.3f}")
ax1.set_xlim(0, sample["frecuencia_x100"].quantile(0.99))
ax1.set_ylim(0, sample["severidad_media"].quantile(0.99))

ax2.scatter(
    sample["frecuencia_x100"], sample["costo_medio_siniestro"],
    s=12, alpha=0.35, color=sb.AQUA_SURA.hex, edgecolors="none",
)
ax2.set_xlabel("Frecuencia × 100 trabajadores")
ax2.set_ylabel("Costo medio por siniestro (COP)")
ax2.set_title(f"ρ Spearman = {ref_cost['spearman_rho']:.3f}")
ax2.set_xlim(0, sample["frecuencia_x100"].quantile(0.99))
ax2.set_ylim(0, sample["costo_medio_siniestro"].quantile(0.99))

sb.add_sura_footer(fig, text="S03-3.1.2 | S1 Independencia frecuencia–severidad")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_S1_freq_vs_severidad.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_S1_freq_vs_severidad.png")

# Heatmap de ρ por clase
clases = sorted(emp_pos["clase_riesgo"].unique())
mat_sev = []
mat_cost = []
for c in clases:
    row_sev = df_corr.query(
        f"estrato == 'clase_{c}' and y == 'severidad_media'"
    )
    row_cost = df_corr.query(
        f"estrato == 'clase_{c}' and y == 'costo_medio_siniestro'"
    )
    mat_sev.append(float(row_sev.iloc[0]["spearman_rho"]) if len(row_sev) else np.nan)
    mat_cost.append(float(row_cost.iloc[0]["spearman_rho"]) if len(row_cost) else np.nan)

fig, ax = plt.subplots(figsize=(8, 4.5))
x_pos = np.arange(len(clases))
w = 0.35
ax.bar(x_pos - w / 2, mat_sev, w, label="vs severidad (días)", color=sb.AZUL_SURA.hex)
ax.bar(x_pos + w / 2, mat_cost, w, label="vs costo medio", color=sb.AQUA_SURA.hex)
ax.axhline(RHO_DEBIL, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.2, label=f"|ρ|={RHO_DEBIL} débil")
ax.axhline(RHO_MODERADO, color="#C62828", ls="--", lw=1.2, label=f"|ρ|={RHO_MODERADO} material")
ax.set_xticks(x_pos)
ax.set_xticklabels([f"Clase {c}" for c in clases])
ax.set_ylabel("Spearman ρ (frecuencia_x100)")
ax.set_title("S1 – Correlación frecuencia–severidad por clase de riesgo")
ax.legend(loc="upper left", fontsize=8)
sb.add_sura_footer(fig, text="S03-3.1.2 | S1 por clase de riesgo")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_S1_corr_por_clase.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_S1_corr_por_clase.png")


# ══════════════════════════════════════════════════════════════════════
#  S2 – Estabilidad del portafolio
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  S2 – ESTABILIDAD DEL PORTAFOLIO (MIX)")
print("=" * 70)

dims = ["clase_riesgo", "sector", "segmento"]
metricas_mix = ["n_empresas", "n_siniestros", "costo_total"]


def _share_table(df: pd.DataFrame, dim: str, value_col: str | None) -> pd.DataFrame:
    """Shares anuales por dimensión. value_col=None → conteo de empresas."""
    if value_col is None:
        g = df.groupby(["anio", dim], observed=True).size().rename("valor")
    else:
        g = df.groupby(["anio", dim], observed=True)[value_col].sum().rename("valor")
    wide = g.unstack(fill_value=0)
    shares = wide.div(wide.sum(axis=1), axis=0)
    long = shares.stack().reset_index()
    long.columns = ["anio", "categoria", "share"]
    long["dimension"] = dim
    long["metrica"] = "n_empresas" if value_col is None else value_col
    long["valor_absoluto"] = g.reindex(
        pd.MultiIndex.from_frame(long[["anio", "categoria"]])
    ).values
    return long


mix_parts = []
for dim in dims:
    mix_parts.append(_share_table(panel, dim, None))
    mix_parts.append(_share_table(panel, dim, "n_siniestros"))
    mix_parts.append(_share_table(panel, dim, "costo_total"))

df_mix = pd.concat(mix_parts, ignore_index=True)
df_mix["categoria"] = df_mix["categoria"].astype(str)

# Estabilidad: JS YoY y JS vs año de referencia (último)
estab_rows = []
for dim in dims:
    for metrica in metricas_mix:
        sub = df_mix.query("dimension == @dim and metrica == @metrica")
        wide = sub.pivot(index="anio", columns="categoria", values="share").fillna(0.0)
        years = sorted(wide.index)
        js_yoy = []
        for i in range(1, len(years)):
            a = wide.loc[years[i - 1]].values.astype(float)
            b = wide.loc[years[i]].values.astype(float)
            # Evitar vectores cero
            if a.sum() == 0 or b.sum() == 0:
                js_yoy.append(np.nan)
            else:
                js_yoy.append(float(jensenshannon(a, b, base=2)))
        js_yoy_arr = np.array(js_yoy, dtype=float)
        # JS de cada año vs referencia
        ref = wide.loc[anio_ref].values.astype(float)
        js_vs_ref = []
        for y in years:
            v = wide.loc[y].values.astype(float)
            if v.sum() == 0 or ref.sum() == 0:
                js_vs_ref.append(np.nan)
            else:
                js_vs_ref.append(float(jensenshannon(v, ref, base=2)))
        mean_js = float(np.nanmean(js_yoy_arr))
        max_js = float(np.nanmax(js_yoy_arr))
        if mean_js < JS_ESTABLE:
            estab = "estable"
        elif mean_js < 2 * JS_ESTABLE:
            estab = "moderadamente_estable"
        else:
            estab = "inestable"
        estab_rows.append({
            "dimension": dim,
            "metrica": metrica,
            "anio_referencia": anio_ref,
            "js_yoy_media": round(mean_js, 4),
            "js_yoy_max": round(max_js, 4),
            "js_vs_ref_media": round(float(np.nanmean(js_vs_ref)), 4),
            "n_anios": len(years),
            "estabilidad": estab,
        })

df_estab = pd.DataFrame(estab_rows)

# Nota: n_empresas es idéntico año a año (panel balanceado de atributos fijos)
# El supuesto de negocio se ancla en composición de siniestros y costo.
estab_riesgo = df_estab.query("metrica in ['n_siniestros', 'costo_total']")
mean_js_riesgo = estab_riesgo["js_yoy_media"].mean()
if mean_js_riesgo < JS_ESTABLE:
    veredicto_s2 = "SOSTENIDO"
    accion_s2 = (
        "El mix de siniestros/costo por clase, sector y tamaño es estable "
        f"(JS YoY media={mean_js_riesgo:.3f} < {JS_ESTABLE}). "
        "Usar el mix histórico reciente como proxy del próximo año."
    )
elif mean_js_riesgo < 2 * JS_ESTABLE:
    veredicto_s2 = "PARCIALMENTE_SOSTENIDO"
    accion_s2 = (
        f"Estabilidad moderada (JS YoY media={mean_js_riesgo:.3f}). "
        "Proyectar con el mix del último año y stress-testear ± variaciones históricas."
    )
else:
    veredicto_s2 = "RECHAZADO"
    accion_s2 = (
        f"Mix inestable (JS YoY media={mean_js_riesgo:.3f}). "
        "No extrapolable; modelar cambios de composición o escenarios explícitos."
    )

print(f"\n  JS YoY media (siniestros+costo, 3 dims): {mean_js_riesgo:.4f}")
print(df_estab.to_string(index=False))
print(f"  Veredicto S2: {veredicto_s2}")

# --- Plots S2 ---
palette = sb.get_palette("categorical_extended")

for dim, fname, title in [
    ("clase_riesgo", "01_S2_mix_clase_costo.png", "Mix de costo por clase de riesgo"),
    ("sector", "01_S2_mix_sector_costo.png", "Mix de costo por sector (top participación)"),
    ("segmento", "01_S2_mix_segmento_costo.png", "Mix de costo por tamaño"),
]:
    sub = df_mix.query("dimension == @dim and metrica == 'costo_total'").copy()
    wide = sub.pivot(index="anio", columns="categoria", values="share").fillna(0.0)
    # Sector: mostrar top 8 por share medio + "Otros"
    if dim == "sector":
        top = wide.mean().sort_values(ascending=False).head(8).index.tolist()
        otros = wide.drop(columns=top).sum(axis=1)
        wide = wide[top].copy()
        wide["Otros"] = otros

    fig, ax = plt.subplots(figsize=(10, 5.5))
    cols = list(wide.columns)
    colors = (palette * ((len(cols) // len(palette)) + 1))[: len(cols)]
    ax.stackplot(wide.index.astype(int), wide.T.values, labels=cols, colors=colors, alpha=0.9)
    ax.set_xlabel("Año")
    ax.set_ylabel("Participación del costo")
    ax.set_title(f"S2 – {title}")
    ax.set_ylim(0, 1)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8, frameon=False)
    sb.add_sura_footer(fig, text="S03-3.1.2 | S2 Estabilidad del portafolio")
    fig.tight_layout(rect=[0, 0.05, 0.82, 1])
    fig.savefig(IMGS_DIR / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Guardado: results/imgs/{fname}")

# Barras JS
fig, ax = plt.subplots(figsize=(9, 4.5))
plot_df = df_estab.copy()
plot_df["label"] = plot_df["dimension"] + " · " + plot_df["metrica"]
order = plot_df.sort_values("js_yoy_media")
colors_bar = [
    sb.AZUL_SURA.hex if r < JS_ESTABLE
    else (sb.AQUA_SURA.hex if r < 2 * JS_ESTABLE else "#C62828")
    for r in order["js_yoy_media"]
]
ax.barh(order["label"], order["js_yoy_media"], color=colors_bar)
ax.axvline(JS_ESTABLE, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.3, label=f"Umbral estable ({JS_ESTABLE})")
ax.set_xlabel("JS divergence YoY (media, base 2)")
ax.set_title("S2 – Estabilidad del mix (menor = más estable)")
ax.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.1.2 | S2 Jensen–Shannon YoY")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_S2_js_estabilidad.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_S2_js_estabilidad.png")


# ══════════════════════════════════════════════════════════════════════
#  S3 – Prima vs costo esperado histórico
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  S3 – PRIMA vs COSTO ESPERADO HISTÓRICO")
print("=" * 70)

cost_anual = (
    panel.groupby("id_empresa", as_index=False)
    .agg(
        costo_anual_medio=("costo_total", "mean"),
        costo_anual_mediana=("costo_total", "median"),
        n_anios_obs=("anio", "nunique"),
        n_siniestros_anual_medio=("n_siniestros", "mean"),
    )
)

df_lr = emp[[
    "id_empresa", "clase_riesgo", "sector", "segmento",
    "n_trabajadores", "prima_anual", "n_siniestros", "costo_total_empresa",
]].merge(cost_anual, on="id_empresa", how="left")

df_lr = df_lr.loc[df_lr["prima_anual"] > 0].copy()
df_lr["loss_ratio"] = df_lr["costo_anual_medio"] / df_lr["prima_anual"]
df_lr["insuficiente"] = (df_lr["loss_ratio"] > LR_INSUFICIENTE).astype(int)
df_lr["log_prima"] = np.log1p(df_lr["prima_anual"])
df_lr["log_costo_anual"] = np.log1p(df_lr["costo_anual_medio"])

# Correlación prima ↔ costo anual (¿la tarifa rankea el riesgo?)
rho_prima_costo, p_prima_costo = stats.spearmanr(
    df_lr["prima_anual"], df_lr["costo_anual_medio"]
)
print(f"\n  Spearman prima ↔ costo anual medio: ρ={rho_prima_costo:.3f} "
      f"(p={p_prima_costo:.2e})")
print(f"  Loss ratio mediana: {df_lr['loss_ratio'].median():.3f}")
print(f"  % empresas con LR > 1: {100 * df_lr['insuficiente'].mean():.1f}%")

# Agregado por segmento clase × sector × tamaño
seg_keys = ["clase_riesgo", "sector", "segmento"]
df_seg = (
    df_lr.groupby(seg_keys, observed=True)
    .agg(
        n_empresas=("id_empresa", "count"),
        prima_media=("prima_anual", "mean"),
        prima_mediana=("prima_anual", "median"),
        costo_anual_medio=("costo_anual_medio", "mean"),
        costo_anual_mediana=("costo_anual_mediana", "median"),
        loss_ratio_media=("loss_ratio", "mean"),
        loss_ratio_mediana=("loss_ratio", "median"),
        pct_insuficiente=("insuficiente", "mean"),
        n_trabajadores_mediana=("n_trabajadores", "median"),
    )
    .reset_index()
)
df_seg["pct_insuficiente"] = (df_seg["pct_insuficiente"] * 100).round(2)
df_seg["brecha_media"] = df_seg["costo_anual_medio"] - df_seg["prima_media"]
df_seg["flag_insuficiente"] = (df_seg["loss_ratio_media"] > LR_INSUFICIENTE).astype(int)
df_seg["share_costo_portafolio_pct"] = (
    100 * df_seg["costo_anual_medio"] * df_seg["n_empresas"]
    / (df_seg["costo_anual_medio"] * df_seg["n_empresas"]).sum()
).round(3)

# También agregados más grueso para lectura ejecutiva
df_seg_clase_tam = (
    df_lr.groupby(["clase_riesgo", "segmento"], observed=True)
    .agg(
        n_empresas=("id_empresa", "count"),
        prima_media=("prima_anual", "mean"),
        costo_anual_medio=("costo_anual_medio", "mean"),
        loss_ratio_media=("loss_ratio", "mean"),
        loss_ratio_mediana=("loss_ratio", "median"),
        pct_insuficiente=("insuficiente", "mean"),
    )
    .reset_index()
)
df_seg_clase_tam["pct_insuficiente"] = (df_seg_clase_tam["pct_insuficiente"] * 100).round(2)
df_seg_clase_tam["flag_insuficiente"] = (
    df_seg_clase_tam["loss_ratio_media"] > LR_INSUFICIENTE
).astype(int)

n_seg_insuf = int(df_seg["flag_insuficiente"].sum())
n_seg_total = len(df_seg)
pct_emp_insuf = 100 * df_lr["insuficiente"].mean()
lr_med = float(df_lr["loss_ratio"].median())

# Veredicto: la prima rankea el riesgo (ρ alto) PERO hay segmentos con LR>1
if rho_prima_costo >= RHO_MODERADO and pct_emp_insuf < 20 and n_seg_insuf / max(n_seg_total, 1) < 0.25:
    veredicto_s3 = "SOSTENIDO"
    accion_s3 = (
        "La prima rankea bien el costo histórico; insuficiencia concentrada en "
        "pocos segmentos — priorizar ajuste tarifario ahí."
    )
elif rho_prima_costo >= RHO_DEBIL:
    veredicto_s3 = "PARCIALMENTE_SOSTENIDO"
    accion_s3 = (
        f"Prima correlacionada con costo (ρ={rho_prima_costo:.2f}), pero "
        f"{pct_emp_insuf:.1f}% de empresas y {n_seg_insuf}/{n_seg_total} segmentos "
        f"con LR medio > 1. Usar el modelo de costo esperado para señalar brechas."
    )
else:
    veredicto_s3 = "RECHAZADO"
    accion_s3 = (
        "La prima no rankea el costo histórico; la tarifa actual no es un proxy "
        "confiable del riesgo — el modelo de S03 es crítico para el ajuste."
    )

print(f"  Segmentos clase×sector×tamaño con LR medio > 1: {n_seg_insuf}/{n_seg_total}")
print(f"  Veredicto S3: {veredicto_s3}")
print(f"  Acción: {accion_s3}")

top_insuf = (
    df_seg.query("flag_insuficiente == 1")
    .sort_values("loss_ratio_media", ascending=False)
    .head(10)
)
print("\n  Top segmentos insuficientes (LR media):")
if len(top_insuf):
    print(top_insuf[seg_keys + ["n_empresas", "loss_ratio_media", "pct_insuficiente"]]
          .to_string(index=False))
else:
    print("  (ninguno)")

# --- Plots S3 ---
fig, axes = sb.create_dashboard(
    1, 2,
    title="S3 – Prima vs costo anual histórico",
    subtitle=(
        f"Spearman ρ={rho_prima_costo:.2f} · LR mediana={lr_med:.2f} · "
        f"% empresas LR>1={pct_emp_insuf:.1f}% → {veredicto_s3}"
    ),
)
ax1, ax2 = axes[0], axes[1]

samp = df_lr.sample(n=min(2500, len(df_lr)), random_state=RANDOM_SEED)
colors_pt = np.where(samp["insuficiente"] == 1, "#C62828", sb.AZUL_SURA.hex)
ax1.scatter(samp["prima_anual"], samp["costo_anual_medio"],
            s=10, alpha=0.3, c=colors_pt, edgecolors="none")
lim_max = max(
    samp["prima_anual"].quantile(0.98),
    samp["costo_anual_medio"].quantile(0.98),
)
ax1.plot([0, lim_max], [0, lim_max], "--", color=sb.AQUA_SURA.hex, lw=1.4, label="LR = 1")
ax1.set_xlim(0, lim_max)
ax1.set_ylim(0, lim_max)
ax1.set_xlabel("Prima anual (COP)")
ax1.set_ylabel("Costo anual medio histórico (COP)")
ax1.set_title("Empresa: prima vs costo (rojo = LR>1)")
ax1.legend(fontsize=8)

# Heatmap LR por clase × segmento
heat = df_seg_clase_tam.pivot(
    index="clase_riesgo", columns="segmento", values="loss_ratio_media"
)
heat = heat.reindex(columns=SEG_ORDER)
im = ax2.imshow(heat.values, cmap=sb.get_cmap("sura_diverging"), aspect="auto",
                vmin=0, vmax=max(1.5, float(np.nanmax(heat.values))))
ax2.set_xticks(range(len(heat.columns)))
ax2.set_xticklabels(heat.columns, rotation=30, ha="right", fontsize=8)
ax2.set_yticks(range(len(heat.index)))
ax2.set_yticklabels([f"Clase {i}" for i in heat.index])
ax2.set_title("Loss ratio media (clase × tamaño)")
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        val = heat.values[i, j]
        if np.isfinite(val):
            ax2.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8,
                     color="white" if val > 0.9 or val < 0.3 else "black")
plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)

sb.add_sura_footer(fig, text="S03-3.1.2 | S3 Prima vs costo")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_S3_prima_vs_costo.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_S3_prima_vs_costo.png")

# Barras top segmentos insuficientes / peor LR
fig, ax = plt.subplots(figsize=(10, 5.5))
top15 = df_seg.sort_values("loss_ratio_media", ascending=False).head(15).copy()
top15["label"] = (
    "C" + top15["clase_riesgo"].astype(str) + " · "
    + top15["segmento"].astype(str).str.replace(r" \(.*\)", "", regex=True)
    + " · " + top15["sector"].astype(str).str.slice(0, 18)
)
cols_lr = [
    "#C62828" if f else sb.AZUL_SURA.hex
    for f in top15["flag_insuficiente"]
]
ax.barh(top15["label"][::-1], top15["loss_ratio_media"][::-1], color=cols_lr[::-1])
ax.axvline(1.0, color=sb.AMARILLO_SURA.hex, ls="--", lw=1.4, label="LR = 1")
ax.set_xlabel("Loss ratio media (costo anual / prima)")
ax.set_title("S3 – Segmentos con mayor loss ratio (clase × tamaño × sector)")
ax.legend(fontsize=8)
sb.add_sura_footer(fig, text="S03-3.1.2 | S3 Segmentos críticos")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(IMGS_DIR / "01_S3_segmentos_loss_ratio.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ Guardado: results/imgs/01_S3_segmentos_loss_ratio.png")


# ══════════════════════════════════════════════════════════════════════
#  Veredicto consolidado + persistencia
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  PERSISTENCIA DE STAGING Y RESULTADOS")
print("=" * 70)

df_veredicto = pd.DataFrame([
    {
        "supuesto": "S1",
        "nombre": "Independencia frecuencia–severidad",
        "metrica_clave": "max_|Spearman_rho|(freq, sev/costo_medio)",
        "valor_metrica": round(float(rho_s1), 4),
        "umbral": RHO_MODERADO,
        "veredicto": veredicto_s1,
        "accion_modelado": accion_s1,
        "detalle": (
            f"ρ(freq,sev)={ref_sev['spearman_rho']}; "
            f"ρ(freq,costo)={ref_cost['spearman_rho']}"
        ),
    },
    {
        "supuesto": "S2",
        "nombre": "Estabilidad del portafolio (mix)",
        "metrica_clave": "JS_YoY_media(siniestros+costo, 3 dims)",
        "valor_metrica": round(float(mean_js_riesgo), 4),
        "umbral": JS_ESTABLE,
        "veredicto": veredicto_s2,
        "accion_modelado": accion_s2,
        "detalle": (
            f"JS n_empresas≈0 (panel fijo); anclar en shares de "
            f"siniestros/costo. anio_ref={anio_ref}"
        ),
    },
    {
        "supuesto": "S3",
        "nombre": "Prima refleja el riesgo",
        "metrica_clave": "Spearman(prima, costo_anual) y % LR>1",
        "valor_metrica": round(float(rho_prima_costo), 4),
        "umbral": RHO_MODERADO,
        "veredicto": veredicto_s3,
        "accion_modelado": accion_s3,
        "detalle": (
            f"LR_mediana={lr_med:.3f}; pct_emp_LR>1={pct_emp_insuf:.1f}%; "
            f"segs_insuf={n_seg_insuf}/{n_seg_total}"
        ),
    },
])

# Guardar staging S03
paths = {
    "supuestos_freq_sev_empresa.parquet": df_freq_sev,
    "supuestos_freq_sev_correlacion.parquet": df_corr,
    "supuestos_mix_anual.parquet": df_mix,
    "supuestos_mix_estabilidad.parquet": df_estab,
    "supuestos_prima_vs_costo_empresa.parquet": df_lr,
    "supuestos_prima_vs_costo_segmento.parquet": df_seg,
    "supuestos_veredicto.parquet": df_veredicto,
}

for name, frame in paths.items():
    out = DATA_S03 / name
    frame.to_parquet(out, index=False)
    print(f"  ✓ Staging: {out.relative_to(ROOT)}  ({frame.shape[0]} × {frame.shape[1]})")

# Espejo CSV en results
csv_map = {
    "supuestos_freq_sev_correlacion.csv": df_corr,
    "supuestos_mix_estabilidad.csv": df_estab,
    "supuestos_prima_vs_costo_segmento.csv": df_seg,
    "supuestos_veredicto.csv": df_veredicto,
}
for name, frame in csv_map.items():
    frame.to_csv(RESULTS_DIR / name, index=False)
    print(f"  ✓ Results: results/{name}")

# Agregado clase×tamaño también a results (lectura rápida)
df_seg_clase_tam.to_csv(RESULTS_DIR / "supuestos_prima_vs_costo_clase_segmento.csv", index=False)

print("\n" + "=" * 70)
print("  RESUMEN DE VEREDICTOS")
print("=" * 70)
print(df_veredicto[["supuesto", "nombre", "veredicto", "valor_metrica"]].to_string(index=False))
print("\n✓ Validación de supuestos completada.")
