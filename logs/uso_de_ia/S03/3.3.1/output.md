# Registro de Uso de IA — 3.3.1

## Modelo utilizado
Cursor Grok 4.5

## Por qué se usó
Se necesitaba proyectar el resultado técnico del portafolio (siniestralidad vs primas, combined ratio base/adverso e incertidumbre), reutilizando 3.2.1, persistir staging S03, generar figuras con `sura_brand` y documentar hallazgos + log.

## Qué se tomó
- Predicciones `modelo_pred_empresa` (`horizonte=proximo_anio`) y agregados por clase.
- Serie de costo anual de `temporal_empresa_anio` para shock YoY y σ histórica.
- Combined ratio = LR + ER con ER operativo documentado (25% / 27% adverso).
- Incertidumbre en tres capas: bootstrap de residuos holdout, proceso YoY paramétrico, combinación.
- Escenario adverso = base × (1 + máx YoY histórico de costo, +36%).

## Qué se descartó o requirió corrección manual
- **Calcular gastos desde raw:** no existen → ER como supuesto explícito + sensibilidad ±5 pp.
- **Usar las 5 000 empresas sin filtrar prima:** distorsiona LR; se restringe a prima>0 (4 421).
- **Adverso solo con P95 del bootstrap de modelo:** demasiado suave (CR~91%); el shock histórico es el estrés de negocio relevante y queda cerca del P95 combinado.
- **Cópulas freq–sev adicionales:** fuera de alcance; el estrés actúa sobre el costo agregado del pure premium.

## Hallazgos clave del proceso
1. **Base:** siniestros 15.86 B / primas 28.76 B → LR 55.2%, CR **80.2%**, resultado **+5.71 B**.
2. **Adverso (+36% YoY):** LR 75.0%, CR **102.0%**, resultado **−0.59 B**.
3. **Incertidumbre combinada:** IC90 siniestralidad [9.8, 22.6] B; P(CR>1) = **8.1%**.

## Lecciones y advertencias relevantes
- Separar claramente LR (dato del modelo) de CR (LR + supuesto de gastos) en la comunicación a Dirección.
- El filtro prima>0 cambia el total de siniestralidad vs 3.2.1; documentarlo evita inconsistencias aparentes.

---

## Archivos generados

| Archivo | Descripción |
|---|---|
| `.../code/01-proyeccion/01-proyeccion.py` | Script ejecutable |
| `.../results/imgs/01_proyeccion_*.png` | 6 figuras |
| `.../results/proyeccion_*.csv` | Espejo de staging |
| `.../results/proyeccion_portafolio.md` | Hallazgos para revisión |
| `data/staging/S03/proyeccion_*.parquet` | Datasets #104–111 |
| `docs/staging_data.md` | Documentación staging |
| `logs/uso_de_ia/S03/3.3.1/output.md` | Este log |
