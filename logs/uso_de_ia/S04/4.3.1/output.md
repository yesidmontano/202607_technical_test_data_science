# Registro de Uso de IA — 4.3.1

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se requería traducir el ATT de frecuencia (4.2) a valor económico en COP, explicitar el grado de causalidad de la conclusión y los supuestos de ruptura, persistir staging S04, generar figuras con `sura_brand`, documentar hallazgos y registrar el uso de IA.

## Qué se tomó
- Contrato 4.2: monetizar ATT de `frecuencia_x100` (−0.428), no el ATT de `costo_por_trab`.
- Puente: `valor = (−ATT/100) × n_trabajadores × E[costo|siniestro]` con E[costo] de siniestros de tratadas (`costo_total_w`).
- Propagación de IC95 del ATT y sensibilidad p25/median/mean/p75.
- Patrón S04-4.2 / S03: staging parquet, plots `01_*`, markdown de resultados, log en `logs/uso_de_ia/S04/4.3.1/`.
- Credibilidad en dos capas: causal moderado–alto en frecuencia; moderado en pesos (puente de severidad).

## Qué se descartó o requirió corrección manual
- **ROI neto:** descartado — no hay costo del programa en COP.
- **ATT directo en COP:** descartado como resultado principal (no significativo en 4.2).
- **Mapeo IC ATT → banda de valor:** se corrigió para que ATT más negativo = cota alta de ahorro (no invertir lo/hi en COP).

## Hallazgos clave del proceso
1. Siniestros evitados acum. post ≈ **1 891**; run-rate pleno ≈ **418**/año.
2. Valor bruto @ media: **5.70 B** acum. / **1.26 B**/año (banda ATT **[0.50, 2.02] B**/año).
3. @ mediana: **2.52 B** acum. / **0.56 B**/año (cola de severidad).
4. Causalidad: frecuencia moderado–alto; pesos moderado (depende de severidad constante).

## Lecciones y advertencias relevantes
- Comunicar media y mediana; no vender el punto central como ROI.
- El valor escala linealmente con exposición — heterogeneidad por cohorte (2022) limita extrapolación.
- S1–S6 en `valor_economico_supuestos` son el checklist de validez ante Dirección.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-val_economico/01-val_economico.py` | Script de monetización |
| `.../results/imgs/01_valor_*.png` | 5 figuras |
| `.../results/efecto_economico.md` | Hallazgos para revisión |
| `data/staging/S04/valor_economico_*.parquet` | Datasets #120–127 |
| `docs/staging_data.md` | Documentación staging |
| `logs/uso_de_ia/S04/4.3.1/output.md` | Este log |
