"""
Diagnóstico de Datos Faltantes – Cuantificación
===============================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.4 – Diagnóstico de datos faltantes
Proceso: 1.4.1 – Cuantificación

Descripción:
    Cuantifica los datos faltantes (NaN) en los CSV raw de empresas y
    siniestros: tasas por columna, cobertura del dataset, patrones de
    co-ocurrencia por fila y tasas estratificadas por variables observables.
    No imputa ni clasifica el mecanismo (MCAR/MAR/MNAR); eso queda para
    procesos posteriores de 1.4.

Inputs (raw + contraste con staging existente):
    - data/raw/empresas.csv
    - data/raw/siniestros.csv
    - data/staging/S01/empresas_staging.parquet   (reutilizado, solo contraste)
    - data/staging/S01/siniestros_staging.parquet (reutilizado, solo contraste)

Outputs:
    - results/imgs/01_*.png
    - results/faltantes_resumen_columnas.csv
    - results/faltantes_patrones.csv
    - results/faltantes_por_estrato.csv
    - data/staging/S01/faltantes_resumen_columnas.parquet
    - data/staging/S01/faltantes_patrones.parquet
    - data/staging/S01/faltantes_por_estrato.parquet
    - data/staging/S01/faltantes_resumen_datasets.parquet

Uso:
    .venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_4_Diagnostico datos faltantes/code/01-cuantificacion/cuantificacion_faltantes.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración global
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
DATA_RAW = ROOT / "data" / "raw"
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_STAGING.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()

print("=" * 70)
print("  S01-1.4.1 | Diagnóstico de Datos Faltantes – Cuantificación")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga de datos
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando CSV raw y contrastando con staging...")

empresas = pd.read_csv(DATA_RAW / "empresas.csv", parse_dates=["fecha_afiliacion"])
siniestros = pd.read_csv(DATA_RAW / "siniestros.csv", parse_dates=["fecha_ocurrencia"])

emp_stg = pd.read_parquet(DATA_STAGING / "empresas_staging.parquet")
sin_stg = pd.read_parquet(DATA_STAGING / "siniestros_staging.parquet")

print(f"  empresas.csv:              {empresas.shape}")
print(f"  siniestros.csv:            {siniestros.shape}")
print(f"  empresas_staging:          {emp_stg.shape} (reutilizado)")
print(f"  siniestros_staging:        {sin_stg.shape} (reutilizado)")

# Contraste: los nulos de columnas raw deben coincidir en staging
for col in empresas.columns:
    n_raw = int(empresas[col].isna().sum())
    n_stg = int(emp_stg[col].isna().sum()) if col in emp_stg.columns else None
    if n_stg is not None and n_raw != n_stg:
        print(f"  ⚠ Diferencia nulos empresas.{col}: raw={n_raw} vs staging={n_stg}")

for col in siniestros.columns:
    n_raw = int(siniestros[col].isna().sum())
    n_stg = int(sin_stg[col].isna().sum()) if col in sin_stg.columns else None
    if n_stg is not None and n_raw != n_stg:
        print(f"  ⚠ Diferencia nulos siniestros.{col}: raw={n_raw} vs staging={n_stg}")


# ──────────────────────────────────────────────────
# 2. Helpers de cuantificación
# ──────────────────────────────────────────────────
def resumen_columnas(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Tabla una fila por columna con conteos y tasas de faltantes."""
    n = len(df)
    rows = []
    for col in df.columns:
        n_miss = int(df[col].isna().sum())
        rows.append(
            {
                "dataset": dataset,
                "columna": col,
                "dtype": str(df[col].dtype),
                "n_filas": n,
                "n_faltantes": n_miss,
                "n_completos": n - n_miss,
                "pct_faltantes": round(100.0 * n_miss / n, 4) if n else np.nan,
                "pct_completos": round(100.0 * (n - n_miss) / n, 4) if n else np.nan,
                "tiene_faltantes": n_miss > 0,
            }
        )
    return pd.DataFrame(rows)


def resumen_dataset(df: pd.DataFrame, dataset: str) -> dict:
    """KPIs de completitud a nivel dataset."""
    n_cells = df.shape[0] * df.shape[1]
    n_miss_cells = int(df.isna().sum().sum())
    n_rows_any = int(df.isna().any(axis=1).sum())
    n_cols_any = int(df.isna().any(axis=0).sum())
    return {
        "dataset": dataset,
        "n_filas": df.shape[0],
        "n_columnas": df.shape[1],
        "n_celdas": n_cells,
        "n_celdas_faltantes": n_miss_cells,
        "pct_celdas_faltantes": round(100.0 * n_miss_cells / n_cells, 4),
        "pct_completitud_celdas": round(100.0 * (1 - n_miss_cells / n_cells), 4),
        "n_filas_con_algun_faltante": n_rows_any,
        "pct_filas_con_algun_faltante": round(100.0 * n_rows_any / df.shape[0], 4),
        "n_columnas_con_faltantes": n_cols_any,
        "columnas_con_faltantes": ", ".join(
            df.columns[df.isna().any()].tolist()
        ),
    }


def patrones_faltantes(
    df: pd.DataFrame, cols: list[str], dataset: str
) -> pd.DataFrame:
    """Conteo de combinaciones de presencia/ausencia en columnas con nulos."""
    miss = df[cols].isna()
    # clave binaria estable (orden de cols)
    key = miss.astype(int).astype(str).agg("".join, axis=1)
    counts = key.value_counts(dropna=False).rename_axis("patron_binario").reset_index(name="n_filas")
    counts["dataset"] = dataset
    counts["pct_filas"] = round(100.0 * counts["n_filas"] / len(df), 4)
    # expandir bits a columnas legibles
    for i, c in enumerate(cols):
        counts[f"miss_{c}"] = counts["patron_binario"].str[i].astype(int).astype(bool)
    counts["n_columnas_faltantes_en_patron"] = counts["patron_binario"].str.count("1")
    counts["descripcion"] = counts.apply(
        lambda r: (
            "completo"
            if r["n_columnas_faltantes_en_patron"] == 0
            else "faltan: "
            + ", ".join(c for c in cols if r[f"miss_{c}"])
        ),
        axis=1,
    )
    cols_out = (
        ["dataset", "patron_binario", "descripcion", "n_filas", "pct_filas", "n_columnas_faltantes_en_patron"]
        + [f"miss_{c}" for c in cols]
    )
    return counts[cols_out].sort_values("n_filas", ascending=False).reset_index(drop=True)


def tasas_estrato(
    df: pd.DataFrame,
    group_col: str,
    target_cols: list[str],
    dataset: str,
) -> pd.DataFrame:
    """Tasa de faltantes de target_cols estratificada por group_col."""
    rows = []
    for g, gdf in df.groupby(group_col, observed=True):
        n = len(gdf)
        for t in target_cols:
            n_miss = int(gdf[t].isna().sum())
            rows.append(
                {
                    "dataset": dataset,
                    "estrato_variable": group_col,
                    "estrato_valor": str(g),
                    "columna": t,
                    "n_filas": n,
                    "n_faltantes": n_miss,
                    "pct_faltantes": round(100.0 * n_miss / n, 4) if n else np.nan,
                }
            )
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────
# 3. Cuantificación principal
# ──────────────────────────────────────────────────
print("\n[CUANT] Resumen por columna y dataset...")

res_cols = pd.concat(
    [
        resumen_columnas(empresas, "empresas"),
        resumen_columnas(siniestros, "siniestros"),
    ],
    ignore_index=True,
)

res_ds = pd.DataFrame(
    [
        resumen_dataset(empresas, "empresas"),
        resumen_dataset(siniestros, "siniestros"),
    ]
)

emp_miss_cols = ["ciudad", "departamento", "prima_anual"]
sin_miss_cols = ["parte_cuerpo", "dias_incapacidad", "costo_asistencial"]

pat_emp = patrones_faltantes(empresas, emp_miss_cols, "empresas")
pat_sin = patrones_faltantes(siniestros, sin_miss_cols, "siniestros")
patrones = pd.concat([pat_emp, pat_sin], ignore_index=True)

# Estratos relevantes (señales para MAR en 1.4.2, aquí solo cuantificación)
estratos = pd.concat(
    [
        tasas_estrato(empresas, "clase_riesgo", ["prima_anual", "ciudad"], "empresas"),
        tasas_estrato(empresas, "sector", ["prima_anual", "ciudad"], "empresas"),
        tasas_estrato(siniestros, "tipo", sin_miss_cols, "siniestros"),
        tasas_estrato(siniestros, "gravedad", sin_miss_cols, "siniestros"),
    ],
    ignore_index=True,
)

# Impresión compacta
print("\n  --- Completitud por dataset ---")
for _, r in res_ds.iterrows():
    print(
        f"  {r['dataset']:<12} filas={r['n_filas']:,}  "
        f"celdas faltantes={r['n_celdas_faltantes']:,} "
        f"({r['pct_celdas_faltantes']:.2f}%)  "
        f"filas con ≥1 nulo={r['n_filas_con_algun_faltante']:,} "
        f"({r['pct_filas_con_algun_faltante']:.2f}%)"
    )

print("\n  --- Columnas con faltantes ---")
for _, r in res_cols[res_cols["tiene_faltantes"]].iterrows():
    print(
        f"  {r['dataset']}.{r['columna']:<28} "
        f"{r['n_faltantes']:>6,}  ({r['pct_faltantes']:5.2f}%)"
    )

print("\n  --- Patrones (empresas: ciudad|departamento|prima) ---")
for _, r in pat_emp.iterrows():
    print(f"  {r['patron_binario']}  n={r['n_filas']:>5,}  ({r['pct_filas']:5.2f}%)  {r['descripcion']}")

print("\n  --- Patrones (siniestros: parte|dias|costo_asist) ---")
for _, r in pat_sin.iterrows():
    print(f"  {r['patron_binario']}  n={r['n_filas']:>6,}  ({r['pct_filas']:5.2f}%)  {r['descripcion']}")

# Señales estratificadas destacadas
print("\n  --- Señales estratificadas (para 1.4.2) ---")
dias_tipo = estratos[
    (estratos["dataset"] == "siniestros")
    & (estratos["estrato_variable"] == "tipo")
    & (estratos["columna"] == "dias_incapacidad")
]
costo_grav = estratos[
    (estratos["dataset"] == "siniestros")
    & (estratos["estrato_variable"] == "gravedad")
    & (estratos["columna"] == "costo_asistencial")
]
print("  dias_incapacidad × tipo:")
for _, r in dias_tipo.iterrows():
    print(f"    {r['estrato_valor']}: {r['pct_faltantes']:.2f}%")
print("  costo_asistencial × gravedad:")
for _, r in costo_grav.iterrows():
    print(f"    {r['estrato_valor']}: {r['pct_faltantes']:.2f}%")


# ──────────────────────────────────────────────────
# 4. Persistencia (results + staging)
# ──────────────────────────────────────────────────
print("\n[SAVE] Guardando tablas de resultados y staging...")

res_cols.to_csv(RESULTS_DIR / "faltantes_resumen_columnas.csv", index=False, encoding="utf-8")
patrones.to_csv(RESULTS_DIR / "faltantes_patrones.csv", index=False, encoding="utf-8")
estratos.to_csv(RESULTS_DIR / "faltantes_por_estrato.csv", index=False, encoding="utf-8")
res_ds.to_csv(RESULTS_DIR / "faltantes_resumen_datasets.csv", index=False, encoding="utf-8")

res_cols.to_parquet(DATA_STAGING / "faltantes_resumen_columnas.parquet", index=False)
patrones.to_parquet(DATA_STAGING / "faltantes_patrones.parquet", index=False)
estratos.to_parquet(DATA_STAGING / "faltantes_por_estrato.parquet", index=False)
res_ds.to_parquet(DATA_STAGING / "faltantes_resumen_datasets.parquet", index=False)

print("  ✓ results/*.csv y data/staging/S01/faltantes_*.parquet")


# ──────────────────────────────────────────────────
# 5. Visualizaciones
# ──────────────────────────────────────────────────
print("\n[PLOT] Generando figuras...")

# ── 5.1 Barras % faltantes por columna (ambos datasets) ──
miss_only = res_cols[res_cols["tiene_faltantes"]].copy()
miss_only["etiqueta"] = miss_only["dataset"] + "." + miss_only["columna"]
miss_only = miss_only.sort_values("pct_faltantes", ascending=True)

fig, ax = plt.subplots(figsize=(10, 5.5))
colors_bar = [
    sb.AZUL_SURA.hex if d == "empresas" else sb.AQUA_SURA.hex
    for d in miss_only["dataset"]
]
bars = ax.barh(miss_only["etiqueta"], miss_only["pct_faltantes"], color=colors_bar, alpha=0.9)
ax.set_xlabel("% de filas con valor faltante")
ax.set_title("Cuantificación de datos faltantes por columna")
ax.axvline(5, color=sb.GRIS_MEDIO.hex, ls="--", lw=1, label="5%")
ax.axvline(10, color="#B85C38", ls="--", lw=1, label="10%")
for bar, pct, n in zip(bars, miss_only["pct_faltantes"], miss_only["n_faltantes"]):
    ax.text(
        bar.get_width() + 0.3,
        bar.get_y() + bar.get_height() / 2,
        f"{pct:.1f}% (n={n:,})",
        va="center",
        fontsize=8,
    )
ax.set_xlim(0, max(miss_only["pct_faltantes"].max() * 1.35, 15))
ax.legend(
    handles=[
        Patch(facecolor=sb.AZUL_SURA.hex, label="empresas"),
        Patch(facecolor=sb.AQUA_SURA.hex, label="siniestros"),
        plt.Line2D([0], [0], color=sb.GRIS_MEDIO.hex, ls="--", label="umbral 5%"),
        plt.Line2D([0], [0], color="#B85C38", ls="--", label="umbral 10%"),
    ],
    fontsize=8,
    loc="lower right",
)
sb.add_sura_footer(fig, text="S01-1.4.1 | Cuantificación faltantes – por columna")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_faltantes_por_columna.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_faltantes_por_columna.png")

# ── 5.2 Completitud KPI + filas afectadas ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Completitud global y filas afectadas",
    subtitle=(
        f"empresas: {res_ds.loc[0, 'pct_completitud_celdas']:.2f}% celdas completas · "
        f"siniestros: {res_ds.loc[1, 'pct_completitud_celdas']:.2f}% celdas completas"
    ),
)
ax1, ax2 = axes[0], axes[1]

x = np.arange(2)
w = 0.35
ax1.bar(
    x - w / 2,
    res_ds["pct_completitud_celdas"],
    w,
    color=sb.AZUL_SURA.hex,
    label="% celdas completas",
)
ax1.bar(
    x + w / 2,
    100 - res_ds["pct_filas_con_algun_faltante"],
    w,
    color=sb.AQUA_SURA.hex,
    label="% filas 100% completas",
)
ax1.set_xticks(x)
ax1.set_xticklabels(res_ds["dataset"])
ax1.set_ylabel("%")
ax1.set_ylim(80, 105)
ax1.set_title("Completitud")
# Leyenda fuera del área de barras para no tapar etiquetas de datos
ax1.legend(
    fontsize=7,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.16),
    ncol=2,
    frameon=False,
)
for i, row in res_ds.iterrows():
    v_celdas = float(row["pct_completitud_celdas"])
    v_filas = float(100 - row["pct_filas_con_algun_faltante"])
    ax1.text(i - w / 2, v_celdas + 0.5, f"{v_celdas:.1f}%", ha="center", va="bottom", fontsize=8)
    ax1.text(i + w / 2, v_filas + 0.5, f"{v_filas:.1f}%", ha="center", va="bottom", fontsize=8)

ax2.bar(
    res_ds["dataset"],
    res_ds["n_filas_con_algun_faltante"],
    color=[sb.AZUL_SURA.hex, sb.AQUA_SURA.hex],
    alpha=0.9,
)
ax2.set_ylabel("N° filas con ≥1 faltante")
ax2.set_title("Filas afectadas")
ymax2 = float(res_ds["n_filas_con_algun_faltante"].max())
ax2.set_ylim(0, ymax2 * 1.18)
for i, row in res_ds.iterrows():
    ax2.text(
        i,
        row["n_filas_con_algun_faltante"] + ymax2 * 0.02,
        f"{int(row['n_filas_con_algun_faltante']):,}\n({row['pct_filas_con_algun_faltante']:.1f}%)",
        ha="center",
        va="bottom",
        fontsize=8,
    )

sb.add_sura_footer(fig, text="S01-1.4.1 | Completitud global")
fig.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(IMGS_DIR / "01_completitud_datasets.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_completitud_datasets.png")

# ── 5.3 Patrones de co-ocurrencia ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Patrones de co-ocurrencia de faltantes",
    subtitle="Combinaciones de columnas ausentes en la misma fila (excluye filas completas)",
)

for ax, pat, title in [
    (axes[0], pat_emp, "empresas\n(ciudad | departamento | prima)"),
    (axes[1], pat_sin, "siniestros\n(parte | días | costo_asist.)"),
]:
    plot_df = pat[pat["n_columnas_faltantes_en_patron"] > 0].copy()
    labels = plot_df["descripcion"].str.replace("faltan: ", "", regex=False)
    ax.barh(labels, plot_df["n_filas"], color=sb.AZUL_SURA.hex if "empresa" in title else sb.AQUA_SURA.hex)
    ax.set_xlabel("N° filas")
    ax.set_title(title, fontsize=10)
    for y, (n, pct) in enumerate(zip(plot_df["n_filas"], plot_df["pct_filas"])):
        ax.text(n + max(plot_df["n_filas"]) * 0.02, y, f"{n:,} ({pct:.1f}%)", va="center", fontsize=7)
    ax.invert_yaxis()

sb.add_sura_footer(fig, text="S01-1.4.1 | Patrones de faltantes")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_patrones_coocurrencia.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_patrones_coocurrencia.png")

# ── 5.4 Tasas estratificadas (señales) ──
fig, axes = sb.create_dashboard(
    1,
    2,
    title="Tasas de faltantes estratificadas (señales para mecanismo)",
    subtitle=(
        "dias_incapacidad × tipo  ·  costo_asistencial × gravedad  "
        "(cuantificación; clasificación MCAR/MAR/MNAR en 1.4.2)"
    ),
)
ax1, ax2 = axes[0], axes[1]

# dias × tipo
sub = dias_tipo.sort_values("estrato_valor")
ax1.bar(sub["estrato_valor"], sub["pct_faltantes"], color=sb.AQUA_SURA.hex, alpha=0.9)
ax1.set_ylabel("% faltantes")
ax1.set_title("dias_incapacidad por tipo")
ax1.set_ylim(0, max(sub["pct_faltantes"].max() * 1.25, 15))
for i, (_, r) in enumerate(sub.iterrows()):
    ax1.text(i, r["pct_faltantes"] + 0.4, f"{r['pct_faltantes']:.1f}%", ha="center", fontsize=9)

# costo × gravedad — orden lógico
orden_grav = ["leve", "grave", "mortal"]
sub2 = costo_grav.copy()
sub2["orden"] = sub2["estrato_valor"].map({v: i for i, v in enumerate(orden_grav)})
sub2 = sub2.sort_values("orden")
ax2.bar(sub2["estrato_valor"], sub2["pct_faltantes"], color=sb.AZUL_SURA.hex, alpha=0.9)
ax2.set_ylabel("% faltantes")
ax2.set_title("costo_asistencial por gravedad")
ax2.set_ylim(0, max(sub2["pct_faltantes"].max() * 1.2, 40))
for i, (_, r) in enumerate(sub2.iterrows()):
    ax2.text(i, r["pct_faltantes"] + 0.8, f"{r['pct_faltantes']:.1f}%", ha="center", fontsize=9)

sb.add_sura_footer(fig, text="S01-1.4.1 | Faltantes estratificados")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_faltantes_estratificados.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_faltantes_estratificados.png")

# ── 5.5 Matriz binaria de faltantes (muestra) ──
# Muestra aleatoria de filas con al menos un nulo, para visualizar estructura
rng = np.random.default_rng(RANDOM_SEED)

fig, axes = sb.create_dashboard(
    1,
    2,
    title="Matriz de faltantes (muestra de filas incompletas)",
    subtitle="Amarillo = faltante · Azul = presente  |  muestra aleatoria de hasta 200 filas con ≥1 nulo",
)

for ax, df, miss_cols, name in [
    (axes[0], empresas, emp_miss_cols, "empresas"),
    (axes[1], siniestros, sin_miss_cols, "siniestros"),
]:
    idx = df.index[df[miss_cols].isna().any(axis=1)].to_numpy()
    take = min(200, len(idx))
    sample_idx = rng.choice(idx, size=take, replace=False)
    sample_idx = np.sort(sample_idx)
    mat = df.loc[sample_idx, miss_cols].isna().astype(int).T  # cols × filas
    im = ax.imshow(mat.values, aspect="auto", cmap="YlOrBr", vmin=0, vmax=1, interpolation="nearest")
    ax.set_yticks(range(len(miss_cols)))
    ax.set_yticklabels(miss_cols, fontsize=8)
    ax.set_xlabel(f"Filas incompletas (muestra n={take})")
    ax.set_title(name)
    ax.set_xticks([])

sb.add_sura_footer(fig, text="S01-1.4.1 | Matriz visual de faltantes")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMGS_DIR / "01_matriz_faltantes_muestra.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_matriz_faltantes_muestra.png")


print("\n" + "=" * 70)
print("  Ejecución completada exitosamente.")
print("=" * 70)
print("\n  Archivos generados:")
print("    results/imgs/01_faltantes_por_columna.png")
print("    results/imgs/01_completitud_datasets.png")
print("    results/imgs/01_patrones_coocurrencia.png")
print("    results/imgs/01_faltantes_estratificados.png")
print("    results/imgs/01_matriz_faltantes_muestra.png")
print("    results/faltantes_resumen_columnas.csv")
print("    results/faltantes_patrones.csv")
print("    results/faltantes_por_estrato.csv")
print("    results/faltantes_resumen_datasets.csv")
print("    data/staging/S01/faltantes_resumen_columnas.parquet")
print("    data/staging/S01/faltantes_patrones.parquet")
print("    data/staging/S01/faltantes_por_estrato.parquet")
print("    data/staging/S01/faltantes_resumen_datasets.parquet")
