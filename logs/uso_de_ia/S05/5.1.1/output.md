# Registro de Uso de IA — 5.1.1

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se requería analizar los tres datasets del recomendador, proponer tres diseños contrastables con justificación cuantitativa, persistir staging S05, generar figuras con `sura_brand`, documentar la elección pendiente en markdown y registrar el uso de IA.

## Qué se tomó
- Perfil de datos: 5 000 empresas, 4 500 warm / 500 cold (10%), 40 servicios, 98 736 usos 2022–2024, densidad warm 25.3%, mediana 10 servicios/empresa.
- Señal contenido: `dirigido_a` cubre 100% empresas pero solo 10.3% de usos históricos → contenido necesario para cold, insuficiente solo.
- Proxy offline leave-one-out Hit@5 (n=800): A=0.46, B=0.78, C=0.62.
- Score multi-criterio (hit 0.30 · cold 0.25 · riesgo 0.25 · explicabilidad 0.20) → sugiere **C**.
- Patrón S04/S03: script único, staging parquet, plots `01_*`, log en `logs/uso_de_ia/S05/5.1.1/`.
- Riesgo empresa: `costo_pred` holdout 2024 de S03 como `score_riesgo_s03`.

## Qué se descartó o requirió corrección manual
- **Prototipo completo 5.2:** fuera de alcance; solo diseños + proxies.
- **Merge S03 sin filtrar horizonte:** primera corrida duplicó empresas (10 000 filas); corregido a `horizonte=holdout_2024` + 1 fila/empresa.
- **Canal = modalidad como feature de match:** descartado (≈33% = azar).
- **Diseño B como default:** descartado como sugerencia final pese a mejor Hit@5, porque no cubre cold ni riesgo.

## Hallazgos clave del proceso
1. Cold-start es material (10%); CF puro no basta.
2. CF item–item es viable (densidad 25%, sim top-5 ≈0.50) y gana adopción pura.
3. Diseño **C híbrido** es el único alineado al enunciado (adopción + riesgo + cold); score decisión 0.82.

## Lecciones y advertencias relevantes
- Los Hit@5 son proxies de diseño, no métricas oficiales de 5.2 (usar split temporal 2023/2024).
- El término de riesgo en C debe calibrarse para no degradar adopción en exceso.
- Decisión final A/B/C queda pendiente de revisión humana antes de 5.2.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-diseños/01-diseños.py` | Análisis + comparación A/B/C |
| `.../results/imgs/01_diseño_*.png` | 6 figuras |
| `.../results/diseño_recomendador.md` | Hallazgos para elección |
| `data/staging/S05/recomendador_*.parquet` | Datasets #128–139 |
| `docs/staging_data.md` | Documentación staging |
| `logs/uso_de_ia/S05/5.1.1/output.md` | Este log |
