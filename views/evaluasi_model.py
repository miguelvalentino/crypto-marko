"""Halaman Evaluasi Model: metrik backtesting seluruh model, aset, dan horizon."""

import pandas as pd
import streamlit as st

from common import ASSET_KEYS, ASSET_NAMES, HORIZONS, MODELS, get_predictions

st.title("Evaluasi Model")

predictions = get_predictions()
backtest = predictions.get("backtest", {})
generated_at = predictions.get("meta", {}).get("generated_at", "-")

# Urutkan per aset, lalu horizon, lalu model.
rows = []
for asset_code in ASSET_KEYS:
    for horizon in HORIZONS:
        for model in MODELS:
            metrics = backtest.get(model, {}).get(str(horizon), {}).get(asset_code, {})
            if not metrics:
                continue

            rows.append(
                {
                    "Model": model,
                    "Aset": f"{asset_code} · {ASSET_NAMES.get(asset_code, '')}",
                    "Horizon": horizon,
                    "MAE (Rp)": metrics.get("MAE", 0),
                    "RMSE (Rp)": metrics.get("RMSE", 0),
                    "MAPE": metrics.get("MAPE", 0),
                    "R²": metrics.get("R2", 0),
                }
            )

st.markdown("### Tabel lengkap")

if rows:
    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Model": st.column_config.TextColumn(
                "Model", width="small", alignment="left"
            ),
            "Aset": st.column_config.TextColumn(
                "Aset", width="medium", alignment="left"
            ),
            "Horizon": st.column_config.NumberColumn(
                "Horizon (hari)", format="%d", width="small", alignment="left"
            ),
            "MAE (Rp)": st.column_config.NumberColumn(
                "MAE (Rp)", format="%,.0f", alignment="left"
            ),
            "RMSE (Rp)": st.column_config.NumberColumn(
                "RMSE (Rp)", format="%,.0f", alignment="left"
            ),
            "MAPE": st.column_config.NumberColumn(
                "MAPE", format="%.2f%%", alignment="left"
            ),
            "R²": st.column_config.NumberColumn(
                "R²", format="%.4f", alignment="left"
            ),
        },
        alt="Tabel metrik MAE, RMSE, MAPE, dan R2 untuk model LSTM dan TCN "
        "pada seluruh aset dan horizon",
    )

    st.caption(
        "Klik judul kolom untuk "
        "mengurutkan ulang. MAE/RMSE dalam rupiah tidak sebanding antar aset karena "
        "skala harga berbeda — gunakan MAPE atau R² untuk membandingkan lintas aset. "
        "R² negatif berarti prediksi lebih buruk daripada rata-rata. "
    )
else:
    st.info("Data evaluasi belum tersedia.")
