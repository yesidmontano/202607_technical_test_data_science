# Estacionariedad — análisis de robustez (2.2.2)

> Generado por `code/02-estacionariedad/estacionariedad_robustez.py`.
> Insumo base: `estacionariedad_tests.parquet` (2.2.1) + re-tests ADF/KPSS/PP.

## Criterio de decisión

- **I(0):** ADF o PP rechazan raíz unitaria **y** KPSS no rechaza estacionariedad (α=0.05).
- **I(1):** evidencia de raíz unitaria o conflicto → tratamiento conservador I(1).
- **PP** se aplica a series ambiguas de 2.2.1: `log_freq_at`, `pib_sectorial_var`.

## Cuadro consolidado ADF / KPSS / PP

| Serie | Ventana | n | ADF p | KPSS p | PP p | Orden | Decisión |
|---|---|---|---|---|---|---|---|
| `log_freq_at` | full_n28 | 28 | 0.1536 | 0.1000 | 0.1800 | I(1) | conflicto_conservador_I1 |
| `log_freq_at` | ceed_n18 | 18 | 0.4433 | 0.0696 | 0.4256 | I(1) | conflicto_conservador_I1 |
| `log_freq_at` | edif_n12 | 12 | 0.0892 | 0.0383 | 0.2851 | I(1) | I1_concordancia |
| `pib_sectorial_var` | full_n28 | 28 | 0.3333 | 0.1000 | 0.1013 | I(1) | conflicto_conservador_I1 |
| `pib_sectorial_var` | ceed_n18 | 18 | 0.6905 | 0.0504 | 0.5571 | I(1) | conflicto_conservador_I1 |
| `pib_sectorial_var` | edif_n12 | 12 | 0.0502 | 0.0234 | 0.0300 | I(1) | conflicto_PP_KPSS_I1 |
| `log_ceed_flujo` | ceed_n18 | 17 | 0.2693 | 0.1000 | — | I(1) | conflicto_conservador_I1 |
| `log_ceed_flujo` | edif_n12 | 11 | 0.6674 | 0.0358 | — | I(1) | I1_concordancia |
| `log_ec` | edif_n12 | 9 | 0.9219 | 0.1000 | — | I(1) | conflicto_conservador_I1 |
| `log_ipoc` | ceed_n18 | 17 | 0.6625 | 0.0559 | — | I(1) | conflicto_conservador_I1 |
| `log_empleo` | full_n28 | 27 | 0.3483 | 0.0180 | — | I(1) | I1_concordancia |
| `log_empleo` | ceed_n18 | 17 | 0.8303 | 0.0241 | — | I(1) | I1_concordancia |
| `log_ipp` | full_n28 | 27 | 0.8174 | 0.0100 | — | I(1) | I1_concordancia |
| `d_log_freq_at` | full_n28 | 27 | 0.0000 | 0.1000 | 0.0000 | I(0) | Delta_I0 |
| `d_pib_sectorial_var` | full_n28 | 27 | 0.0004 | 0.1000 | 0.0028 | I(0) | Delta_I0 |

## Decisiones formales sobre series ambiguas

### `pib_sectorial_var` (ventana larga n=28)
- ADF p=0.3333 | KPSS p=0.1000 | PP p=0.1013
- **Veredicto:** `conflicto_conservador_I1` → mantener **I(1)** / primeras diferencias como en 2.2.1.

### `log_freq_at` (ventana larga n=28 + PP)
- ADF p=0.1536 | KPSS p=0.1000 | PP p=0.1800
- **Veredicto:** `conflicto_conservador_I1` → confirma tratamiento **I(1)** del núcleo AT.

## Implicación para el modelado

La robustez **no altera** la conclusión operativa de 2.2.1 para el bloque endógeno (AT, CEED, EC, IPOC, empleo): series de nivel I(1) → modelar en diferencias o VECM si hubiera cointegración. El único matiz es `pib_sectorial_var` en n=28, donde la potencia mejora; ver veredicto arriba.

*Referencia visual:* `results/imgs/02_estacionariedad_robustez.png`