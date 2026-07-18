"""Streamlit page: DFM nowcast panel."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config.settings import STAGING_S02
from tools.nowcast_dfm import get_nowcast_dict


def render() -> None:
    st.subheader("Nowcast DFM (sección 2.3)")
    st.caption(
        "Modelo operativo: Dynamic Factor Model (1 factor + puente OLS). "
        "Valores desde staging S02 — no se inventan cifras."
    )

    period = st.text_input("Periodo", value="2025-T1")
    if st.button("Obtener nowcast DFM", type="primary"):
        data = get_nowcast_dict(period)
        if not data.get("ok"):
            st.error(data.get("error") or "Error desconocido")
            return
        c1, c2, c3 = st.columns(3)
        c1.metric("Punto (ŷ)", f"{data['y_hat']:.3f}")
        c2.metric("IC80% inf.", f"{data['ic80_lo']:.3f}")
        c3.metric("IC80% sup.", f"{data['ic80_hi']:.3f}")
        st.write(
            f"**Periodo:** {data['periodo']} · **Unidad:** {data['unidad']} · "
            f"**Split:** {data.get('split')}"
        )
        st.info(data.get("notas", ""))
        st.json(data)

    hist_path = STAGING_S02 / "nowcast_dfm_predicciones.parquet"
    if hist_path.exists():
        st.markdown("#### Serie de predicciones DFM (staging)")
        df = pd.read_parquet(hist_path)
        st.dataframe(df, use_container_width=True)
        chart = df.copy()
        chart = chart.sort_values(["anio", "q"])
        st.line_chart(chart.set_index("periodo")[["y_pred", "y_true"]].astype(float))
