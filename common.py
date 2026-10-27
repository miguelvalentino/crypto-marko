"""Konstanta, pemuatan data, state, dan CSS bersama untuk aplikasi Streamlit."""

import json
import os

import streamlit as st

# ========================= KONSTANTA =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTIONS_FILE = os.path.join(BASE_DIR, "predictions.json")

ASSET_NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
ASSET_KEYS = ["BTC", "ETH", "SOL"]
HORIZONS = [1, 3, 7, 14, 30]
MODELS = ["TCN", "LSTM"]

# Warna nilai pada tabel: hijau untuk untung, merah untuk rugi.
POSITIVE_COLOR = "#7dff9b"
NEGATIVE_COLOR = "#ff9b9b"


# ========================= MUAT DATA =========================
@st.cache_data
def _load_predictions(mtime):
    """Baca predictions.json (mtime dipakai sebagai kunci cache)."""
    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_predictions():
    """Ambil data prediksi; otomatis segar saat file diperbarui."""
    return _load_predictions(os.path.getmtime(PREDICTIONS_FILE))


def model_block(model):
    """Ambil seluruh data untuk satu model (TCN/LSTM)."""
    return get_predictions().get("models", {}).get(model, {})


def asset_entry(model, asset):
    """Ambil histori + forecast satu aset pada model terpilih."""
    return model_block(model).get(asset, {})


def analysis_block(model, horizon):
    """Ambil expected return, covariance, dan risk-free untuk horizon terpilih."""
    return model_block(model).get("analysis", {}).get(str(horizon), {})


def backtest_metrics(model, horizon, asset):
    """Ambil metrik backtesting (MAE, RMSE, MAPE, R2)."""
    return (
        get_predictions()
        .get("backtest", {})
        .get(model, {})
        .get(str(horizon), {})
        .get(asset, {})
    )


# ========================= STATE AWAL =========================
def init_state():
    """Isi session_state dengan nilai default saat aplikasi pertama dibuka."""
    defaults = {
        "model": "LSTM",
        "asset": "BTC",
        "horizon": 7,
        "weight_min": 0.20,
        "sim_modal": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ========================= TAMPILAN =========================
def value_color(value):
    """Warna hijau untuk nilai >= 0, merah untuk nilai negatif."""
    color = POSITIVE_COLOR if value >= 0 else NEGATIVE_COLOR
    return f"color: {color}; font-weight: 700;"


def inject_css():
    """CSS kustom: hanya untuk detail yang tidak diatur tema."""
    st.markdown(
        """
        <style>
            .stMetric {
                background-color: rgba(128, 128, 128, 0.10);
                padding: 10px;
                border-radius: 8px;
                border: 1px solid rgba(128, 128, 128, 0.25);
            }
            .stButton > button {
                font-weight: 700;
                border-radius: 8px;
            }
            .stButton > button[data-testid="stBaseButton-primary"] {
                color: #0b0b0b;
                border: 1px solid #7dff9b;
            }
            /* Rapatkan jarak atas konten utama. Halaman auth punya aturan
               sendiri (padding-top: 12vh) yang di-inject setelah CSS ini. */
            [data-testid="stAppViewContainer"] .block-container {
                padding-top: 3rem !important;
            }
            /* Pembatas antar grup kontrol (Model | Cryptocurrency) */
            .st-key-grup_model {
                padding-right: 1.25rem;
            }
            .st-key-grup_asset {
                border-left: 1px solid rgba(128, 128, 128, 0.35);
                padding-left: 1.25rem;
            }
            /* Horizon kini menjadi bagian header Estimasi & Optimasi. */
            .st-key-grup_horizon {
                width: 100% !important;
                max-width: 460px;
            }
            .st-key-grup_horizon [data-testid="stMarkdownContainer"] p {
                font-size: 13px;
                font-weight: 600;
                opacity: 0.75;
                margin-bottom: 0.25rem;
            }
            @media (max-width: 700px) {
                .st-key-grup_model {
                    padding-right: 0;
                }
                .st-key-grup_asset {
                    border-left: none;
                    padding-left: 0;
                }
                .st-key-grup_horizon {
                    max-width: 100%;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
