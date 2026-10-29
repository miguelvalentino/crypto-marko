"""Halaman Dashboard: grafik prediksi, evaluasi model, analisis, bobot, simulasi."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    ASSET_KEYS,
    ASSET_NAMES,
    HORIZONS,
    MODELS,
    analysis_block,
    asset_entry,
    backtest_metrics,
    get_predictions,
    value_color,
)
from portfolio import optimize_weights, simulate_portfolio

ACTUAL_LINE_COLOR = "#7fb3ff"
PREDICTION_LINE_COLOR = "#7dff9b"
CHART_HEIGHT = 400
FALLBACK_RISK_FREE_ANNUAL = 0.0575


# ========================= HELPER =========================
def tombol_pilihan(label, options, state_key, key_prefix):
    """Render satu baris tombol pilihan (pengganti radio)."""
    current = st.session_state[state_key]

    st.write(label)
    columns = st.columns(len(options), gap="small")
    for index, option in enumerate(options):
        with columns[index]:
            if st.button(
                str(option),
                key=f"{key_prefix}_{option}",
                type="primary" if option == current else "secondary",
                width="stretch",
            ):
                st.session_state[state_key] = option
                st.rerun()


def build_analysis_table(analysis):
    """Tabel expected return dan risiko tiap aset."""
    rows = []
    for asset_code in ASSET_KEYS:
        data = analysis["assets"].get(asset_code, {})
        rows.append(
            {
                "Aset": f"{asset_code} · {ASSET_NAMES.get(asset_code, '')}",
                "Harga Terakhir": data.get("last", 0),
                "Tanggal Prediksi": data.get("date", "-"),
                "Prediksi": data.get("pred", 0),
                "Expected Return": data.get("expected_return", 0),
                "Risiko (σ)": data.get("risk", 0),
            }
        )

    df = pd.DataFrame(rows)
    df["Expected Return"] = df["Expected Return"] * 100
    df["Risiko (σ)"] = df["Risiko (σ)"] * 100

    return df.style.map(value_color, subset=["Expected Return"])


def build_simulation_table(simulation):
    """Tabel rincian alokasi dana hasil simulasi."""
    rows = [
        {
            "Aset": f"{row.asset} · {ASSET_NAMES.get(row.asset, '')}",
            "Bobot": row.weight,
            "Jumlah Aset": row.units,
            "Nilai Akhir (Prediksi)": row.final_value,
            "Keuntungan / Kerugian": row.profit,
        }
        for row in simulation.rows
    ]

    return (
        pd.DataFrame(rows)
        .style.map(value_color, subset=["Keuntungan / Kerugian"])
        .format(
            {
                "Bobot": "{:.1%}",
                "Jumlah Aset": "{:.6f}",
                "Nilai Akhir (Prediksi)": "Rp{:,.0f}",
                "Keuntungan / Kerugian": "Rp{:+,.0f}",
            }
        )
    )


# ========================= KONTROL UTAMA =========================
st.title("Dashboard Prediksi Aset Crypto | Marko")

col_model, col_asset = st.columns(2)
with col_model:
    with st.container(key="grup_model"):
        tombol_pilihan("Model", MODELS, "model", "btn_model")
with col_asset:
    with st.container(key="grup_asset"):
        tombol_pilihan("Cryptocurrency", ASSET_KEYS, "asset", "btn_asset")

model = st.session_state.model
asset = st.session_state.asset

asset_data = asset_entry(model, asset)

# ========================= 01 / GRAFIK PREDIKSI =========================
st.subheader("Grafik Prediksi")

if asset_data:
    history = asset_data.get("history", {})
    forecast = asset_data.get("forecast", {})
    forecast_horizons = sorted(int(h) for h in forecast)

    forecast_dates = [asset_data.get("last_date")] + [
        forecast[str(h)]["date"] for h in forecast_horizons
    ]
    forecast_prices = [asset_data.get("last_close")] + [
        forecast[str(h)]["price"] for h in forecast_horizons
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history.get("dates", []),
            y=history.get("close", []),
            name="Actual (60 hari)",
            line=dict(color=ACTUAL_LINE_COLOR),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_dates,
            y=forecast_prices,
            name=f"Predicted {model}",
            line=dict(dash="dot", color=PREDICTION_LINE_COLOR),
        )
    )
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(t=40, b=40, l=40, r=40),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        alt=f"Grafik harga historis dan prediksi {asset} dengan model {model}",
    )

    last_close = asset_data.get("last_close", 0)
    last_date = asset_data.get("last_date", "-")
    forecast_text = " | ".join(
        f"H+{h} Rp{forecast[str(h)]['price']:,.0f}" for h in forecast_horizons
    )
    st.info(
        f"{model} · {asset} · harga terakhir Rp{last_close:,.0f} ({last_date}) "
        f"· forecast: {forecast_text}"
    )
else:
    st.warning("Data tidak tersedia untuk model/aset yang dipilih.")

# ========================= 02 / EVALUASI MODEL =========================
st.divider()

st.subheader(" 02 / Estimasi & Optimasi")

with st.container(key="grup_horizon"):
    tombol_pilihan("Horizon (hari)", HORIZONS, "horizon", "btn_horizon")

horizon = st.session_state.horizon

st.markdown("### 03 / Evaluasi Model")
st.write(f"**Hasil Evaluasi Akurasi Model - {horizon} hari**")

backtest = backtest_metrics(model, horizon, asset)
if backtest:
    col_mae, col_rmse, col_mape, col_r2 = st.columns(4)
    with col_mae:
        st.metric("MAE", f"Rp{backtest.get('MAE', 0):,.0f}")
    with col_rmse:
        st.metric("RMSE", f"Rp{backtest.get('RMSE', 0):,.0f}")
    with col_mape:
        st.metric("MAPE", f"{backtest.get('MAPE', 0):.2f}%")
    with col_r2:
        st.metric("R²", f"{backtest.get('R2', 0):.4f}")
else:
    st.info("Data backtesting tidak tersedia.")

# ========================= 03 / ANALISIS PER ASET =========================
st.markdown("### 04 / Analisis per Aset")
st.write(f"**Expected return & risiko - {horizon} hari**")

analysis = analysis_block(model, horizon)
if analysis:
    st.dataframe(
        build_analysis_table(analysis),
        width="stretch",
        hide_index=True,
        column_config={
            "Harga Terakhir": st.column_config.NumberColumn(
                "Harga Terakhir",
                format="Rp%,.0f",
                alignment="left",
            ),
            "Prediksi": st.column_config.NumberColumn(
                "Prediksi",
                format="Rp%,.0f",
                alignment="left",
            ),
            "Expected Return": st.column_config.NumberColumn(
                "Expected Return",
                format="%+.2f%%",
                alignment="left",
            ),
            "Risiko (σ)": st.column_config.NumberColumn(
                "Risiko (σ)",
                format="%.2f%%",
                alignment="left",
            ),
        },
    )
    st.caption(
        "μ = (prediksi - terakhir) / terakhir · σ dari covariance 90 hari × horizon "
    )
else:
    st.info("Data analisis tidak tersedia.")

# ========================= 04 / BOBOT MARKOWITZ =========================
st.divider()
st.subheader("Rekomendasi bobot aset Portofolio Markowitz")


st.write("Tentukan bobot minimum per aset, lalu tekan konfirmasi untuk melanjutkan")
min_weight_percent = st.slider(
    "Bobot minimum per aset (%)",
    min_value=0,
    max_value=30,
    value=int(st.session_state.weight_min * 100),
    step=1,
    label_visibility="collapsed",
)

col_confirm, _, _ = st.columns([1, 1, 8])
with col_confirm:
    if st.button("Konfirmasi", key="confirm_w"):
        st.session_state.weight_min = min_weight_percent / 100

if analysis:
    expected_returns = [analysis["assets"][a]["expected_return"] for a in ASSET_KEYS]
    covariance = analysis.get("cov", [[0.0] * 3 for _ in range(3)])
    risk_free = analysis.get("rf", FALLBACK_RISK_FREE_ANNUAL / 365 * horizon)

    result = optimize_weights(
        expected_returns,
        covariance,
        risk_free,
        st.session_state.weight_min,
    )

    # Bobot tiap aset
    weight_columns = st.columns(3)
    for index, asset_code in enumerate(ASSET_KEYS):
        weight_percent = result.weights[index] * 100
        with weight_columns[index]:
            st.metric(asset_code, f"{weight_percent:.1f}%")
            st.progress(weight_percent / 100)

    # Ringkasan portofolio
    col_return, col_risk, col_sharpe = st.columns(3)
    with col_return:
        st.metric("Expected Return", f"{result.expected_return:.2%}")
    with col_risk:
        st.metric("Risiko", f"{result.risk:.2%}")
    with col_sharpe:
        st.metric("Sharpe Ratio", f"{result.sharpe:.3f}")

    st.caption(
        f"Horizon {horizon} hari · Maks. Sharpe (min. bobot per aset dapat "
        "diubah di slider) · update: "
        + get_predictions().get("meta", {}).get("generated_at", "-")
    )

    # ========================= 05 / SIMULASI MODAL =========================
    st.divider()
    st.subheader("Simulasi Modal")

    capital_input = st.number_input(
        "Modal awal (Rp)",
        min_value=0,
        step=1000,
        value=1000000,
        key="sim_input",
    )
    if st.button("Hitung", key="btn_sim"):
        st.session_state.sim_modal = capital_input

    if st.session_state.get("sim_modal"):
        st.markdown("### Hasil Simulasi")

        asset_inputs = {
            asset_code: {
                "last": analysis["assets"][asset_code]["last"],
                "pred": analysis["assets"][asset_code]["pred"],
            }
            for asset_code in ASSET_KEYS
        }
        simulation = simulate_portfolio(
            asset_inputs,
            result.weights,
            st.session_state.sim_modal,
        )

        st.dataframe(
            build_simulation_table(simulation),
            width="stretch",
            hide_index=True,
            column_config={
                "Bobot": st.column_config.NumberColumn(
                    "Bobot", alignment="left"
                ),
                "Jumlah Aset": st.column_config.NumberColumn(
                    "Jumlah Aset", alignment="left"
                ),
                "Nilai Akhir (Prediksi)": st.column_config.NumberColumn(
                    "Nilai Akhir (Prediksi)", alignment="left"
                ),
                "Keuntungan / Kerugian": st.column_config.NumberColumn(
                    "Keuntungan / Kerugian", alignment="left"
                ),
            },
            alt="Tabel alokasi dana dan nilai akhir prediksi tiap aset",
        )

        col_capital, col_value, col_profit = st.columns(3)
        with col_capital:
            st.metric("Modal", f"Rp{st.session_state.sim_modal:,.0f}")
        with col_value:
            st.metric("Nilai Portfolio", f"Rp{simulation.total_value:,.0f}")
        with col_profit:
            delta_percent = (
                ((simulation.total_value / st.session_state.sim_modal) - 1) * 100
                if st.session_state.sim_modal
                else 0
            )
            st.metric(
                "Keuntungan / Kerugian",
                f"{'+' if simulation.total_profit >= 0 else ''}"
                f"Rp{simulation.total_profit:,.0f}",
                delta=f"{delta_percent:.2f}%",
            )
else:
    st.info("Data optimisasi tidak tersedia.")

st.caption(
    "Dashboard ini merupakan prototipe penelitian, bukan nasihat atau rekomendasi "
    "investasi."
)
