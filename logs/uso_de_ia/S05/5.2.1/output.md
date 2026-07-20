# Registro de Uso de IA — 5.2.1

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se requería implementar el prototipo del Diseño C (5.1.1), evaluarlo con partición temporal, calibrar α, persistir staging S05, generar figuras con `sura_brand`, documentar hallazgos/limitaciones offline y registrar el uso de IA.

## Qué se tomó
- Diseño C: `score = α·adopción + (1-α)·riesgo`; warm = CF item–item + contenido; cold = contenido + popularidad de segmento.
- Split temporal train ≤2023 / test 2024; GT = nuevas adopciones 2024.
- Cold-start real sin GT → cold_sim (n=500, historial oculto) para NDCG/Recall; true_cold para guardrails.
- Regla α: max ΔRisk@5 s.t. NDCG@5 ≥ 95% del máximo → **α\*=0.70**.
- Baselines: popularidad, A contenido, B CF.
- Log en `logs/uso_de_ia/S05/5.2.1/` (proceso 5.2; no sobrescribir 5.1.1).

## Qué se descartó o requirió corrección manual
- **Eval adopción en true-cold:** imposible offline (0 usos); sustituido por cold_sim + guardrails.
- **Loop O(n·m) al generar recs:** precomputar `all_hist` por empresa.
- **α_cold distinto en el barrido:** se usó la misma α en ambas ramas por simplicidad; documentado como L6.

## Hallazgos clave del proceso
1. **α\*=0.70** — NDCG@5 warm=0.402, Recall@5=0.490, ΔRisk@5=+0.173.
2. vs B: C cede adopción (NDCG 0.40 vs 0.48) a cambio de ~2× ΔRisk (0.17 vs 0.08).
3. Guardrails true_cold: 100% con K=5, coverage 95%.
4. Cold_sim NDCG@5=0.108 — rama contenido limita adopción sin historial.

## Lecciones y advertencias relevantes
- ΔRisk es proxy de intención preventiva, no causalidad.
- Si el KPI es solo adopción → B; si es dual → C @ 0.70.
- 5.3 debe monitorear warm/cold por separado y revisar α.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-prototipo/01-prototipo.py` | Prototipo + evaluación |
| `.../results/imgs/01_prototipo_*.png` | 7 figuras |
| `.../results/prototipo_recomendador.md` | Hallazgos para revisión |
| `data/staging/S05/prototipo_*.parquet` | Datasets #140–145 |
| `docs/staging_data.md` | Documentación staging |
| `logs/uso_de_ia/S05/5.2.1/output.md` | Este log |
