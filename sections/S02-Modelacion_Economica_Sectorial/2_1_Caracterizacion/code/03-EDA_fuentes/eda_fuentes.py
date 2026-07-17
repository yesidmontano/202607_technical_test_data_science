"""
EDA preliminar de fuentes DANE del sector construcción
======================================================
Sección: S02 – Modelación Económica Sectorial
Subsección: 2.1 – Caracterización (ítem 2.1.3)

Descripción:
    Análisis exploratorio preliminar corto de las fuentes seleccionadas
    en 2.1.2 (ELIC, CEED, IPOC, EC):
    · Limpieza tipográfica (miles con coma, espacios en meses)
    · Series temporales y composición por fuente
    · Persistencia de staging reutilizable en data/staging/S02/
    · Visualizaciones con sura_brand en results/imgs/

Inputs:
    - sections/.../resources/ELIC-2025-2026.csv
    - sections/.../resources/CEED-2020-2026.csv
    - sections/.../resources/IPOC-2018-2026.csv
    - sections/.../resources/EC-2022-2026.csv

Outputs:
    - data/staging/S02/elic_staging.parquet
    - data/staging/S02/ceed_staging.parquet
    - data/staging/S02/ipoc_staging.parquet
    - data/staging/S02/ec_staging.parquet
    - data/staging/S02/fuentes_eda_resumen.parquet
    - sections/.../results/imgs/03_*.png

Uso:
    .venv/bin/python \\
      sections/S02-Modelacion_Economica_Sectorial/2_1_Caracterizacion/code/03-EDA_fuentes/eda_fuentes.py
"""

from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
#  Global config
# ──────────────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
RESOURCES = (
    ROOT
    / "sections"
    / "S02-Modelacion_Economica_Sectorial"
    / "2_1_Caracterizacion"
    / "resources"
)
DATA_STAGING = ROOT / "data" / "staging" / "S02"
RESULTS_IMGS = (
    ROOT
    / "sections"
    / "S02-Modelacion_Economica_Sectorial"
    / "2_1_Caracterizacion"
    / "results"
    / "imgs"
)

DATA_STAGING.mkdir(parents=True, exist_ok=True)
RESULTS_IMGS.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()
PALETTE = sb.get_palette("categorical")

QUARTER_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}
MONTH_MAP = {
    "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12,
}
MONTH_LABELS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]

IPOC_SHORT = {
    "Tipo de construcción_530201_Carreteras, calles, vías férreas y pistas "
    "de aterrizaje, puentes, carreteras elevadas y túneles": "Carreteras/puentes",
    "Tipo de construcción_530202_Puertos, canales, presas, sistemas de riego "
    "y otras obras hidráulicas (acueductos)": "Obras hidráulicas",
    "Tipo de construcción_530203_Tuberías para la conducción de gas a larga "
    "distancia, líneas de comunicación y cables de poder; tuberías y cables "
    "locales, y obras conexas": "Tuberías/cables",
    "Tipo de construcción_530204_Construcciones  en minas y plantas "
    "industriales ": "Minas/plantas",
    "Tipo de construcción_530205_Instalaciones al aire libre para deportes "
    "y esparcimiento; y otras obras de ingeniería civil": "Otras obras civil",
}


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_numeric(series: pd.Series) -> pd.Series:
    """Parse DANE-style numbers with thousand commas and surrounding spaces."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .replace({"": np.nan, "nan": np.nan, "None": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _save_fig(fig: plt.Figure, name: str) -> None:
    path = RESULTS_IMGS / name
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"   💾  {name}")


def _fmt_millones(x, _pos=None) -> str:
    return f"{x / 1e6:.1f}M"


def _period_label(anio: int, trimestre: str) -> str:
    return f"{anio}-T{QUARTER_ORDER[trimestre]}"


def _save_parquet(df: pd.DataFrame, name: str) -> Path:
    path = DATA_STAGING / name
    df.to_parquet(path, index=False)
    print(f"   📦  {name}  shape={df.shape}")
    return path


# ──────────────────────────────────────────────────────────────────────────────
#  1. Load & clean sources
# ──────────────────────────────────────────────────────────────────────────────
print("📂  Loading DANE resource CSVs...")

# --- ELIC --------------------------------------------------------------------
elic_raw = pd.read_csv(RESOURCES / "ELIC-2025-2026.csv")
elic = elic_raw.rename(columns={
    "Año": "anio",
    "Metros cuadrados_Mayo": "m2_mayo",
    "Metros cuadrados_Enero - mayo": "m2_ene_mayo",
    "Metros cuadrados_Doce meses a mayo": "m2_doce_meses",
    "Variaciones (%)_Anual": "var_anual_pct",
    "Variaciones (%)_Año corrido": "var_anio_corrido_pct",
    "Variaciones (%)_Doce meses": "var_doce_meses_pct",
    "Variaciones (%)_Mensual": "var_mensual_pct",
}).copy()
for col in ["m2_mayo", "m2_ene_mayo", "m2_doce_meses"]:
    elic[col] = _parse_numeric(elic[col])
elic["fuente"] = "ELIC"
elic["frecuencia"] = "anual_referencia_mayo"
elic["rezago_aprox_dias"] = 45

# --- CEED --------------------------------------------------------------------
ceed_raw = pd.read_csv(RESOURCES / "CEED-2020-2026.csv")
ceed = ceed_raw.rename(columns={
    "Año": "anio",
    "Trimestre": "trimestre",
    "Total área censada": "area_censada_m2",
    "Total área culminada": "area_culminada_m2",
    "Área en proceso_Nueva": "proceso_nueva_m2",
    "Área en proceso_Continúa en proceso": "proceso_continua_m2",
    "Área en proceso_Reinicia proceso": "proceso_reinicia_m2",
    "Área en proceso_Total área en proceso": "proceso_total_m2",
    "Área paralizada_Nueva": "paralizada_nueva_m2",
    "Área paralizada_Continúa paralizada": "paralizada_continua_m2",
    "Área paralizada_Total área paralizada": "paralizada_total_m2",
}).copy()
ceed["trimestre"] = ceed["trimestre"].astype(str).str.strip()
m2_cols = [c for c in ceed.columns if c.endswith("_m2")]
for col in m2_cols:
    ceed[col] = _parse_numeric(ceed[col])
ceed["q"] = ceed["trimestre"].map(QUARTER_ORDER)
ceed["periodo"] = ceed.apply(lambda r: _period_label(int(r["anio"]), r["trimestre"]), axis=1)
ceed["fecha"] = pd.to_datetime(
    ceed["anio"].astype(str) + "-" + (ceed["q"] * 3).astype(str) + "-01"
)
ceed["share_proceso"] = ceed["proceso_total_m2"] / ceed["area_censada_m2"]
ceed["share_paralizada"] = ceed["paralizada_total_m2"] / ceed["area_censada_m2"]
ceed["share_culminada"] = ceed["area_culminada_m2"] / ceed["area_censada_m2"]
ceed["fuente"] = "CEED"
ceed["frecuencia"] = "trimestral"
ceed["rezago_aprox_dias"] = 45
ceed = ceed.sort_values(["anio", "q"]).reset_index(drop=True)

# --- IPOC --------------------------------------------------------------------
ipoc_raw = pd.read_csv(RESOURCES / "IPOC-2018-2026.csv")
ipoc = ipoc_raw.rename(columns={"Año": "anio", "Trimestre": "trimestre", "Total IPOC": "ipoc_total"})
ipoc["trimestre"] = ipoc["trimestre"].astype(str).str.strip()
ipoc = ipoc.rename(columns=IPOC_SHORT)
short_cols = list(IPOC_SHORT.values())
ipoc["q"] = ipoc["trimestre"].map(QUARTER_ORDER)
ipoc["periodo"] = ipoc.apply(lambda r: _period_label(int(r["anio"]), r["trimestre"]), axis=1)
ipoc["fecha"] = pd.to_datetime(
    ipoc["anio"].astype(str) + "-" + (ipoc["q"] * 3).astype(str) + "-01"
)
ipoc["fuente"] = "IPOC"
ipoc["frecuencia"] = "trimestral"
ipoc["rezago_aprox_dias"] = 48
ipoc = ipoc.sort_values(["anio", "q"]).reset_index(drop=True)

# --- EC ----------------------------------------------------------------------
ec_raw = pd.read_csv(RESOURCES / "EC-2022-2026.csv")
ec = ec_raw.rename(columns={
    "Año": "anio",
    "Mes": "mes_label",
    "Metros cúbicos_premezclado": "m3_premezclado",
}).copy()
ec["mes_label"] = ec["mes_label"].astype(str).str.strip()
ec["mes"] = ec["mes_label"].map(MONTH_MAP)
ec["m3_premezclado"] = _parse_numeric(ec["m3_premezclado"])
ec["fecha"] = pd.to_datetime(
    ec["anio"].astype(str) + "-" + ec["mes"].astype(str).str.zfill(2) + "-01"
)
ec["anio_mes"] = ec["fecha"].dt.to_period("M").astype(str)
ec["fuente"] = "EC"
ec["frecuencia"] = "mensual"
ec["rezago_aprox_dias"] = 38
ec = ec.sort_values("fecha").reset_index(drop=True)
ec["m3_ma3"] = ec["m3_premezclado"].rolling(3, min_periods=1).mean()
ec["var_yoy_pct"] = ec["m3_premezclado"].pct_change(12) * 100

print(f"   ELIC : {elic.shape}  |  CEED : {ceed.shape}  |  IPOC : {ipoc.shape}  |  EC : {ec.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  2. Persist staging
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔧  Saving staging datasets to data/staging/S02/...")

_save_parquet(elic, "elic_staging.parquet")
_save_parquet(ceed, "ceed_staging.parquet")
_save_parquet(ipoc, "ipoc_staging.parquet")
_save_parquet(ec, "ec_staging.parquet")

resumen_rows = [
    {
        "fuente": "ELIC",
        "n_obs": len(elic),
        "frecuencia": "anual_referencia_mayo",
        "inicio": str(elic["anio"].min()),
        "fin": str(elic["anio"].max()),
        "indicador_clave": "m2_mayo",
        "valor_ultimo": float(elic.loc[elic["anio"].idxmax(), "m2_mayo"]),
        "var_ultimo_pct": float(elic.loc[elic["anio"].idxmax(), "var_anual_pct"]),
        "rezago_aprox_dias": 45,
        "rol_ciclo": "lider",
    },
    {
        "fuente": "CEED",
        "n_obs": len(ceed),
        "frecuencia": "trimestral",
        "inicio": ceed["periodo"].iloc[0],
        "fin": ceed["periodo"].iloc[-1],
        "indicador_clave": "area_censada_m2",
        "valor_ultimo": float(ceed["area_censada_m2"].iloc[-1]),
        "var_ultimo_pct": float(
            (ceed["area_censada_m2"].iloc[-1] / ceed["area_censada_m2"].iloc[-5] - 1) * 100
        ) if len(ceed) >= 5 else np.nan,
        "rezago_aprox_dias": 45,
        "rol_ciclo": "coincidente_edificacion",
    },
    {
        "fuente": "IPOC",
        "n_obs": len(ipoc),
        "frecuencia": "trimestral",
        "inicio": ipoc["periodo"].iloc[0],
        "fin": ipoc["periodo"].iloc[-1],
        "indicador_clave": "ipoc_total",
        "valor_ultimo": float(ipoc["ipoc_total"].iloc[-1]),
        "var_ultimo_pct": float(
            (ipoc["ipoc_total"].iloc[-1] / ipoc["ipoc_total"].iloc[-5] - 1) * 100
        ) if len(ipoc) >= 5 else np.nan,
        "rezago_aprox_dias": 48,
        "rol_ciclo": "coincidente_obras_civiles",
    },
    {
        "fuente": "EC",
        "n_obs": len(ec),
        "frecuencia": "mensual",
        "inicio": ec["anio_mes"].iloc[0],
        "fin": ec["anio_mes"].iloc[-1],
        "indicador_clave": "m3_premezclado",
        "valor_ultimo": float(ec["m3_premezclado"].iloc[-1]),
        "var_ultimo_pct": float(ec["var_yoy_pct"].iloc[-1]) if pd.notna(ec["var_yoy_pct"].iloc[-1]) else np.nan,
        "rezago_aprox_dias": 38,
        "rol_ciclo": "coincidente_rapido",
    },
]
resumen = pd.DataFrame(resumen_rows)
_save_parquet(resumen, "fuentes_eda_resumen.parquet")

# ──────────────────────────────────────────────────────────────────────────────
#  3. Descriptive prints (for caracterizacion.md)
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊  Descriptive highlights")
print("─" * 72)

print("\n[ELIC] Área licenciada (referencia mayo)")
print(elic[["anio", "m2_mayo", "m2_ene_mayo", "m2_doce_meses",
            "var_anual_pct", "var_anio_corrido_pct", "var_doce_meses_pct",
            "var_mensual_pct"]].to_string(index=False))

print("\n[CEED] Últimos 4 trimestres")
print(
    ceed[["periodo", "area_censada_m2", "area_culminada_m2",
          "proceso_total_m2", "paralizada_total_m2",
          "share_proceso", "share_paralizada"]].tail(4).to_string(index=False)
)
print(
    f"   Área censada rango: {ceed['area_censada_m2'].min():,.0f} → "
    f"{ceed['area_censada_m2'].max():,.0f} m²"
)
print(
    f"   Share paralizada (media / último): "
    f"{ceed['share_paralizada'].mean():.1%} / {ceed['share_paralizada'].iloc[-1]:.1%}"
)

print("\n[IPOC] Resumen índice")
print(
    f"   Periodo: {ipoc['periodo'].iloc[0]} → {ipoc['periodo'].iloc[-1]}  "
    f"(n={len(ipoc)})"
)
print(
    f"   IPOC total min/mediana/máx: "
    f"{ipoc['ipoc_total'].min():.1f} / {ipoc['ipoc_total'].median():.1f} / "
    f"{ipoc['ipoc_total'].max():.1f}"
)
print(f"   Último: {ipoc['periodo'].iloc[-1]} = {ipoc['ipoc_total'].iloc[-1]:.1f}")
print("   Media por tipología:")
for c in short_cols:
    print(f"      {c:20s}: media={ipoc[c].mean():6.1f}  último={ipoc[c].iloc[-1]:6.1f}")

print("\n[EC] Concreto premezclado")
print(
    f"   Periodo: {ec['anio_mes'].iloc[0]} → {ec['anio_mes'].iloc[-1]}  "
    f"(n={len(ec)})"
)
print(
    f"   m³ media/últ: {ec['m3_premezclado'].mean():,.0f} / "
    f"{ec['m3_premezclado'].iloc[-1]:,.0f}"
)
print(
    f"   YoY último: {ec['var_yoy_pct'].iloc[-1]:+.1f}%  |  "
    f"máx YoY: {ec['var_yoy_pct'].max():+.1f}%  |  "
    f"mín YoY: {ec['var_yoy_pct'].min():+.1f}%"
)
seasonal = (
    ec.groupby("mes", observed=True)["m3_premezclado"]
    .mean()
    .reindex(range(1, 13))
)
seasonal_idx = seasonal / seasonal.mean()
print(
    f"   Índice estacional amplitud: "
    f"{(seasonal_idx.max() - seasonal_idx.min()) * 100:.1f} pp "
    f"(pico mes {int(seasonal_idx.idxmax())}, valle mes {int(seasonal_idx.idxmin())})"
)

# ──────────────────────────────────────────────────────────────────────────────
#  4. Visualizations
# ──────────────────────────────────────────────────────────────────────────────
print("\n🎨  Generating plots...")

# ── 03_elic_area_y_variaciones ──────────────────────────────────────────────
fig, axes = sb.create_dashboard(
    1, 2,
    title="ELIC – Licencias de Construcción (referencia mayo)",
    subtitle="Área aprobada y variaciones % interanuales | DANE",
)
ax1, ax2 = axes[0], axes[1]
years = elic["anio"].astype(str).tolist()

ax1.bar(years, elic["m2_mayo"] / 1e6, color=PALETTE[0], alpha=0.90, label="Mayo")
ax1.plot(
    years, elic["m2_ene_mayo"] / 1e6,
    color=PALETTE[1], marker="o", linewidth=2.2, markersize=7, label="Ene–May acumulado",
)
ax1.set_title("Área licenciada (millones m²)")
ax1.set_ylabel("Millones de m²")
ax1.set_xlabel("Año")
ax1.legend(frameon=True, loc="upper left", fontsize=8)
for i, v in enumerate(elic["m2_mayo"] / 1e6):
    ax1.text(i, v + 0.05, f"{v:.2f}", ha="center", va="bottom", fontsize=8)

x = np.arange(len(years))
w = 0.2
vars_plot = [
    ("var_anual_pct", "Anual"),
    ("var_anio_corrido_pct", "Año corrido"),
    ("var_doce_meses_pct", "Doce meses"),
    ("var_mensual_pct", "Mensual"),
]
for i, (col, label) in enumerate(vars_plot):
    ax2.bar(x + (i - 1.5) * w, elic[col], width=w, color=PALETTE[i], alpha=0.90, label=label)
ax2.axhline(0, color="#888888", linewidth=0.9)
ax2.set_xticks(x)
ax2.set_xticklabels(years)
ax2.set_title("Variaciones %")
ax2.set_ylabel("%")
ax2.set_xlabel("Año")
ax2.legend(frameon=True, loc="upper left", fontsize=7, ncol=2)

sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | ELIC")
_save_fig(fig, "03_elic_area_y_variaciones.png")

# ── 03_ceed_series_areas ────────────────────────────────────────────────────
fig, ax = sb.create_report_figure(
    title="CEED – Evolución del área censada y estados de obra",
    subtitle="Trimestres 2020-III → 2026-I | m²",
)
periodos = ceed["periodo"].tolist()
ax.plot(periodos, ceed["area_censada_m2"] / 1e6, color=PALETTE[0],
        marker="o", linewidth=2.2, markersize=4, label="Área censada")
ax.plot(periodos, ceed["proceso_total_m2"] / 1e6, color=PALETTE[1],
        marker="s", linewidth=2.0, markersize=4, label="En proceso")
ax.plot(periodos, ceed["paralizada_total_m2"] / 1e6, color=PALETTE[2],
        marker="^", linewidth=2.0, markersize=4, label="Paralizada")
ax.plot(periodos, ceed["area_culminada_m2"] / 1e6, color=PALETTE[3],
        marker="D", linewidth=2.0, markersize=4, label="Culminada")
tick_pos = list(range(0, len(periodos), 2))
ax.set_xticks(tick_pos)
ax.set_xticklabels([periodos[i] for i in tick_pos], rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Millones de m²")
ax.set_xlabel("Periodo")
ax.legend(frameon=True, loc="best", fontsize=8)
ax.set_ylim(bottom=0)
sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | CEED series")
_save_fig(fig, "03_ceed_series_areas.png")

# ── 03_ceed_composicion ─────────────────────────────────────────────────────
fig, axes = sb.create_dashboard(
    1, 2,
    title="CEED – Composición del stock censado",
    subtitle="Participación de área en proceso vs paralizada | shares sobre área censada",
)
ax1, ax2 = axes[0], axes[1]

ax1.stackplot(
    range(len(ceed)),
    ceed["share_proceso"] * 100,
    ceed["share_paralizada"] * 100,
    ceed["share_culminada"] * 100,
    labels=["En proceso", "Paralizada", "Culminada"],
    colors=PALETTE[:3],
    alpha=0.85,
)
ax1.set_xticks(tick_pos)
ax1.set_xticklabels([periodos[i] for i in tick_pos], rotation=45, ha="right", fontsize=7)
ax1.set_ylabel("% del área censada")
ax1.set_title("Shares apilados")
ax1.legend(frameon=True, loc="lower right", fontsize=7)
ax1.set_ylim(0, 100)

ax2.bar(periodos, ceed["proceso_nueva_m2"] / 1e6, color=PALETTE[0],
        alpha=0.90, label="Nueva (iniciada)")
ax2.plot(periodos, ceed["proceso_reinicia_m2"] / 1e6, color=PALETTE[4],
         marker="o", linewidth=2.0, label="Reinicia proceso")
ax2.set_xticks(tick_pos)
ax2.set_xticklabels([periodos[i] for i in tick_pos], rotation=45, ha="right", fontsize=7)
ax2.set_ylabel("Millones de m²")
ax2.set_title("Flujo: nuevas vs reinicios")
ax2.legend(frameon=True, loc="upper right", fontsize=7)

sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | CEED composición")
_save_fig(fig, "03_ceed_composicion.png")

# ── 03_ipoc_total_y_tipologias ───────────────────────────────────────────────
fig, axes = sb.create_dashboard(
    1, 2,
    title="IPOC – Producción de obras civiles",
    subtitle="Índice total y por tipología CPC | 2018-I → 2026-I",
)
ax1, ax2 = axes[0], axes[1]
p_ipoc = ipoc["periodo"].tolist()
tick_ipoc = list(range(0, len(p_ipoc), 4))

ax1.plot(p_ipoc, ipoc["ipoc_total"], color=PALETTE[0],
         marker="o", linewidth=2.2, markersize=4, label="IPOC total")
ax1.axhline(ipoc["ipoc_total"].mean(), color=PALETTE[1], linestyle="--",
            linewidth=1.2, label=f"Media ({ipoc['ipoc_total'].mean():.1f})")
ax1.set_xticks(tick_ipoc)
ax1.set_xticklabels([p_ipoc[i] for i in tick_ipoc], rotation=45, ha="right", fontsize=7)
ax1.set_ylabel("Índice")
ax1.set_title("IPOC total")
ax1.legend(frameon=True, loc="upper left", fontsize=8)

for i, col in enumerate(short_cols):
    ax2.plot(p_ipoc, ipoc[col], color=PALETTE[i % len(PALETTE)],
             linewidth=1.6, marker="o", markersize=2.5, label=col)
ax2.set_xticks(tick_ipoc)
ax2.set_xticklabels([p_ipoc[i] for i in tick_ipoc], rotation=45, ha="right", fontsize=7)
ax2.set_ylabel("Índice")
ax2.set_title("Por tipología")
ax2.legend(frameon=True, loc="upper left", fontsize=6, ncol=1)

sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | IPOC")
_save_fig(fig, "03_ipoc_total_y_tipologias.png")

# ── 03_ec_serie_mensual ─────────────────────────────────────────────────────
fig, axes = sb.create_dashboard(
    1, 2,
    title="EC – Concreto premezclado despachado",
    subtitle="Serie mensual 2022-01 → 2026-05 | miles de m³",
)
ax1, ax2 = axes[0], axes[1]
x_ec = ec["anio_mes"].tolist()
tick_ec = list(range(0, len(x_ec), 6))

ax1.plot(x_ec, ec["m3_premezclado"] / 1e3, color=PALETTE[0],
         linewidth=1.4, alpha=0.55, label="m³ mensuales")
ax1.plot(x_ec, ec["m3_ma3"] / 1e3, color=PALETTE[1],
         linewidth=2.4, label="Media móvil 3m")
ax1.set_xticks(tick_ec)
ax1.set_xticklabels([x_ec[i] for i in tick_ec], rotation=45, ha="right", fontsize=7)
ax1.set_ylabel("Miles de m³")
ax1.set_title("Despachos mensuales")
ax1.legend(frameon=True, loc="upper right", fontsize=8)
ax1.set_ylim(bottom=0)

yoy = ec.dropna(subset=["var_yoy_pct"])
ax2.bar(yoy["anio_mes"], yoy["var_yoy_pct"], color=PALETTE[0], alpha=0.85)
ax2.axhline(0, color="#888888", linewidth=0.9)
tick_yoy = list(range(0, len(yoy), 4))
ax2.set_xticks([yoy["anio_mes"].iloc[i] for i in tick_yoy])
ax2.set_xticklabels([yoy["anio_mes"].iloc[i] for i in tick_yoy],
                    rotation=45, ha="right", fontsize=7)
ax2.set_ylabel("Variación YoY (%)")
ax2.set_title("Variación interanual")

sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | EC serie")
_save_fig(fig, "03_ec_serie_mensual.png")

# ── 03_ec_estacionalidad ────────────────────────────────────────────────────
fig, axes = sb.create_dashboard(
    1, 2,
    title="EC – Perfil estacional del concreto premezclado",
    subtitle="Promedio por mes calendario e índice estacional (media = 1)",
)
ax1, ax2 = axes[0], axes[1]

ax1.bar(MONTH_LABELS, seasonal.values / 1e3, color=PALETTE[0], alpha=0.90)
ax1.set_ylabel("Miles de m³ (promedio)")
ax1.set_title("Promedio mensual")
ax1.set_xlabel("Mes")

ax2.plot(MONTH_LABELS, seasonal_idx.values, color=PALETTE[1],
         marker="o", linewidth=2.2, markersize=7)
ax2.axhline(1.0, color="#888888", linestyle="--", linewidth=1.0)
ax2.set_ylabel("Índice (media = 1)")
ax2.set_title("Índice estacional")
ax2.set_xlabel("Mes")
ax2.set_ylim(0.7, 1.3)

sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | EC estacionalidad")
_save_fig(fig, "03_ec_estacionalidad.png")

# ── 03_panel_ciclo_resumen ──────────────────────────────────────────────────
# Align CEED / IPOC / EC (monthly → quarterly mean) on overlapping window
ec_q = (
    ec.assign(q=((ec["mes"] - 1) // 3) + 1)
    .groupby(["anio", "q"], as_index=False)["m3_premezclado"]
    .mean()
    .rename(columns={"m3_premezclado": "ec_m3_promedio_trim"})
)
panel = (
    ceed[["anio", "q", "periodo", "fecha", "area_censada_m2", "proceso_nueva_m2"]]
    .merge(ipoc[["anio", "q", "ipoc_total"]], on=["anio", "q"], how="inner")
    .merge(ec_q, on=["anio", "q"], how="left")
    .sort_values(["anio", "q"])
    .reset_index(drop=True)
)

# Z-score for visual co-movement (exploratory only)
for col, out in [
    ("area_censada_m2", "z_ceed"),
    ("ipoc_total", "z_ipoc"),
    ("ec_m3_promedio_trim", "z_ec"),
]:
    s = panel[col]
    panel[out] = (s - s.mean()) / s.std(ddof=0)

_save_parquet(panel, "panel_fuentes_trimestral.parquet")

fig, ax = sb.create_report_figure(
    title="Co-movimiento preliminar del ciclo (z-scores)",
    subtitle="CEED área censada · IPOC total · EC m³ (promedio trimestral) | ventana común",
)
p_panel = panel["periodo"].tolist()
ax.plot(p_panel, panel["z_ceed"], color=PALETTE[0], marker="o",
        linewidth=2.0, markersize=4, label="CEED (área censada)")
ax.plot(p_panel, panel["z_ipoc"], color=PALETTE[1], marker="s",
        linewidth=2.0, markersize=4, label="IPOC total")
ax.plot(p_panel, panel["z_ec"], color=PALETTE[2], marker="^",
        linewidth=2.0, markersize=4, label="EC m³ (prom. trim.)")
ax.axhline(0, color="#888888", linewidth=0.9)
tick_p = list(range(0, len(p_panel), 2))
ax.set_xticks(tick_p)
ax.set_xticklabels([p_panel[i] for i in tick_p], rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Z-score")
ax.set_xlabel("Periodo")
ax.legend(frameon=True, loc="best", fontsize=8)
sb.add_sura_footer(fig, text="S02 – 2.1.3 EDA fuentes | Panel ciclo")
_save_fig(fig, "03_panel_ciclo_resumen.png")

# Correlations on overlapping non-null rows
corr_cols = ["area_censada_m2", "ipoc_total", "ec_m3_promedio_trim"]
corr = panel[corr_cols].dropna().corr(method="spearman")
print("\n🔗  Spearman (panel trimestral solapado):")
print(corr.round(3).to_string())

print("\n✅  EDA preliminar de fuentes DANE completado.")
print(f"   Staging → {DATA_STAGING}")
print(f"   Imágenes → {RESULTS_IMGS}")
