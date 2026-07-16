"""
Definición de Baseline – Cuantificación de métricas
===================================================
Sección: S01 – Metodología, EDA y Análisis
Subsección: 1.5 – Definición de baseline
Proceso: 1.5.1 – Simulación del predictor baseline y métricas

Descripción:
    Simula un clasificador binario baseline para predecir
    `alta_siniestralidad` (Top 10% de empresas por n_siniestros
    dentro del año) en el último año disponible (T):

      ŷ_i(T) = 1  si la empresa i estuvo en el Top 10% en T−1
      ŷ_i(T) = 0  en caso contrario

    Métricas reportadas (sobre y_true del año T):
      · AUC-ROC
      · Sensibilidad (Recall)
      · Precisión
      · F1-Score

    Además se reporta la matriz de confusión y, como contexto,
    las mismas métricas en pares históricos t → t+1.

Inputs (reutilizados — no se regeneran):
    - data/staging/S01/temporal_empresa_anio.parquet
    - data/staging/S01/temporal_persistencia_yoy.parquet  (trazabilidad)
    - data/staging/S01/hip_p10_retencion_top10.parquet   (trazabilidad)

Outputs:
    - results/imgs/01_baseline_*.png
    - results/baseline_*.csv
    - data/staging/S01/baseline_predicciones.parquet
    - data/staging/S01/baseline_metricas.parquet
    - data/staging/S01/baseline_confusion.parquet

Uso:
    .venv/bin/python "sections/S01-Metodologia_EDA_Analisis/1_5_Definición de baseline/code/01-cuantificacion_baseline/cuantificacion_baseline.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[5]
DATA_STAGING = ROOT / "data" / "staging" / "S01"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"
DATA_STAGING.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()


def _roc_curve_binary(y_true: np.ndarray, y_score: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """ROC y AUC (Mann–Whitney / trapecio) sin depender de scikit-learn."""
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score).astype(float)
    order = np.argsort(-y_score, kind="mergesort")
    y_true = y_true[order]
    y_score = y_score[order]

    n_pos = int(y_true.sum())
    n_neg = int(len(y_true) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0]), 0.5

    # Puntos en cambios de score
    distinct = np.where(np.diff(y_score))[0]
    thresholds_idx = np.r_[distinct, len(y_true) - 1]

    tps = np.cumsum(y_true)[thresholds_idx]
    fps = (1 + thresholds_idx) - tps
    tpr = np.r_[0.0, tps / n_pos]
    fpr = np.r_[0.0, fps / n_neg]
    # Cerrar en (1,1) si hace falta
    if fpr[-1] < 1.0 or tpr[-1] < 1.0:
        fpr = np.r_[fpr, 1.0]
        tpr = np.r_[tpr, 1.0]
    auc_val = float(np.trapezoid(tpr, fpr))
    return fpr, tpr, auc_val


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray) -> dict:
    """Métricas de clasificación binaria + matriz de confusión."""
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    y_score = np.asarray(y_score).astype(float)

    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tp = int(((y_true == 1) & (y_pred == 1)).sum())

    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    _, _, auc_roc = _roc_curve_binary(y_true, y_score)

    return {
        "n": int(len(y_true)),
        "n_positivos_true": int(y_true.sum()),
        "n_positivos_pred": int(y_pred.sum()),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "auc_roc": float(auc_roc),
        "recall": float(recall),
        "precision": float(precision),
        "f1": float(f1),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else np.nan,
        "accuracy": float((tp + tn) / len(y_true)) if len(y_true) else np.nan,
    }


print("=" * 70)
print("  S01-1.5.1 | Baseline: Top 10% del año previo → año T")
print("=" * 70)

# ──────────────────────────────────────────────────
# 1. Carga (reutiliza staging existente)
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando staging reutilizado...")
panel = pd.read_parquet(DATA_STAGING / "temporal_empresa_anio.parquet")
persist = pd.read_parquet(DATA_STAGING / "temporal_persistencia_yoy.parquet")
hip_p10 = pd.read_parquet(DATA_STAGING / "hip_p10_retencion_top10.parquet")

anios = sorted(panel["anio"].unique())
anio_eval = int(anios[-1])
anio_prev = int(anios[-2])
print(f"  Panel empresa×año: {panel.shape} | años {anios[0]}–{anios[-1]}")
print(f"  Año de evaluación (T): {anio_eval} | Año predictor (T−1): {anio_prev}")
print(f"  Persistencia YoY (trazabilidad): {persist.shape}")
print(f"  hip_p10 retención (trazabilidad): {hip_p10.shape}")


def build_pair(df: pd.DataFrame, y_prev: int, y_eval: int) -> pd.DataFrame:
    """Une labels de T−1 (predicción) con labels de T (verdad)."""
    left = (
        df.loc[df["anio"] == y_prev, ["id_empresa", "alta_siniestralidad", "n_siniestros"]]
        .rename(
            columns={
                "alta_siniestralidad": "y_pred",
                "n_siniestros": "n_siniestros_prev",
            }
        )
    )
    right = (
        df.loc[df["anio"] == y_eval, ["id_empresa", "alta_siniestralidad", "n_siniestros", "clase_riesgo", "sector"]]
        .rename(
            columns={
                "alta_siniestralidad": "y_true",
                "n_siniestros": "n_siniestros_eval",
            }
        )
    )
    out = left.merge(right, on="id_empresa", how="inner")
    out["anio_prev"] = y_prev
    out["anio_eval"] = y_eval
    # Score del baseline = etiqueta dura del año previo (0/1)
    out["y_score"] = out["y_pred"].astype(float)
    return out


# ──────────────────────────────────────────────────
# 2. Predicción baseline en el último año
# ──────────────────────────────────────────────────
print(f"\n[BASELINE] Predicción ŷ={anio_prev} Top10% → y={anio_eval}...")
pred_eval = build_pair(panel, anio_prev, anio_eval)
metrics_eval = _binary_metrics(
    pred_eval["y_true"].to_numpy(),
    pred_eval["y_pred"].to_numpy(),
    pred_eval["y_score"].to_numpy(),
)

print(
    f"  n={metrics_eval['n']} | positivas true={metrics_eval['n_positivos_true']} "
    f"| pred={metrics_eval['n_positivos_pred']}"
)
print(
    f"  TP={metrics_eval['tp']} FP={metrics_eval['fp']} "
    f"FN={metrics_eval['fn']} TN={metrics_eval['tn']}"
)
print(
    f"  AUC-ROC={metrics_eval['auc_roc']:.4f} | "
    f"Recall={metrics_eval['recall']:.4f} | "
    f"Precision={metrics_eval['precision']:.4f} | "
    f"F1={metrics_eval['f1']:.4f}"
)

# ──────────────────────────────────────────────────
# 3. Contexto: mismas métricas en pares históricos
# ──────────────────────────────────────────────────
print("\n[CONTEXTO] Métricas baseline en pares históricos t → t+1...")
hist_rows = []
for y1, y2 in zip(anios[:-1], anios[1:]):
    pair = build_pair(panel, int(y1), int(y2))
    m = _binary_metrics(
        pair["y_true"].to_numpy(),
        pair["y_pred"].to_numpy(),
        pair["y_score"].to_numpy(),
    )
    m["anio_prev"] = int(y1)
    m["anio_eval"] = int(y2)
    m["es_evaluacion_principal"] = int(y2) == anio_eval
    m["regla"] = "top10_anio_previo"
    hist_rows.append(m)
    tag = " ★" if m["es_evaluacion_principal"] else ""
    print(
        f"  {y1}→{y2}: AUC={m['auc_roc']:.3f}  Rec={m['recall']:.3f}  "
        f"Prec={m['precision']:.3f}  F1={m['f1']:.3f}{tag}"
    )

metricas = pd.DataFrame(hist_rows)
metricas = metricas[
    [
        "anio_prev",
        "anio_eval",
        "es_evaluacion_principal",
        "regla",
        "n",
        "n_positivos_true",
        "n_positivos_pred",
        "tp",
        "fp",
        "fn",
        "tn",
        "auc_roc",
        "recall",
        "precision",
        "f1",
        "specificity",
        "accuracy",
    ]
]

confusion = pd.DataFrame(
    [
        {
            "anio_prev": anio_prev,
            "anio_eval": anio_eval,
            "celda": celda,
            "n": metrics_eval[celda],
            "descripcion": desc,
        }
        for celda, desc in [
            ("tp", "Verdaderos positivos: Top10% en T−1 y en T"),
            ("fp", "Falsos positivos: Top10% en T−1 pero no en T"),
            ("fn", "Falsos negativos: no Top10% en T−1 pero sí en T"),
            ("tn", "Verdaderos negativos: fuera del Top10% en T−1 y en T"),
        ]
    ]
)

# Dataset de predicciones (solo evaluación principal)
predicciones = pred_eval[
    [
        "id_empresa",
        "anio_prev",
        "anio_eval",
        "y_true",
        "y_pred",
        "y_score",
        "n_siniestros_prev",
        "n_siniestros_eval",
        "clase_riesgo",
        "sector",
    ]
].copy()
predicciones["regla"] = "top10_anio_previo"
predicciones["acierto"] = (predicciones["y_true"] == predicciones["y_pred"]).astype(int)

# ──────────────────────────────────────────────────
# 4. Persistencia staging + CSV
# ──────────────────────────────────────────────────
print("\n[SAVE] Staging + CSV...")
predicciones.to_parquet(DATA_STAGING / "baseline_predicciones.parquet", index=False)
metricas.to_parquet(DATA_STAGING / "baseline_metricas.parquet", index=False)
confusion.to_parquet(DATA_STAGING / "baseline_confusion.parquet", index=False)

predicciones.to_csv(RESULTS_DIR / "baseline_predicciones.csv", index=False, encoding="utf-8")
metricas.to_csv(RESULTS_DIR / "baseline_metricas.csv", index=False, encoding="utf-8")
confusion.to_csv(RESULTS_DIR / "baseline_confusion.csv", index=False, encoding="utf-8")
print("  ✓ baseline_{predicciones,metricas,confusion}")

# ──────────────────────────────────────────────────
# 5. Plots
# ──────────────────────────────────────────────────
print("\n[PLOT] Figuras...")
palette = sb.get_palette("categorical")
azul, aqua = sb.AZUL_SURA.hex, sb.AQUA_SURA.hex
amarillo = sb.AMARILLO_SURA.hex
profundo = sb.AZUL_PROFUNDO.hex

# ── 5.1 Matriz de confusión (año T) ──
fig, ax = plt.subplots(figsize=(7.2, 6.0))
cm = np.array(
    [[metrics_eval["tn"], metrics_eval["fp"]], [metrics_eval["fn"], metrics_eval["tp"]]],
    dtype=float,
)
cmap_cm = LinearSegmentedColormap.from_list(
    "sura_blues", ["#FFFFFF", aqua, azul, profundo]
)
im = ax.imshow(cm, cmap=cmap_cm)
for (i, j), val in np.ndenumerate(cm):
    text_color = "white" if val > cm.max() * 0.55 else profundo
    ax.text(j, i, f"{int(val):,}", ha="center", va="center", fontsize=16, fontweight="bold", color=text_color)
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(["No top 10%", "Top 10%"])
ax.set_yticklabels(["No top 10%", "Top 10%"])
ax.set_xlabel("Predicción (Top 10% año previo)")
ax.set_ylabel("Real (Top 10% año evaluación)")
ax.set_title(
    f"Matriz de confusión — Baseline {anio_prev}→{anio_eval}",
    fontsize=13,
    fontweight="bold",
    color=profundo,
)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
sb.add_sura_footer(
    fig,
    text=f"Regla: ŷ(T)=alta_siniestralidad(T−1) · n={metrics_eval['n']:,}",
)
fig.tight_layout()
fig.savefig(IMGS_DIR / "01_baseline_confusion.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_baseline_confusion.png")

# ── 5.2 Curva ROC ──
fpr, tpr, roc_auc = _roc_curve_binary(
    pred_eval["y_true"].to_numpy(),
    pred_eval["y_score"].to_numpy(),
)

fig, ax = plt.subplots(figsize=(7.2, 6.0))
ax.plot(fpr, tpr, color=azul, lw=2.5, label=f"Baseline (AUC = {roc_auc:.3f})")
ax.plot([0, 1], [0, 1], color=sb.GRIS_MEDIO.hex, ls="--", lw=1.5, label="Azar (AUC = 0.50)")
# Marcar el único umbral operativo (score 0/1)
ax.scatter(
    [metrics_eval["fp"] / (metrics_eval["fp"] + metrics_eval["tn"])],
    [metrics_eval["recall"]],
    s=80,
    color=aqua,
    zorder=5,
    label=f"Umbral operativo (Rec={metrics_eval['recall']:.2f})",
)
ax.set_xlim(-0.02, 1.02)
ax.set_ylim(-0.02, 1.02)
ax.set_xlabel("1 − Especificidad (FPR)")
ax.set_ylabel("Sensibilidad (TPR / Recall)")
ax.set_title(
    f"Curva ROC — Baseline Top 10% previo ({anio_prev}→{anio_eval})",
    fontsize=13,
    fontweight="bold",
    color=profundo,
)
ax.legend(loc="lower right", frameon=False)
ax.set_aspect("equal")
sb.add_sura_footer(
    fig,
    text="Score = etiqueta dura del año previo (0/1); ROC con 3 puntos característicos",
)
fig.tight_layout()
fig.savefig(IMGS_DIR / "01_baseline_roc.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_baseline_roc.png")

# ── 5.3 Barras de métricas principales ──
metric_labels = ["AUC-ROC", "Recall", "Precisión", "F1-Score"]
metric_vals = [
    metrics_eval["auc_roc"],
    metrics_eval["recall"],
    metrics_eval["precision"],
    metrics_eval["f1"],
]
colors_m = [azul, aqua, profundo, amarillo]

fig, ax = plt.subplots(figsize=(8.0, 5.2))
bars = ax.bar(metric_labels, metric_vals, color=colors_m, width=0.62, edgecolor="white")
ax.axhline(0.5, color=sb.GRIS_MEDIO.hex, ls="--", lw=1, label="Referencia 0.50 (azar)")
ax.set_ylim(0, 1.05)
ax.set_ylabel("Valor")
ax.set_title(
    f"Métricas del baseline — evaluación {anio_eval}",
    fontsize=13,
    fontweight="bold",
    color=profundo,
)
for b, v in zip(bars, metric_vals):
    ax.text(
        b.get_x() + b.get_width() / 2,
        v + 0.03,
        f"{v:.3f}",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color=profundo,
    )
ax.legend(loc="upper right", frameon=False)
sb.add_sura_footer(
    fig,
    text=f"ŷ = mismas empresas Top 10% de {anio_prev} · prevalencia target = 10%",
)
fig.tight_layout()
fig.savefig(IMGS_DIR / "01_baseline_metricas.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_baseline_metricas.png")

# ── 5.4 Serie histórica de métricas ──
fig, ax = plt.subplots(figsize=(9.0, 5.4))
x_labels = [f"{r.anio_prev}→{r.anio_eval}" for r in metricas.itertuples()]
x = np.arange(len(metricas))
ax.plot(x, metricas["auc_roc"], "o-", color=azul, lw=2, label="AUC-ROC")
ax.plot(x, metricas["recall"], "s-", color=aqua, lw=2, label="Recall")
ax.plot(x, metricas["precision"], "^-", color=profundo, lw=2, label="Precisión")
ax.plot(x, metricas["f1"], "D-", color="#B85C38", lw=2, label="F1")
# Destacar año de evaluación
ax.axvline(len(metricas) - 1, color=amarillo, ls="--", lw=1.5, alpha=0.8, label=f"Eval. {anio_eval}")
ax.set_xticks(x)
ax.set_xticklabels(x_labels, rotation=20, ha="right")
ax.set_ylim(0.3, 0.85)
ax.set_ylabel("Valor")
ax.set_title(
    "Estabilidad del baseline en pares YoY",
    fontsize=13,
    fontweight="bold",
    color=profundo,
)
ax.legend(loc="lower left", ncol=3, frameon=False, fontsize=9)
sb.add_sura_footer(fig, text="Misma regla en todos los pares: Top 10% de t predice Top 10% de t+1")
fig.tight_layout()
fig.savefig(IMGS_DIR / "01_baseline_metricas_historicas.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_baseline_metricas_historicas.png")

# ── 5.5 Panel resumen ejecutivo ──
fig, ax = plt.subplots(figsize=(9.0, 5.0))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")
ax.set_title(
    f"Resumen ejecutivo — Baseline clasificación binaria ({anio_prev}→{anio_eval})",
    fontsize=13,
    fontweight="bold",
    color=profundo,
    pad=12,
)

kpis = [
    ("AUC-ROC", f"{metrics_eval['auc_roc']:.3f}", azul),
    ("Recall", f"{metrics_eval['recall']:.3f}", aqua),
    ("Precisión", f"{metrics_eval['precision']:.3f}", profundo),
    ("F1-Score", f"{metrics_eval['f1']:.3f}", "#B85C38"),
]
for i, (lab, val, col) in enumerate(kpis):
    x0 = 0.4 + i * 2.4
    box = FancyBboxPatch(
        (x0, 5.8),
        2.1,
        3.2,
        boxstyle="round,pad=0.05,rounding_size=0.2",
        facecolor=col,
        alpha=0.12,
        edgecolor=col,
        lw=1.5,
    )
    ax.add_patch(box)
    ax.text(x0 + 1.05, 8.2, val, ha="center", va="center", fontsize=20, fontweight="bold", color=col)
    ax.text(x0 + 1.05, 6.5, lab, ha="center", va="center", fontsize=11, color=profundo)

notes = [
    f"Regla: predecir como positivas las {metrics_eval['n_positivos_pred']} empresas del Top 10% de {anio_prev}.",
    f"Verdaderos positivos: {metrics_eval['tp']} · Falsos positivos: {metrics_eval['fp']} · "
    f"Falsos negativos: {metrics_eval['fn']}.",
    f"Retención observada (= Recall = Precisión bajo prevalencia 10% simétrica): {metrics_eval['recall']:.1%}.",
    "Un modelo más complejo debe superar estas métricas de forma estable en validación temporal.",
]
for i, txt in enumerate(notes):
    ax.text(0.4, 4.6 - i * 1.0, f"• {txt}", ha="left", va="center", fontsize=10, color="#333333")

sb.add_sura_footer(fig, text="Línea base CRISP-DM · S01-1.5.1")
fig.tight_layout()
fig.savefig(IMGS_DIR / "01_baseline_resumen.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  ✓ 01_baseline_resumen.png")

# ──────────────────────────────────────────────────
# 6. Cierre
# ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  RESULTADO PRINCIPAL (evaluación último año)")
print("=" * 70)
print(f"  Año evaluación : {anio_eval} (predictor = Top 10% de {anio_prev})")
print(f"  AUC-ROC        : {metrics_eval['auc_roc']:.4f}")
print(f"  Recall         : {metrics_eval['recall']:.4f}")
print(f"  Precisión      : {metrics_eval['precision']:.4f}")
print(f"  F1-Score       : {metrics_eval['f1']:.4f}")
print(f"\n  Plots → {IMGS_DIR}")
print(f"  Staging → {DATA_STAGING}/baseline_*.parquet")
print("  ✅  1.5.1 completado")
