"""
Prototipo del recomendador híbrido (Diseño C)
=============================================
Sección: S05 – Sistema Recomendador
Subsección: 5.2 – Implementación de prototipo
Proceso: 5.2.1 – Prototipo funcional + evaluación temporal

Descripción:
    Implementa el Diseño C (híbrido adopción × riesgo con enrutamiento
    warm/cold) seleccionado en 5.1.1. Entrena con usos ≤2023, evalúa en
    2024 y calibra α sobre la frontera NDCG@5 vs ΔRisk@5.

    Score:
        score = α · score_adopcion + (1-α) · score_riesgo
        warm  → CF item–item (+ mezcla contenido)
        cold  → contenido + popularidad de segmento

Inputs:
    - data/raw/uso_servicios.csv, catalogo_servicios.csv
    - data/staging/S05/recomendador_empresas_features.parquet
    - data/staging/S03/modelo_pred_empresa.parquet (costo_pred)

Outputs:
    - data/staging/S05/prototipo_*.parquet
    - results/imgs/01_prototipo_*.png
    - results/prototipo_recomendador.md (escrito aparte)

Uso:
    .venv/bin/python \\
      "sections/S05-Sistema_Recomendador/5_2_Implementacion de prototipo/code/01-prototipo/01-prototipo.py"
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

import sura_brand as sb

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────
RANDOM_SEED = 42
K = 5
TRAIN_END = pd.Timestamp("2023-12-31")
TEST_START = pd.Timestamp("2024-01-01")
ALPHAS = np.round(np.linspace(0.0, 1.0, 11), 2)
N_COLD_SIM = 500  # empresas warm evaluadas como cold (rama contenido)

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data" / "raw"
DATA_S03 = ROOT / "data" / "staging" / "S03"
DATA_S05 = ROOT / "data" / "staging" / "S05"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_S05.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(RANDOM_SEED)
sb.apply_sura_style()
PAL = sb.get_palette("categorical")

print("=" * 70)
print("  S05-5.2.1 | Prototipo Diseño C — híbrido + eval temporal")
print("=" * 70)


def save_parquet(df: pd.DataFrame, name: str) -> None:
    path = DATA_S05 / name
    df.to_parquet(path, index=False)
    print(f"  [staging] {path.relative_to(ROOT)}  ({df.shape[0]}×{df.shape[1]})")


def save_fig(fig: plt.Figure, name: str) -> None:
    path = IMGS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] {path.relative_to(ROOT)}")


# ──────────────────────────────────────────────────
# 1. Carga
# ──────────────────────────────────────────────────
print("\n[DATOS] Cargando raw + staging...")
uso = pd.read_csv(RAW / "uso_servicios.csv", parse_dates=["fecha_uso"])
cat = pd.read_csv(RAW / "catalogo_servicios.csv")
emp = pd.read_parquet(DATA_S05 / "recomendador_empresas_features.parquet")

risk = pd.read_parquet(DATA_S03 / "modelo_pred_empresa.parquet")
risk = risk.loc[risk["horizonte"] == "holdout_2024", ["id_empresa", "costo_pred"]].drop_duplicates(
    "id_empresa"
)
emp = emp.merge(risk, on="id_empresa", how="left")
if "score_riesgo_s03" not in emp.columns:
    emp["score_riesgo_s03"] = emp["costo_pred"]
else:
    emp["score_riesgo_s03"] = emp["score_riesgo_s03"].fillna(emp["costo_pred"])

emp["clase_label"] = "Clase " + emp["clase_riesgo"].astype(str)
emp = emp.set_index("id_empresa", drop=False)

svc_ids = sorted(cat["id_servicio"].tolist())
svc_index = {s: i for i, s in enumerate(svc_ids)}
n_svc = len(svc_ids)

cat = cat.set_index("id_servicio", drop=False)
CAT_RISK = {
    "Seguridad": 1.00,
    "Emergencias": 0.90,
    "Ergonomia": 0.80,
    "Formacion": 0.60,
    "Salud": 0.55,
    "Psicosocial": 0.50,
}
svc_risk = np.array([CAT_RISK.get(cat.loc[s, "categoria"], 0.4) for s in svc_ids], dtype=float)
svc_risk_n = svc_risk / (svc_risk.max() + 1e-12)

print(f"  uso={len(uso):,}  emp={len(emp):,}  servicios={n_svc}")

# ──────────────────────────────────────────────────
# 2. Split temporal
# ──────────────────────────────────────────────────
print("\n[SPLIT] Train ≤2023 / Test 2024...")
uso_train = uso.loc[uso["fecha_uso"] <= TRAIN_END].copy()
uso_test = uso.loc[uso["fecha_uso"] >= TEST_START].copy()

train_pairs = (
    uso_train.groupby(["id_empresa", "id_servicio"], as_index=False)
    .size()
    .rename(columns={"size": "n_usos"})
)
test_pairs = (
    uso_test.groupby(["id_empresa", "id_servicio"], as_index=False)
    .size()
    .rename(columns={"size": "n_usos"})
)

train_by_emp = train_pairs.groupby("id_empresa")["id_servicio"].apply(set).to_dict()
test_by_emp = test_pairs.groupby("id_empresa")["id_servicio"].apply(set).to_dict()

warm_train_ids = sorted(train_by_emp.keys())
true_cold_ids = sorted(emp.loc[emp["es_cold"] == 1, "id_empresa"].tolist())

# Ground truth: servicios en test no vistos en train (nuevas adopciones)
gt_new = {}
for e, test_set in test_by_emp.items():
    known = train_by_emp.get(e, set())
    rel = test_set - known
    if rel:
        gt_new[e] = rel

split_diag = pd.DataFrame(
    [
        {"metrica": "n_eventos_train", "valor": len(uso_train)},
        {"metrica": "n_eventos_test", "valor": len(uso_test)},
        {"metrica": "n_pares_train", "valor": len(train_pairs)},
        {"metrica": "n_pares_test", "valor": len(test_pairs)},
        {"metrica": "n_warm_train", "valor": len(warm_train_ids)},
        {"metrica": "n_true_cold", "valor": len(true_cold_ids)},
        {"metrica": "n_emp_con_gt_nuevas", "valor": len(gt_new)},
        {"metrica": "mediana_gt_nuevas", "valor": float(np.median([len(v) for v in gt_new.values()]))},
    ]
)
save_parquet(split_diag, "prototipo_split_temporal.parquet")
print(
    f"  train_evt={len(uso_train):,}  test_evt={len(uso_test):,}  "
    f"warm_train={len(warm_train_ids)}  gt_nuevas={len(gt_new)}  true_cold={len(true_cold_ids)}"
)

# ──────────────────────────────────────────────────
# 3. Señales de adopción (train only)
# ──────────────────────────────────────────────────
print("\n[SEÑALES] Popularidad, contenido, CF item–item...")

# Popularidad global train
pop_counts = train_pairs.groupby("id_servicio")["n_usos"].sum().reindex(svc_ids).fillna(0.0)
pop_n = (pop_counts / (pop_counts.sum() + 1e-12)).to_numpy(dtype=float)

# Popularidad por sector
train_w = train_pairs.merge(emp[["sector"]], left_on="id_empresa", right_index=True, how="left")
pop_sector = {}
for sector, g in train_w.groupby("sector"):
    s = g.groupby("id_servicio")["n_usos"].sum().reindex(svc_ids).fillna(0.0)
    tot = s.sum()
    pop_sector[sector] = (s / tot).to_numpy(dtype=float) if tot > 0 else pop_n.copy()

# Match contenido empresa × servicio
dirigido = cat["dirigido_a"].to_dict()


def content_score_vec(emp_id: str) -> np.ndarray:
    row = emp.loc[emp_id]
    sector, clase = row["sector"], row["clase_label"]
    match = np.array(
        [1.0 if dirigido[s] in (sector, clase) else 0.0 for s in svc_ids], dtype=float
    )
    ps = pop_sector.get(sector, pop_n)
    # normalizar componentes
    match_n = match / (match.max() + 1e-12) if match.max() > 0 else match
    scores = 0.6 * match_n + 0.4 * ps
    return scores


# Matriz CF train
emp_idx = {e: i for i, e in enumerate(warm_train_ids)}
rows = train_pairs["id_empresa"].map(emp_idx).to_numpy()
cols = train_pairs["id_servicio"].map(svc_index).to_numpy()
data = np.log1p(train_pairs["n_usos"].to_numpy(dtype=float))
R = sparse.csr_matrix((data, (rows, cols)), shape=(len(warm_train_ids), n_svc))
item_sim = cosine_similarity(R.T)
np.fill_diagonal(item_sim, 0.0)


def cf_score_vec(known: set[str]) -> np.ndarray:
    if not known:
        return pop_n.copy()
    scores = np.zeros(n_svc, dtype=float)
    for s in known:
        if s in svc_index:
            scores += item_sim[svc_index[s]]
    if scores.max() <= 0:
        return pop_n.copy()
    return scores / (scores.max() + 1e-12)


def risk_score_vec(emp_id: str) -> np.ndarray:
    """Prior de servicio × intensidad de riesgo de la empresa."""
    clase = float(emp.loc[emp_id, "clase_riesgo"])
    costo = float(emp.loc[emp_id, "score_riesgo_s03"])
    # intensidad empresa en [0.5, 1.5] vía clase + percentil costo
    costo_rank = emp["score_riesgo_s03"].rank(pct=True).loc[emp_id]
    intensity = 0.5 + 0.3 * (clase / 5.0) + 0.2 * float(costo_rank)
    return svc_risk_n * intensity


def adoption_score_vec(emp_id: str, known: set[str], mode: str) -> np.ndarray:
    """mode: warm | cold"""
    content = content_score_vec(emp_id)
    content_n = content / (content.max() + 1e-12)
    if mode == "cold" or len(known) == 0:
        return content_n
    cf = cf_score_vec(known)
    return 0.7 * cf + 0.3 * content_n


def hybrid_scores(emp_id: str, known: set[str], alpha: float, mode: str) -> np.ndarray:
    adopt = adoption_score_vec(emp_id, known, mode)
    risk = risk_score_vec(emp_id)
    risk_n = risk / (risk.max() + 1e-12)
    return alpha * adopt + (1.0 - alpha) * risk_n


def popularity_scores(_emp_id: str) -> np.ndarray:
    return pop_n.copy()


def topk_ids(scores: np.ndarray, exclude: set[str], k: int = K) -> list[str]:
    sc = scores.copy()
    for s in exclude:
        if s in svc_index:
            sc[svc_index[s]] = -np.inf
    # si todo -inf, no excluir
    if not np.isfinite(sc).any():
        sc = scores.copy()
    order = np.argpartition(-sc, range(min(k, n_svc)))[:k]
    order = order[np.argsort(-sc[order])]
    return [svc_ids[i] for i in order if np.isfinite(sc[i])][:k]


# ──────────────────────────────────────────────────
# 4. Métricas
# ──────────────────────────────────────────────────
def dcg_at_k(rels: list[int], k: int) -> float:
    return sum(rel / np.log2(i + 2) for i, rel in enumerate(rels[:k]))


def ndcg_at_k(recommended: list[str], relevant: set[str], k: int = K) -> float:
    rels = [1 if s in relevant else 0 for s in recommended[:k]]
    dcg = dcg_at_k(rels, k)
    n_rel = min(len(relevant), k)
    idcg = dcg_at_k([1] * n_rel, k)
    return float(dcg / idcg) if idcg > 0 else 0.0


def recall_at_k(recommended: list[str], relevant: set[str], k: int = K) -> float:
    if not relevant:
        return np.nan
    hit = len(set(recommended[:k]) & relevant)
    return hit / len(relevant)


def risk_at_k(recommended: list[str], k: int = K) -> float:
    if not recommended:
        return np.nan
    vals = [svc_risk_n[svc_index[s]] for s in recommended[:k] if s in svc_index]
    return float(np.mean(vals)) if vals else np.nan


def evaluate_users(
    user_ids: list[str],
    alpha: float,
    mode: str,
    use_gt: bool = True,
    scorer: str = "hybrid",
) -> dict:
    """Evalúa un conjunto de empresas. mode fuerza warm/cold en hybrid."""
    ndcgs, recalls, risks, risks_pop = [], [], [], []
    n_with_k = 0
    rec_items: set[str] = set()
    n_eval = 0

    for emp_id in user_ids:
        known = train_by_emp.get(emp_id, set()) if mode == "warm" else set()
        # en cold simulado ocultamos historial
        if mode == "cold":
            known_score = set()
        else:
            known_score = known

        relevant = gt_new.get(emp_id, set()) if use_gt else set()
        exclude = known  # no recomendar ya adoptados en train

        if scorer == "hybrid":
            scores = hybrid_scores(emp_id, known_score, alpha, mode)
        elif scorer == "popularity":
            scores = popularity_scores(emp_id)
        elif scorer == "content":
            scores = content_score_vec(emp_id)
        elif scorer == "cf":
            scores = cf_score_vec(known_score if known_score else known)
        else:
            raise ValueError(scorer)

        rec = topk_ids(scores, exclude=exclude, k=K)
        if len(rec) >= K:
            n_with_k += 1
        rec_items.update(rec)

        risks.append(risk_at_k(rec, K))
        # baseline popularidad con mismo exclude
        rec_pop = topk_ids(popularity_scores(emp_id), exclude=exclude, k=K)
        risks_pop.append(risk_at_k(rec_pop, K))

        if use_gt and relevant:
            ndcgs.append(ndcg_at_k(rec, relevant, K))
            recalls.append(recall_at_k(rec, relevant, K))
            n_eval += 1

    out = {
        "n_users": len(user_ids),
        "n_eval_gt": n_eval,
        "ndcg_at_5": float(np.nanmean(ndcgs)) if ndcgs else np.nan,
        "recall_at_5": float(np.nanmean(recalls)) if recalls else np.nan,
        "risk_at_5": float(np.nanmean(risks)) if risks else np.nan,
        "risk_pop_at_5": float(np.nanmean(risks_pop)) if risks_pop else np.nan,
        "delta_risk_at_5": float(np.nanmean(risks) - np.nanmean(risks_pop))
        if risks and risks_pop
        else np.nan,
        "coverage": len(rec_items) / n_svc,
        "pct_with_k_valid": n_with_k / max(len(user_ids), 1),
    }
    return out


# ──────────────────────────────────────────────────
# 5. Cohortes de evaluación
# ──────────────────────────────────────────────────
# Warm: empresas con train y GT nuevas en 2024
warm_eval_ids = sorted(e for e in gt_new if e in train_by_emp)

# Cold simulado: muestra de warm_eval evaluada con rama cold (sin historial)
rng = np.random.default_rng(RANDOM_SEED)
cold_sim_ids = sorted(
    rng.choice(warm_eval_ids, size=min(N_COLD_SIM, len(warm_eval_ids)), replace=False).tolist()
)

print(
    f"  cohortes: warm_eval={len(warm_eval_ids)}  cold_sim={len(cold_sim_ids)}  "
    f"true_cold={len(true_cold_ids)}"
)

# ──────────────────────────────────────────────────
# 6. Calibración de α
# ──────────────────────────────────────────────────
print("\n[α] Barrido NDCG@5 vs ΔRisk@5...")
alpha_rows = []
for a in ALPHAS:
    warm_m = evaluate_users(warm_eval_ids, alpha=float(a), mode="warm", scorer="hybrid")
    cold_m = evaluate_users(cold_sim_ids, alpha=float(a), mode="cold", scorer="hybrid")
    true_cold_m = evaluate_users(
        true_cold_ids, alpha=float(a), mode="cold", use_gt=False, scorer="hybrid"
    )
    alpha_rows.append(
        {
            "alpha": float(a),
            "warm_ndcg_at_5": warm_m["ndcg_at_5"],
            "warm_recall_at_5": warm_m["recall_at_5"],
            "warm_delta_risk_at_5": warm_m["delta_risk_at_5"],
            "warm_risk_at_5": warm_m["risk_at_5"],
            "warm_coverage": warm_m["coverage"],
            "cold_sim_ndcg_at_5": cold_m["ndcg_at_5"],
            "cold_sim_recall_at_5": cold_m["recall_at_5"],
            "cold_sim_delta_risk_at_5": cold_m["delta_risk_at_5"],
            "true_cold_coverage": true_cold_m["coverage"],
            "true_cold_pct_k_valid": true_cold_m["pct_with_k_valid"],
            "true_cold_risk_at_5": true_cold_m["risk_at_5"],
            "true_cold_delta_risk_at_5": true_cold_m["delta_risk_at_5"],
        }
    )
    print(
        f"  α={a:.2f}  warm NDCG={warm_m['ndcg_at_5']:.4f}  "
        f"ΔRisk={warm_m['delta_risk_at_5']:+.4f}  "
        f"cold_sim NDCG={cold_m['ndcg_at_5']:.4f}"
    )

alpha_df = pd.DataFrame(alpha_rows)
save_parquet(alpha_df, "prototipo_alpha_curve.parquet")

# Selección de α: maximizar ΔRisk sujeto a NDCG ≥ 95% del máximo NDCG
ndcg_max = alpha_df["warm_ndcg_at_5"].max()
ndcg_floor = 0.95 * ndcg_max
candidatos = alpha_df.loc[alpha_df["warm_ndcg_at_5"] >= ndcg_floor].copy()
# entre candidatos, máximo ΔRisk; si empate, α más cercano a 0.55
candidatos["dist_055"] = (candidatos["alpha"] - 0.55).abs()
best = candidatos.sort_values(
    ["warm_delta_risk_at_5", "warm_ndcg_at_5", "dist_055"],
    ascending=[False, False, True],
).iloc[0]
alpha_star = float(best["alpha"])
print(
    f"\n  α*={alpha_star:.2f}  "
    f"(NDCG≥{ndcg_floor:.4f}={0.95:.0%}·max; ΔRisk={best['warm_delta_risk_at_5']:+.4f})"
)

# ──────────────────────────────────────────────────
# 7. Evaluación final @ α* + baselines
# ──────────────────────────────────────────────────
print("\n[EVAL] Métricas finales @ α* + baselines...")

rows_metrics = []


def add_metrics(tag: str, cohort: str, res: dict, alpha: float | None = None) -> None:
    rows_metrics.append(
        {
            "modelo": tag,
            "cohorte": cohort,
            "alpha": alpha,
            **res,
        }
    )


# Hybrid C @ α*
for cohort, ids, mode, use_gt in [
    ("warm", warm_eval_ids, "warm", True),
    ("cold_sim", cold_sim_ids, "cold", True),
    ("true_cold", true_cold_ids, "cold", False),
]:
    res = evaluate_users(ids, alpha=alpha_star, mode=mode, use_gt=use_gt, scorer="hybrid")
    add_metrics("C_hibrido", cohort, res, alpha_star)

# Baselines en warm
for tag, scorer in [
    ("popularidad", "popularity"),
    ("A_contenido", "content"),
    ("B_cf", "cf"),
]:
    res = evaluate_users(warm_eval_ids, alpha=alpha_star, mode="warm", scorer=scorer)
    add_metrics(tag, "warm", res, None)
    # cold_sim para contenido/popularidad
    if scorer in ("popularity", "content"):
        res_c = evaluate_users(cold_sim_ids, alpha=alpha_star, mode="cold", scorer=scorer)
        add_metrics(tag, "cold_sim", res_c, None)

metrics_df = pd.DataFrame(rows_metrics)
save_parquet(metrics_df, "prototipo_metricas.parquet")

# Resumen ejecutivo
c_warm = metrics_df.query("modelo=='C_hibrido' and cohorte=='warm'").iloc[0]
c_cold = metrics_df.query("modelo=='C_hibrido' and cohorte=='cold_sim'").iloc[0]
c_tc = metrics_df.query("modelo=='C_hibrido' and cohorte=='true_cold'").iloc[0]
pop_warm = metrics_df.query("modelo=='popularidad' and cohorte=='warm'").iloc[0]

resumen = pd.DataFrame(
    [
        {
            "alpha_star": alpha_star,
            "regla_alpha": "max ΔRisk@5 s.t. NDCG@5 ≥ 95% del máximo en curva",
            "ndcg_floor": ndcg_floor,
            "warm_ndcg_at_5": c_warm["ndcg_at_5"],
            "warm_recall_at_5": c_warm["recall_at_5"],
            "warm_delta_risk_at_5": c_warm["delta_risk_at_5"],
            "warm_coverage": c_warm["coverage"],
            "cold_sim_ndcg_at_5": c_cold["ndcg_at_5"],
            "cold_sim_recall_at_5": c_cold["recall_at_5"],
            "cold_sim_delta_risk_at_5": c_cold["delta_risk_at_5"],
            "true_cold_pct_k_valid": c_tc["pct_with_k_valid"],
            "true_cold_coverage": c_tc["coverage"],
            "true_cold_delta_risk_at_5": c_tc["delta_risk_at_5"],
            "pop_warm_ndcg_at_5": pop_warm["ndcg_at_5"],
            "pop_warm_recall_at_5": pop_warm["recall_at_5"],
            "n_warm_eval": int(c_warm["n_eval_gt"]),
            "n_cold_sim": int(c_cold["n_users"]),
            "n_true_cold": int(c_tc["n_users"]),
            "k": K,
        }
    ]
)
save_parquet(resumen, "prototipo_resumen.parquet")

print(
    f"  C warm: NDCG={c_warm['ndcg_at_5']:.4f}  Recall={c_warm['recall_at_5']:.4f}  "
    f"ΔRisk={c_warm['delta_risk_at_5']:+.4f}  cov={c_warm['coverage']:.2%}"
)
print(
    f"  C cold_sim: NDCG={c_cold['ndcg_at_5']:.4f}  Recall={c_cold['recall_at_5']:.4f}"
)
print(
    f"  true_cold: pct_K={c_tc['pct_with_k_valid']:.1%}  cov={c_tc['coverage']:.2%}  "
    f"ΔRisk={c_tc['delta_risk_at_5']:+.4f}"
)

# ──────────────────────────────────────────────────
# 8. Recomendaciones finales (todas las empresas @ α*)
# ──────────────────────────────────────────────────
print("\n[RECS] Generando top-5 para 5 000 empresas...")
all_hist = uso.groupby("id_empresa")["id_servicio"].apply(set).to_dict()
rec_rows = []
for emp_id in emp["id_empresa"].tolist():
    is_cold = bool(emp.loc[emp_id, "es_cold"] == 1) or emp_id not in train_by_emp
    mode = "cold" if is_cold else "warm"
    if not is_cold:
        # Excluir ya usados; CF solo con train (sin leakage del test 2024)
        exclude = all_hist.get(emp_id, set())
        known_score = train_by_emp.get(emp_id, set())
    else:
        exclude = set()
        known_score = set()

    scores = hybrid_scores(emp_id, known_score, alpha_star, mode)
    rec = topk_ids(scores, exclude=exclude, k=K)
    for rank, s in enumerate(rec, start=1):
        rec_rows.append(
            {
                "id_empresa": emp_id,
                "id_servicio": s,
                "rank": rank,
                "score": float(scores[svc_index[s]]),
                "modo": mode,
                "alpha": alpha_star,
                "categoria": cat.loc[s, "categoria"],
                "servicio": cat.loc[s, "servicio"],
            }
        )

recs_df = pd.DataFrame(rec_rows)
save_parquet(recs_df, "prototipo_recomendaciones.parquet")

# Limitaciones documentadas
lims = pd.DataFrame(
    [
        {
            "id": "L1",
            "limitacion": "Sin ground truth de adopción para true-cold (500 empresas nunca usadas)",
            "impacto": "NDCG/Recall cold solo vía cold_sim; true_cold solo guardrails/riesgo",
        },
        {
            "id": "L2",
            "limitacion": "ΔRisk es proxy de categoría×perfil, no efecto causal post-adopción",
            "impacto": "No demuestra reducción real de siniestros; alinea intención preventiva",
        },
        {
            "id": "L3",
            "limitacion": "Offline ignora posición/capacidad operativa y canibalización de canales",
            "impacto": "Métricas de ranking pueden sobreestimar valor de negocio en producción",
        },
        {
            "id": "L4",
            "limitacion": "Feedback implícito ≠ preferencia; reuso puede ser hábito/contrato",
            "impacto": "CF puede reforzar head items ya populares",
        },
        {
            "id": "L5",
            "limitacion": "Un solo corte temporal 2023/2024; sin validación rolling",
            "impacto": "Sensibilidad a shocks 2024 no cuantificada",
        },
        {
            "id": "L6",
            "limitacion": "α calibrado en warm; cold usa la misma α en rama contenido",
            "impacto": "Óptimo cold puede diferir; monitorizar en 5.3",
        },
    ]
)
save_parquet(lims, "prototipo_limitaciones.parquet")

# ──────────────────────────────────────────────────
# 9. Figuras
# ──────────────────────────────────────────────────
print("\n[FIGS] Generando visualizaciones...")

# 9.1 Curva α
fig, ax1 = plt.subplots(figsize=(8.5, 4.8))
ax2 = ax1.twinx()
ax1.plot(
    alpha_df["alpha"],
    alpha_df["warm_ndcg_at_5"],
    color=PAL[0],
    marker="o",
    label="NDCG@5 warm",
)
ax2.plot(
    alpha_df["alpha"],
    alpha_df["warm_delta_risk_at_5"],
    color=PAL[2],
    marker="s",
    label="ΔRisk@5 vs pop",
)
ax1.axvline(alpha_star, color=PAL[1], ls="--", lw=1.2, label=f"α*={alpha_star:.2f}")
ax1.axhline(ndcg_floor, color=PAL[0], ls=":", alpha=0.5, label="piso 95% NDCG máx")
ax1.set_xlabel("α (peso adopción)")
ax1.set_ylabel("NDCG@5", color=PAL[0])
ax2.set_ylabel("ΔRisk@5", color=PAL[2])
ax1.set_title("Calibración de α — frontera adopción vs riesgo (warm)")
lines1, lab1 = ax1.get_legend_handles_labels()
lines2, lab2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, lab1 + lab2, frameon=False, loc="best", fontsize=8)
sb.add_sura_footer(fig, "Regla: max ΔRisk s.t. NDCG@5 ≥ 95% del máximo")
save_fig(fig, "01_prototipo_alpha_curve.png")

# 9.2 Scatter frontera
fig, ax = plt.subplots(figsize=(7.2, 4.8))
ax.scatter(
    alpha_df["warm_ndcg_at_5"],
    alpha_df["warm_delta_risk_at_5"],
    c=[PAL[0]] * len(alpha_df),
    s=60,
)
for _, r in alpha_df.iterrows():
    ax.annotate(
        f"{r['alpha']:.1f}",
        (r["warm_ndcg_at_5"], r["warm_delta_risk_at_5"]),
        textcoords="offset points",
        xytext=(4, 4),
        fontsize=8,
    )
ax.scatter(
    [best["warm_ndcg_at_5"]],
    [best["warm_delta_risk_at_5"]],
    s=140,
    facecolors="none",
    edgecolors=PAL[2],
    linewidths=2,
    label=f"α*={alpha_star:.2f}",
)
ax.set_xlabel("NDCG@5 (warm)")
ax.set_ylabel("ΔRisk@5 vs popularidad")
ax.set_title("Frontera NDCG@5 vs ΔRisk@5")
ax.legend(frameon=False)
sb.add_sura_footer(fig, "Cada punto = un α ∈ {0.0,…,1.0}")
save_fig(fig, "01_prototipo_alpha_frontier.png")

# 9.3 Primarias warm/cold
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.5))
labels = ["Warm", "Cold sim"]
ndcg_vals = [c_warm["ndcg_at_5"], c_cold["ndcg_at_5"]]
rec_vals = [c_warm["recall_at_5"], c_cold["recall_at_5"]]
axes[0].bar(labels, ndcg_vals, color=[PAL[0], PAL[1]], edgecolor="none")
axes[0].set_ylim(0, max(ndcg_vals) * 1.25 + 1e-6)
axes[0].set_title("NDCG@5")
for i, v in enumerate(ndcg_vals):
    axes[0].text(i, v + 0.005, f"{v:.3f}", ha="center")
axes[1].bar(labels, rec_vals, color=[PAL[0], PAL[1]], edgecolor="none")
axes[1].set_ylim(0, max(rec_vals) * 1.25 + 1e-6)
axes[1].set_title("Recall@5")
for i, v in enumerate(rec_vals):
    axes[1].text(i, v + 0.005, f"{v:.3f}", ha="center")
fig.suptitle(f"Métricas primarias Diseño C @ α*={alpha_star:.2f}", y=1.02)
sb.add_sura_footer(fig, "Cold sim: historial oculto; GT = nuevas adopciones 2024")
save_fig(fig, "01_prototipo_metricas_primarias.png")

# 9.4 Comparación vs baselines (warm)
fig, ax = plt.subplots(figsize=(8.5, 4.8))
base = metrics_df.query("cohorte=='warm'").copy()
order = ["popularidad", "A_contenido", "B_cf", "C_hibrido"]
base["modelo"] = pd.Categorical(base["modelo"], categories=order, ordered=True)
base = base.sort_values("modelo")
x = np.arange(len(base))
w = 0.35
ax.bar(x - w / 2, base["ndcg_at_5"], w, label="NDCG@5", color=PAL[0])
ax.bar(x + w / 2, base["recall_at_5"], w, label="Recall@5", color=PAL[1])
ax.set_xticks(x)
ax.set_xticklabels(["Popularidad", "A Contenido", "B CF", "C Híbrido"])
ax.set_ylabel("Score")
ax.set_title("Adopción offline (warm, test 2024) — C vs baselines")
ax.legend(frameon=False)
sb.add_sura_footer(fig, "Misma partición temporal train≤2023 / test 2024")
save_fig(fig, "01_prototipo_vs_baselines.png")

# 9.5 ΔRisk
fig, ax = plt.subplots(figsize=(8.0, 4.5))
delta_vals = [
    pop_warm["delta_risk_at_5"],
    metrics_df.query("modelo=='A_contenido' and cohorte=='warm'").iloc[0]["delta_risk_at_5"],
    metrics_df.query("modelo=='B_cf' and cohorte=='warm'").iloc[0]["delta_risk_at_5"],
    c_warm["delta_risk_at_5"],
]
ax.bar(
    ["Popularidad", "A Contenido", "B CF", "C Híbrido"],
    delta_vals,
    color=[PAL[3], PAL[0], PAL[1], PAL[2]],
    edgecolor="none",
)
ax.axhline(0, color="gray", lw=0.8)
ax.set_ylabel("ΔRisk@5 vs popularidad")
ax.set_title("Señal de negocio — prior preventivo del top-5")
for i, v in enumerate(delta_vals):
    ax.text(i, v + (0.005 if v >= 0 else -0.015), f"{v:+.3f}", ha="center", fontsize=9)
sb.add_sura_footer(fig, "Risk = media del prior de categoría de servicios en top-5")
save_fig(fig, "01_prototipo_delta_risk.png")

# 9.6 Guardrails
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.5))
axes[0].bar(
    ["Warm", "Cold sim", "True cold"],
    [c_warm["coverage"], c_cold["coverage"], c_tc["coverage"]],
    color=[PAL[0], PAL[1], PAL[2]],
    edgecolor="none",
)
axes[0].set_ylim(0, 1.05)
axes[0].set_ylabel("Coverage (fracción del catálogo)")
axes[0].set_title("Coverage@recomendaciones")
for i, v in enumerate([c_warm["coverage"], c_cold["coverage"], c_tc["coverage"]]):
    axes[0].text(i, v + 0.02, f"{v:.0%}", ha="center")

axes[1].bar(
    ["True cold\n% con K=5"],
    [c_tc["pct_with_k_valid"]],
    color=PAL[2],
    edgecolor="none",
)
axes[1].set_ylim(0, 1.05)
axes[1].set_title("Guardrail cold real")
axes[1].text(0, c_tc["pct_with_k_valid"] + 0.02, f"{c_tc['pct_with_k_valid']:.0%}", ha="center")
fig.suptitle("Guardrails de cobertura", y=1.02)
sb.add_sura_footer(fig, f"Catálogo={n_svc} servicios · true cold n={len(true_cold_ids)}")
save_fig(fig, "01_prototipo_guardrails.png")

# 9.7 Mix categorías en recomendaciones C
fig, ax = plt.subplots(figsize=(7.5, 4.5))
mix = recs_df.groupby("categoria").size().sort_values(ascending=False)
ax.barh(mix.index, mix.values, color=PAL[1], edgecolor="none")
ax.invert_yaxis()
ax.set_xlabel("Recomendaciones (rank≤5, todas las empresas)")
ax.set_title(f"Mix de categorías recomendadas @ α*={alpha_star:.2f}")
sb.add_sura_footer(fig, "Diseño C desplaza masa hacia categorías de mayor prior preventivo")
save_fig(fig, "01_prototipo_mix_categorias.png")

print("\n" + "=" * 70)
print(f"  LISTO — prototipo C @ α*={alpha_star:.2f}")
print("=" * 70)
