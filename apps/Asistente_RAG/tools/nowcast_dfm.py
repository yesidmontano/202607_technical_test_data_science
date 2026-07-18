"""ADK tool: DFM nowcast from S02 staging (section 2.3)."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from config.settings import STAGING_S02

FORWARD_DEFAULT = "2025-T1"
NOTES = (
    "Modelo operativo DFM (1 factor + puente OLS) seleccionado en §2.3.3. "
    "IC80% vía bootstrap residual del puente. "
    "Forward 2025-T1 usa AT parcial proxy (share histórico × lag-1)."
)


def _load_dfm_row(period: str) -> dict[str, Any] | None:
    preds = STAGING_S02 / "nowcast_dfm_predicciones.parquet"
    fwd = STAGING_S02 / "nowcast_forward_2025T1.parquet"
    if preds.exists():
        df = pd.read_parquet(preds)
        hit = df.loc[(df["modelo"] == "DFM") & (df["periodo"].astype(str) == period)]
        if not hit.empty:
            r = hit.iloc[-1]
            return {
                "periodo": str(r["periodo"]),
                "split": str(r.get("split", "")),
                "y_pred": float(r["y_pred"]),
                "y_lo80": float(r["y_lo80"]),
                "y_hi80": float(r["y_hi80"]),
                "y_true": None if pd.isna(r.get("y_true")) else float(r["y_true"]),
                "factor1": None if pd.isna(r.get("factor1")) else float(r["factor1"]),
            }
    if fwd.exists() and period == FORWARD_DEFAULT:
        df = pd.read_parquet(fwd)
        hit = df.loc[df["modelo"] == "DFM"]
        if not hit.empty:
            r = hit.iloc[0]
            return {
                "periodo": str(r["periodo"]),
                "split": "forward",
                "y_pred": float(r["y_pred"]),
                "y_lo80": float(r["y_lo80"]),
                "y_hi80": float(r["y_hi80"]),
                "y_true": None,
                "factor1": None if pd.isna(r.get("factor1")) else float(r["factor1"]),
            }
    return None


def run_nowcast_dfm(period: str | None = None) -> str:
    """Return the DFM nowcast of workplace-accident frequency for construction.

    Call this tool when the user asks for nowcast, predicción, proyección or
    estimación de frecuencia de accidentes de trabajo (AT) del trimestre.
    Do NOT invent numbers — only report values returned by this tool.

    Args:
        period: Quarter label like '2025-T1'. Defaults to the operative forward
            period from section 2.3 (2025-T1).

    Returns:
        JSON with modelo, periodo, y_hat, ic80_lo, ic80_hi, unidad, notas.
    """
    periodo = (period or FORWARD_DEFAULT).strip()
    row = _load_dfm_row(periodo)
    if row is None:
        # Fall back to summary table for default forward
        resumen = STAGING_S02 / "nowcast_resumen_final.parquet"
        if resumen.exists() and periodo == FORWARD_DEFAULT:
            df = pd.read_parquet(resumen)
            hit = df.loc[df["modelo"] == "DFM"]
            if not hit.empty:
                r = hit.iloc[0]
                row = {
                    "periodo": FORWARD_DEFAULT,
                    "split": "forward",
                    "y_pred": float(r["nowcast_2025T1"]),
                    "y_lo80": float(r["lo80"]),
                    "y_hi80": float(r["hi80"]),
                    "y_true": None,
                    "factor1": None,
                }
    if row is None:
        return json.dumps(
            {
                "ok": False,
                "error": f"No hay predicción DFM para periodo={periodo}",
                "hint": f"Periodos disponibles en staging S02; default={FORWARD_DEFAULT}",
            },
            ensure_ascii=False,
        )

    payload = {
        "ok": True,
        "modelo": "DFM",
        "periodo": row["periodo"],
        "split": row["split"],
        "y_hat": round(row["y_pred"], 4),
        "ic80_lo": round(row["y_lo80"], 4),
        "ic80_hi": round(row["y_hi80"], 4),
        "y_true": row["y_true"],
        "factor1": None if row["factor1"] is None else round(row["factor1"], 4),
        "unidad": "accidentes por 100 trabajadores (freq_at × 100)",
        "fuente_staging": "data/staging/S02/nowcast_* (sección 2.3)",
        "notas": NOTES,
    }
    return json.dumps(payload, ensure_ascii=False)


def get_nowcast_dict(period: str | None = None) -> dict[str, Any]:
    """Python helper for Streamlit nowcast page (no agent)."""
    return json.loads(run_nowcast_dfm(period))
