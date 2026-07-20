"""
Diseño del recomendador de servicios de prevención
==================================================
Sección: S05 – Sistema Recomendador
Subsección: 5.1 – Diseño de recomendador
Proceso: 5.1.1 – Análisis de datos y comparación de tres diseños

Descripción:
    Perfila uso_servicios / catalogo_servicios / empresas, cuantifica
    cobertura, densidad, arranque en frío y alineación contenido↔perfil,
    y compara tres diseños candidatos para que el área elija el enfoque
    a prototipar en 5.2.

Diseños evaluados:
    A. Basado en contenido + popularidad de segmento (cold-start nativo)
    B. Filtrado colaborativo item–item (señal de adopción)
    C. Híbrido adopción × riesgo con enrutamiento warm/cold

Inputs:
    - data/raw/uso_servicios.csv
    - data/raw/catalogo_servicios.csv
    - data/raw/empresas.csv
    - data/staging/S01/empresas_imputadas.parquet (features enriquecidas)
    - data/staging/S03/modelo_pred_empresa.parquet (proxy de riesgo; opcional)

Outputs:
    - data/staging/S05/recomendador_*.parquet
    - results/imgs/01_diseño_*.png
    - results/diseño_recomendador.md (escrito aparte)

Uso:
    .venv/bin/python \\
      "sections/S05-Sistema_Recomendador/5_1_Diseño de recomendador/code/01-diseños/01-diseños.py"
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
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data" / "raw"
DATA_S01 = ROOT / "data" / "staging" / "S01"
DATA_S03 = ROOT / "data" / "staging" / "S03"
DATA_S05 = ROOT / "data" / "staging" / "S05"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
IMGS_DIR = RESULTS_DIR / "imgs"

DATA_S05.mkdir(parents=True, exist_ok=True)
IMGS_DIR.mkdir(parents=True, exist_ok=True)

sb.apply_sura_style()
PAL = sb.get_palette("categorical")

print("=" * 70)
print("  S05-5.1.1 | Diseño del recomendador — 3 candidatos")
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
print("\n[DATOS] Cargando raw + staging S01/S03...")
uso = pd.read_csv(RAW / "uso_servicios.csv", parse_dates=["fecha_uso"])
cat = pd.read_csv(RAW / "catalogo_servicios.csv")
emp_raw = pd.read_csv(RAW / "empresas.csv")
emp = pd.read_parquet(DATA_S01 / "empresas_imputadas.parquet")

risk_path = DATA_S03 / "modelo_pred_empresa.parquet"
has_risk = risk_path.exists()
if has_risk:
    risk_raw = pd.read_parquet(risk_path)
    if "horizonte" in risk_raw.columns:
        risk = risk_raw.loc[risk_raw["horizonte"] == "holdout_2024"].copy()
    elif "anio" in risk_raw.columns:
        risk = risk_raw.loc[risk_raw["anio"] == risk_raw["anio"].max()].copy()
    else:
        risk = risk_raw.copy()
    risk = risk.drop_duplicates(subset=["id_empresa"], keep="last")
    risk_cols = [c for c in risk.columns if c != "id_empresa"]
    print(f"  Riesgo S03 disponible: n={len(risk)} cols={risk_cols[:8]}")
else:
    risk = None
    print("  Riesgo S03 no disponible — proxy por clase_riesgo")

print(f"  uso={uso.shape}  cat={cat.shape}  emp={emp.shape}")
print(f"  periodo uso: {uso['fecha_uso'].min().date()} → {uso['fecha_uso'].max().date()}")

# ──────────────────────────────────────────────────
# 2. Perfil de interacción y cold-start
# ──────────────────────────────────────────────────
print("\n[PERFIL] Interacciones y arranque en frío...")

warm_ids = set(uso["id_empresa"].unique())
all_ids = set(emp["id_empresa"].unique())
cold_ids = all_ids - warm_ids

uso["anio"] = uso["fecha_uso"].dt.year
uso["mes"] = uso["fecha_uso"].dt.to_period("M").astype(str)

pairs = (
    uso.groupby(["id_empresa", "id_servicio"], as_index=False)
    .agg(n_usos=("fecha_uso", "size"), primera=("fecha_uso", "min"), ultima=("fecha_uso", "max"))
)
n_serv = cat["id_servicio"].nunique()
n_emp = emp["id_empresa"].nunique()
n_warm = len(warm_ids)
n_cold = len(cold_ids)
n_pairs = len(pairs)
density_all = n_pairs / (n_emp * n_serv)
density_warm = n_pairs / (n_warm * n_serv)

svc_per_emp = pairs.groupby("id_empresa")["id_servicio"].nunique()
uso_per_emp = uso.groupby("id_empresa").size()
pop_svc = uso.groupby("id_servicio").size().rename("n_usos")

perfil = pd.DataFrame(
    [
        {"metrica": "n_empresas", "valor": n_emp},
        {"metrica": "n_empresas_warm", "valor": n_warm},
        {"metrica": "n_empresas_cold", "valor": n_cold},
        {"metrica": "pct_cold", "valor": n_cold / n_emp},
        {"metrica": "n_servicios", "valor": n_serv},
        {"metrica": "n_eventos_uso", "valor": len(uso)},
        {"metrica": "n_pares_empresa_servicio", "valor": n_pairs},
        {"metrica": "densidad_matriz_all", "valor": density_all},
        {"metrica": "densidad_matriz_warm", "valor": density_warm},
        {"metrica": "mediana_servicios_por_empresa", "valor": float(svc_per_emp.median())},
        {"metrica": "media_servicios_por_empresa", "valor": float(svc_per_emp.mean())},
        {"metrica": "mediana_usos_por_empresa", "valor": float(uso_per_emp.median())},
        {"metrica": "pct_pares_con_reuso", "valor": float((pairs["n_usos"] > 1).mean())},
        {"metrica": "anio_min", "valor": int(uso["anio"].min())},
        {"metrica": "anio_max", "valor": int(uso["anio"].max())},
    ]
)
save_parquet(perfil, "recomendador_perfil_interaccion.parquet")

# cold-start por estrato
emp["es_cold"] = emp["id_empresa"].isin(cold_ids).astype(int)
cold_sector = (
    emp.groupby("sector", as_index=False)
    .agg(n=("id_empresa", "size"), n_cold=("es_cold", "sum"))
    .assign(pct_cold=lambda d: d["n_cold"] / d["n"])
    .sort_values("n_cold", ascending=False)
)
cold_clase = (
    emp.groupby("clase_riesgo", as_index=False)
    .agg(n=("id_empresa", "size"), n_cold=("es_cold", "sum"))
    .assign(pct_cold=lambda d: d["n_cold"] / d["n"])
    .sort_values("clase_riesgo")
)
save_parquet(cold_sector, "recomendador_coldstart_sector.parquet")
save_parquet(cold_clase, "recomendador_coldstart_clase.parquet")

print(
    f"  warm={n_warm}  cold={n_cold} ({100*n_cold/n_emp:.1f}%)  "
    f"densidad_warm={density_warm:.3f}  mediana_svc/emp={svc_per_emp.median():.0f}"
)

# ──────────────────────────────────────────────────
# 3. Alineación contenido (dirigido_a ↔ sector/clase)
# ──────────────────────────────────────────────────
print("\n[CONTENIDO] Alineación dirigido_a ↔ perfil empresa...")

emp["clase_label"] = "Clase " + emp["clase_riesgo"].astype(str)
sectores = set(emp["sector"].unique())
clases = set(emp["clase_label"].unique())

cat = cat.copy()
cat["tipo_target"] = np.where(
    cat["dirigido_a"].isin(clases),
    "clase_riesgo",
    np.where(cat["dirigido_a"].isin(sectores), "sector", "otro"),
)

# cobertura: % empresas con ≥1 servicio "dirigido" a su sector o clase
svc_by_target = cat.groupby("dirigido_a")["id_servicio"].apply(list).to_dict()


def n_matching_services(row: pd.Series) -> int:
    keys = {row["sector"], row["clase_label"]}
    return sum(len(svc_by_target.get(k, [])) for k in keys)


emp["n_svc_match_contenido"] = emp.apply(n_matching_services, axis=1)
emp["tiene_match_contenido"] = (emp["n_svc_match_contenido"] > 0).astype(int)

# histórico: % de usos que caen en servicios matched al perfil
uso_enriched = uso.merge(
    emp[["id_empresa", "sector", "clase_label", "clase_riesgo"]],
    on="id_empresa",
    how="left",
).merge(cat[["id_servicio", "categoria", "modalidad", "dirigido_a", "tipo_target"]], on="id_servicio")
uso_enriched["match_contenido"] = (
    (uso_enriched["dirigido_a"] == uso_enriched["sector"])
    | (uso_enriched["dirigido_a"] == uso_enriched["clase_label"])
).astype(int)

contenido_diag = pd.DataFrame(
    [
        {
            "metrica": "servicios_dirigidos_a_sector",
            "valor": int((cat["tipo_target"] == "sector").sum()),
        },
        {
            "metrica": "servicios_dirigidos_a_clase",
            "valor": int((cat["tipo_target"] == "clase_riesgo").sum()),
        },
        {
            "metrica": "pct_empresas_con_match",
            "valor": float(emp["tiene_match_contenido"].mean()),
        },
        {
            "metrica": "mediana_svc_match_por_empresa",
            "valor": float(emp["n_svc_match_contenido"].median()),
        },
        {
            "metrica": "pct_usos_alineados_contenido",
            "valor": float(uso_enriched["match_contenido"].mean()),
        },
        {
            "metrica": "pct_canal_eq_modalidad",
            "valor": float((uso_enriched["canal"] == uso_enriched["modalidad"]).mean()),
        },
    ]
)
save_parquet(contenido_diag, "recomendador_contenido_diagnostico.parquet")

cat_stats = (
    cat.merge(pop_svc, on="id_servicio", how="left")
    .fillna({"n_usos": 0})
    .sort_values("n_usos", ascending=False)
)
save_parquet(cat_stats, "recomendador_catalogo_enriquecido.parquet")

print(
    f"  match empresas={emp['tiene_match_contenido'].mean():.1%}  "
    f"usos alineados={uso_enriched['match_contenido'].mean():.1%}  "
    f"svc sector/clase={ (cat['tipo_target']=='sector').sum() }/{ (cat['tipo_target']=='clase_riesgo').sum() }"
)

# ──────────────────────────────────────────────────
# 4. Matriz implícita y similaridad item–item (proxy Diseño B)
# ──────────────────────────────────────────────────
print("\n[CF] Matriz implícita + similaridad item–item...")

emp_idx = {e: i for i, e in enumerate(sorted(warm_ids))}
svc_idx = {s: i for i, s in enumerate(sorted(cat["id_servicio"]))}
svc_ids = sorted(cat["id_servicio"])
rows = pairs["id_empresa"].map(emp_idx).to_numpy()
cols = pairs["id_servicio"].map(svc_idx).to_numpy()
# feedback implícito: log1p(n_usos)
data = np.log1p(pairs["n_usos"].to_numpy(dtype=float))
R = sparse.csr_matrix((data, (rows, cols)), shape=(n_warm, n_serv))

# item-item cosine on item vectors (empresas × servicios)^T
item_sim = cosine_similarity(R.T)
np.fill_diagonal(item_sim, 0.0)
mean_topk_sim = float(np.sort(item_sim, axis=1)[:, -5:].mean())

cf_diag = pd.DataFrame(
    [
        {"metrica": "shape_usuarios_warm", "valor": n_warm},
        {"metrica": "shape_items", "valor": n_serv},
        {"metrica": "nnz", "valor": int(R.nnz)},
        {"metrica": "densidad", "valor": density_warm},
        {"metrica": "similitud_media_top5_item", "valor": mean_topk_sim},
        {"metrica": "feedback", "valor": 0.0},  # placeholder numérico
    ]
)
# guardar nota de feedback como fila texto-num via flag
cf_diag.loc[cf_diag["metrica"] == "feedback", "valor"] = np.nan
cf_diag["nota"] = ""
cf_diag.loc[cf_diag["metrica"] == "feedback", "nota"] = "log1p(n_usos) implícito"
save_parquet(cf_diag, "recomendador_cf_diagnostico.parquet")

item_sim_df = pd.DataFrame(item_sim, index=svc_ids, columns=svc_ids)
# top vecinos por servicio (long format)
nn_rows = []
for i, s in enumerate(svc_ids):
    order = np.argsort(-item_sim[i])[:5]
    for rank, j in enumerate(order, start=1):
        nn_rows.append(
            {
                "id_servicio": s,
                "vecino": svc_ids[j],
                "similitud": float(item_sim[i, j]),
                "rank": rank,
            }
        )
save_parquet(pd.DataFrame(nn_rows), "recomendador_item_neighbors.parquet")
print(f"  R={R.shape} nnz={R.nnz}  sim_top5_media={mean_topk_sim:.3f}")

# ──────────────────────────────────────────────────
# 5. Proxies offline leave-one-out (A vs B vs C)
# ──────────────────────────────────────────────────
print("\n[EVAL] Proxies leave-one-out @K (muestra warm)...")

K = 5
# sample empresas warm con ≥3 servicios distintos
eligible = svc_per_emp[svc_per_emp >= 3].index.to_numpy()
rng = np.random.default_rng(RANDOM_SEED)
sample_emps = rng.choice(eligible, size=min(800, len(eligible)), replace=False)

# popularidad global y por (sector, clase)
pop_global = pairs.groupby("id_servicio")["n_usos"].sum()
pop_global = (pop_global / pop_global.sum()).rename("p")

emp_keys = emp.set_index("id_empresa")[["sector", "clase_label", "clase_riesgo"]]
pairs_w = pairs.merge(emp_keys, left_on="id_empresa", right_index=True, how="left")

# popularidad por segmento sector
pop_sector = (
    pairs_w.groupby(["sector", "id_servicio"])["n_usos"]
    .sum()
    .groupby(level=0)
    .transform(lambda s: s / s.sum())
)

# riesgo proxy (preferir costo esperado S03; si no, clase_riesgo)
RISK_COL_PREF = ["costo_pred", "pure_premium", "loss_ratio_pred", "freq_pred"]
risk_col_used = next((c for c in RISK_COL_PREF if has_risk and c in risk.columns), None)
if risk_col_used:
    risk_score = risk.set_index("id_empresa")[risk_col_used]
else:
    risk_score = emp.set_index("id_empresa")["clase_riesgo"]
    risk_col_used = "clase_riesgo"

# score de "potencial de reducción de riesgo" por servicio:
# priorizar servicios dirigidos a clase alta / categorías Seguridad/Ergonomia/Emergencias
cat_risk_w = {
    "Seguridad": 1.0,
    "Emergencias": 0.9,
    "Ergonomia": 0.8,
    "Formacion": 0.6,
    "Salud": 0.55,
    "Psicosocial": 0.5,
}
svc_risk_prior = cat.set_index("id_servicio")["categoria"].map(cat_risk_w).fillna(0.4)


def score_design_a(emp_id: str, exclude: set[str]) -> pd.Series:
    """Contenido + popularidad de segmento."""
    row = emp_keys.loc[emp_id]
    scores = pd.Series(0.0, index=svc_ids)
    # boost por match dirigido_a
    for s, d in cat.set_index("id_servicio")["dirigido_a"].items():
        if d in (row["sector"], row["clase_label"]):
            scores[s] += 1.0
    # popularidad sector
    try:
        ps = pop_sector.loc[row["sector"]]
        scores = scores.add(ps.reindex(svc_ids).fillna(0.0), fill_value=0.0)
    except KeyError:
        scores = scores.add(pop_global.reindex(svc_ids).fillna(0.0), fill_value=0.0)
    scores.loc[list(exclude)] = -np.inf
    return scores


def score_design_b(emp_id: str, exclude: set[str], known: set[str]) -> pd.Series:
    """Item-item CF: suma similitudes a items consumidos."""
    scores = pd.Series(0.0, index=svc_ids)
    if not known:
        scores = pop_global.reindex(svc_ids).fillna(0.0)
    else:
        for s in known:
            j = svc_idx[s]
            scores = scores.add(pd.Series(item_sim[j], index=svc_ids), fill_value=0.0)
    scores.loc[list(exclude)] = -np.inf
    return scores


def score_design_c(emp_id: str, exclude: set[str], known: set[str], is_cold: bool) -> pd.Series:
    """Híbrido: α·adopción + (1-α)·riesgo; cold → más contenido."""
    if is_cold or len(known) == 0:
        adopt = score_design_a(emp_id, exclude=set())
        alpha = 0.35
    else:
        adopt = score_design_b(emp_id, exclude=set(), known=known)
        # mezclar un poco de contenido
        adopt = 0.7 * (adopt / (adopt.max() + 1e-9)) + 0.3 * (
            score_design_a(emp_id, exclude=set()) / 2.0
        )
        alpha = 0.55
    # riesgo: prior categoría × clase_riesgo normalizada de la empresa
    clase = float(emp_keys.loc[emp_id, "clase_riesgo"])
    risk_emp = clase / 5.0
    risk_part = svc_risk_prior.reindex(svc_ids).fillna(0.4) * (0.5 + 0.5 * risk_emp)
    adopt_n = adopt / (adopt.max() + 1e-9)
    risk_n = risk_part / (risk_part.max() + 1e-9)
    scores = alpha * adopt_n + (1 - alpha) * risk_n
    scores.loc[list(exclude)] = -np.inf
    return scores


def hits_at_k(scores: pd.Series, target: str, k: int = K) -> int:
    top = scores.nlargest(k).index
    return int(target in set(top))


metrics = {"A": [], "B": [], "C": []}
for emp_id in sample_emps:
    hist = set(pairs.loc[pairs["id_empresa"] == emp_id, "id_servicio"])
    # hold out one random service
    target = rng.choice(list(hist))
    known = hist - {target}
    exclude = known  # no recomendar ya usados en este proxy (excepto target held-out)
    # para ranking evaluamos si el held-out entra al top-K entre no-conocidos
    sa = score_design_a(emp_id, exclude=known)
    sb_ = score_design_b(emp_id, exclude=known, known=known)
    sc = score_design_c(emp_id, exclude=known, known=known, is_cold=False)
    metrics["A"].append(hits_at_k(sa, target))
    metrics["B"].append(hits_at_k(sb_, target))
    metrics["C"].append(hits_at_k(sc, target))

# cold-start coverage proxy: % cold con ≥K candidatos de contenido
cold_coverage = float((emp.loc[emp["es_cold"] == 1, "n_svc_match_contenido"] >= 1).mean())

eval_df = pd.DataFrame(
    [
        {
            "diseno": "A_contenido_popularidad",
            "hit_rate_at_5": float(np.mean(metrics["A"])),
            "n_eval": len(metrics["A"]),
            "cold_start_nativo": 1,
            "usa_historial": 0,
            "usa_riesgo": 0,
            "explicabilidad": 1.0,
            "cobertura_cold": cold_coverage,
        },
        {
            "diseno": "B_colaborativo_item_item",
            "hit_rate_at_5": float(np.mean(metrics["B"])),
            "n_eval": len(metrics["B"]),
            "cold_start_nativo": 0,
            "usa_historial": 1,
            "usa_riesgo": 0,
            "explicabilidad": 0.5,
            "cobertura_cold": 0.0,  # requiere fallback
        },
        {
            "diseno": "C_hibrido_adopcion_riesgo",
            "hit_rate_at_5": float(np.mean(metrics["C"])),
            "n_eval": len(metrics["C"]),
            "cold_start_nativo": 1,
            "usa_historial": 1,
            "usa_riesgo": 1,
            "explicabilidad": 0.7,
            "cobertura_cold": cold_coverage,
        },
    ]
)

# score de decisión multi-criterio (para facilitar elección)
# pesos: hit_rate 0.30, cold 0.25, dual-objetivo riesgo 0.25, explicabilidad 0.20
eval_df["score_decision"] = (
    0.30 * eval_df["hit_rate_at_5"]
    + 0.25 * eval_df["cold_start_nativo"]
    + 0.25 * eval_df["usa_riesgo"]
    + 0.20 * eval_df["explicabilidad"]
)
save_parquet(eval_df, "recomendador_diseños_evaluacion.parquet")
print(eval_df[["diseno", "hit_rate_at_5", "score_decision"]].to_string(index=False))

# ──────────────────────────────────────────────────
# 6. Fichas de diseño (metadatos)
# ──────────────────────────────────────────────────
fichas = pd.DataFrame(
    [
        {
            "diseno_id": "A",
            "nombre": "Contenido + popularidad de segmento",
            "familia": "content-based",
            "señal_principal": "atributos empresa↔servicio + popularidad en sector/clase",
            "cold_start": "nativo (100% empresas con features)",
            "warm_start": "débil (poca personalización individual)",
            "objetivo_adopcion": "parcial (popularidad de pares similares)",
            "objetivo_riesgo": "indirecto vía dirigido_a / clase",
            "complejidad": "baja",
            "stack_sugerido": "reglas + tablas de popularidad; sin modelo ML",
            "riesgo_principal": "sesgo a servicios populares; poca exploración",
            "cuando_elegir": "prioridad a explicabilidad y go-live rápido con 10% cold",
        },
        {
            "diseno_id": "B",
            "nombre": "Filtrado colaborativo item–item",
            "familia": "collaborative filtering",
            "señal_principal": "co-consumo implícito log1p(n_usos)",
            "cold_start": "no nativo — requiere fallback popularidad/contenido",
            "warm_start": "fuerte (patrones de adopción entre empresas)",
            "objetivo_adopcion": "directo (maximiza P(uso))",
            "objetivo_riesgo": "ausente",
            "complejidad": "media",
            "stack_sugerido": "item-item cosine / ALS implícito (implicit, LightFM)",
            "riesgo_principal": "500 empresas cold sin score; no alinea a reducción de riesgo",
            "cuando_elegir": "prioridad a lift de adopción en warm; cold es secundario",
        },
        {
            "diseno_id": "C",
            "nombre": "Híbrido adopción × riesgo (enrutamiento warm/cold)",
            "familia": "hybrid",
            "señal_principal": "CF (warm) + contenido (cold) + prior de riesgo (categoría×clase / S03)",
            "cold_start": "nativo vía rama contenido+riesgo",
            "warm_start": "fuerte (CF + re-rank por riesgo)",
            "objetivo_adopcion": "directo",
            "objetivo_riesgo": "directo (segundo término del score)",
            "complejidad": "media-alta",
            "stack_sugerido": "LightFM/two-tower o CF+LTR; re-rank con pure premium S03",
            "riesgo_principal": "más piezas que calibrar (α adopción/riesgo)",
            "cuando_elegir": "alineado al enunciado: adopción Y reducción de riesgo + cold-start",
        },
    ]
)
save_parquet(fichas, "recomendador_diseños_fichas.parquet")

# matriz empresa×features mínimas para futuros procesos
empresa_rec = emp[
    [
        "id_empresa",
        "sector",
        "clase_riesgo",
        "clase_label",
        "n_trabajadores",
        "antiguedad_meses",
        "es_cold",
        "n_svc_match_contenido",
        "tiene_match_contenido",
    ]
].copy()
empresa_rec["n_servicios_hist"] = empresa_rec["id_empresa"].map(svc_per_emp).fillna(0).astype(int)
empresa_rec["n_usos_hist"] = empresa_rec["id_empresa"].map(uso_per_emp).fillna(0).astype(int)
if has_risk and risk_col_used in risk.columns:
    empresa_rec = empresa_rec.merge(
        risk[["id_empresa", risk_col_used]].rename(columns={risk_col_used: "score_riesgo_s03"}),
        on="id_empresa",
        how="left",
    )
assert empresa_rec["id_empresa"].is_unique, "empresas_features debe ser 1 fila / empresa"
save_parquet(empresa_rec, "recomendador_empresas_features.parquet")

# interacciones agregadas
save_parquet(pairs, "recomendador_interacciones.parquet")

# resumen ejecutivo staging
best = eval_df.sort_values("score_decision", ascending=False).iloc[0]
resumen = pd.DataFrame(
    [
        {
            "n_empresas": n_emp,
            "n_warm": n_warm,
            "n_cold": n_cold,
            "pct_cold": n_cold / n_emp,
            "n_servicios": n_serv,
            "densidad_warm": density_warm,
            "pct_usos_alineados_contenido": float(uso_enriched["match_contenido"].mean()),
            "hit_rate_A": float(eval_df.loc[0, "hit_rate_at_5"]),
            "hit_rate_B": float(eval_df.loc[1, "hit_rate_at_5"]),
            "hit_rate_C": float(eval_df.loc[2, "hit_rate_at_5"]),
            "diseno_sugerido": best["diseno"],
            "score_decision_sugerido": float(best["score_decision"]),
            "k_eval": K,
            "n_eval_empresas": int(eval_df.loc[0, "n_eval"]),
        }
    ]
)
save_parquet(resumen, "recomendador_diseños_resumen.parquet")

# ──────────────────────────────────────────────────
# 7. Figuras
# ──────────────────────────────────────────────────
print("\n[FIGS] Generando visualizaciones...")

# 7.1 Cobertura warm/cold
fig, ax = plt.subplots(figsize=(7.5, 4.2))
vals = [n_warm, n_cold]
labels = [f"Warm\n({n_warm})", f"Cold-start\n({n_cold})"]
bars = ax.bar(labels, vals, color=[PAL[0], PAL[2]], edgecolor="none")
ax.set_ylabel("Empresas")
ax.set_title("Cobertura de histórico de uso (arranque en frío)")
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 40, f"{100*v/n_emp:.1f}%", ha="center", fontsize=10)
ax.set_ylim(0, max(vals) * 1.15)
sb.add_sura_footer(fig, "Fuente: uso_servicios.csv · empresas.csv")
save_fig(fig, "01_diseño_coldstart.png")

# 7.2 Popularidad de servicios
fig, ax = plt.subplots(figsize=(9, 4.5))
top = cat_stats.sort_values("n_usos", ascending=False)
colors = [PAL[i % len(PAL)] for i in range(len(top))]
ax.bar(range(len(top)), top["n_usos"].values, color=colors, edgecolor="none")
ax.set_xticks(range(len(top)))
ax.set_xticklabels(top["id_servicio"], rotation=90, fontsize=7)
ax.set_ylabel("Eventos de uso")
ax.set_title("Popularidad del catálogo (40 servicios)")
sb.add_sura_footer(fig, "Long-tail moderada: CF viable; contenido evita monopolio de head items")
save_fig(fig, "01_diseño_popularidad_servicios.png")

# 7.3 Usos por categoría
fig, ax = plt.subplots(figsize=(7.5, 4.2))
cat_uso = uso_enriched.groupby("categoria").size().sort_values(ascending=False)
ax.barh(cat_uso.index, cat_uso.values, color=PAL[1], edgecolor="none")
ax.invert_yaxis()
ax.set_xlabel("Eventos de uso")
ax.set_title("Demanda histórica por categoría de servicio")
sb.add_sura_footer(fig, "Prior de riesgo Diseño C pondera Seguridad / Emergencias / Ergonomía")
save_fig(fig, "01_diseño_uso_categoria.png")

# 7.4 Alineación contenido
fig, ax = plt.subplots(figsize=(7.5, 4.2))
align = [
    emp["tiene_match_contenido"].mean() * 100,
    uso_enriched["match_contenido"].mean() * 100,
    (uso_enriched["canal"] == uso_enriched["modalidad"]).mean() * 100,
]
labs = ["Empresas con\n≥1 svc match", "Usos alineados\na dirigido_a", "Canal =\nmodalidad catálogo"]
ax.bar(labs, align, color=[PAL[0], PAL[1], PAL[3]], edgecolor="none")
ax.set_ylabel("%")
ax.set_ylim(0, 105)
ax.set_title("Señal de contenido disponible para Diseño A / rama cold de C")
for i, v in enumerate(align):
    ax.text(i, v + 2, f"{v:.1f}%", ha="center")
sb.add_sura_footer(fig, "dirigido_a ↔ sector o Clase N; canal≠modalidad ≈ azar (no usar como match)")
save_fig(fig, "01_diseño_alineacion_contenido.png")

# 7.5 Comparación de diseños (hit-rate + score)
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
names = ["A\nContenido", "B\nColaborativo", "C\nHíbrido"]
axes[0].bar(names, eval_df["hit_rate_at_5"], color=[PAL[0], PAL[1], PAL[2]], edgecolor="none")
axes[0].set_ylim(0, max(0.05, eval_df["hit_rate_at_5"].max() * 1.25))
axes[0].set_ylabel(f"Hit-rate@{K}")
axes[0].set_title(f"Proxy offline (n={int(eval_df.iloc[0]['n_eval'])} warm)")
for i, v in enumerate(eval_df["hit_rate_at_5"]):
    axes[0].text(i, v + 0.005, f"{v:.3f}", ha="center", fontsize=9)

axes[1].bar(names, eval_df["score_decision"], color=[PAL[0], PAL[1], PAL[2]], edgecolor="none")
axes[1].set_ylim(0, 1.05)
axes[1].set_ylabel("Score multi-criterio")
axes[1].set_title("Adopción · cold-start · riesgo · explicabilidad")
for i, v in enumerate(eval_df["score_decision"]):
    axes[1].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
fig.suptitle("Comparación de diseños candidatos", y=1.02)
sb.add_sura_footer(fig, "Pesos score: hit 0.30 · cold 0.25 · riesgo 0.25 · explicabilidad 0.20")
save_fig(fig, "01_diseño_comparacion.png")

# 7.6 Radar-like criteria table as grouped bars
fig, ax = plt.subplots(figsize=(8.5, 4.5))
criteria = ["Hit@5\n(norm)", "Cold-start", "Usa riesgo", "Explicabilidad"]
A_vals = [
    eval_df.loc[0, "hit_rate_at_5"] / max(eval_df["hit_rate_at_5"].max(), 1e-9),
    eval_df.loc[0, "cold_start_nativo"],
    eval_df.loc[0, "usa_riesgo"],
    eval_df.loc[0, "explicabilidad"],
]
B_vals = [
    eval_df.loc[1, "hit_rate_at_5"] / max(eval_df["hit_rate_at_5"].max(), 1e-9),
    eval_df.loc[1, "cold_start_nativo"],
    eval_df.loc[1, "usa_riesgo"],
    eval_df.loc[1, "explicabilidad"],
]
C_vals = [
    eval_df.loc[2, "hit_rate_at_5"] / max(eval_df["hit_rate_at_5"].max(), 1e-9),
    eval_df.loc[2, "cold_start_nativo"],
    eval_df.loc[2, "usa_riesgo"],
    eval_df.loc[2, "explicabilidad"],
]
x = np.arange(len(criteria))
w = 0.25
ax.bar(x - w, A_vals, w, label="A Contenido", color=PAL[0])
ax.bar(x, B_vals, w, label="B Colaborativo", color=PAL[1])
ax.bar(x + w, C_vals, w, label="C Híbrido", color=PAL[2])
ax.set_xticks(x)
ax.set_xticklabels(criteria)
ax.set_ylim(0, 1.15)
ax.set_ylabel("Puntaje normalizado [0,1]")
ax.set_title("Perfil de capacidades por diseño")
ax.legend(frameon=False, ncol=3, loc="upper center")
sb.add_sura_footer(fig, "Diseño C es el único que cubre adopción + riesgo + cold-start")
save_fig(fig, "01_diseño_capacidades.png")

print("\n" + "=" * 70)
print("  LISTO — diseños A/B/C documentados en staging + figs")
print(f"  Sugerencia multi-criterio: {best['diseno']} (score={best['score_decision']:.3f})")
print("=" * 70)
