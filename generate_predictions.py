"""
Export hasil prediksi LSTM (.keras) ke predictions.json untuk website.

Mirip fungsi predict_future() + plot_historical_vs_points() di notebook
pipeline_data_dan_lstm_btc (3).ipynb.

KONFIGURASI PENTING (disamakan dengan notebook):
- WINDOW_SIZE = 30  (input model = 30 hari x 10 fitur)
  Catatan: "60 hari" di notebook hanya n_historical_days untuk TAMPILAN
  grafik, bukan input model.
- FEATURE_COLS = 10 kolom (Open/High/Low/Close/Volume x Indodax/Binance)
- Target = Close_indodax pada h hari ke depan (h = 1,3,7,14,30)
- scaler_{ASET}.pkl dipakai untuk scaling fitur (fit dari train saja)
- target_scaler_{ASET}_h{H}.pkl dipakai untuk inverse-transform output

CARA PAKAI (jalankan di environment yang sama dengan notebook,
bukan di terminal polos — butuh tensorflow, scikit-learn, ccxt, pandas):

  1. Pastikan struktur folder:
       kode skripsi/
         models_LSTM/            <- 15x .keras + 3x scaler + 15x target_scaler (sudah ada)
         data/merged/            <- BTC_merged.csv, ETH_merged.csv, SOL_merged.csv
                                    (copy dari output notebook: data/merged/)
         generate_predictions.py <- file ini
         predictions.json        <- hasil (dibuat oleh script ini)

     Jika data/merged belum ada, script otomatis fetch live via ccxt
     (butuh internet) seperti Tahap 1-2 notebook.

  2. Jalankan:
       python generate_predictions.py
       -> menghasilkan predictions.json

  3. Copy predictions.json ke folder yang sama dengan index.html
     (script ini sudah menyimpannya di situ), lalu buka website via
     HTTP server (bukan double-click file://), misal:
       npx serve .
       atau VS Code -> Live Server -> Open index.html
     Alasan: fetch('predictions.json') diblokir browser bila file://.

  4. Di website pilih model=LSTM + aset BTC/ETH/SOL -> grafik update.
     Buka DevTools (F12) -> Console untuk log status load.

Output predictions.json:
{
  "meta": {"window_size": 30, "history_days": 60, "generated_at": "..."},
  "BTC": {
    "last_close": 123456789, "last_date": "2026-10-12",
    "history": {"dates": [...60...], "close": [...60...]},
    "forecast": {"1": {"date": "...", "price": ...}, "3": {...}, ...}
  },
  "ETH": {...}, "SOL": {...}
}
"""
import argparse
import json
import os
import sys
from datetime import datetime, date, timezone, timedelta

import joblib
import numpy as np
import pandas as pd

WIB = timezone(timedelta(hours=7))  # Waktu Indonesia Barat (UTC+7)

ASSETS = ["BTC", "ETH", "SOL"]
MODELS = ["LSTM", "TCN"]  # urutan tampilan di dashboard
HORIZONS = [1, 3, 7, 14, 30]
WINDOW_SIZE = 30          # <-- samakan dengan notebook, JANGAN 60
HISTORY_DAYS = 60         # hanya untuk tampilan grafik
LOOKBACK_DAYS = 90        # untuk matriks covariance (samakan notebook)
BI_RATE_ANNUAL = 0.0575   # samakan Tabel proposal; RF harian = /365
MIN_WEIGHT = 0.2          # batas bawah bobot Markowitz (samakan notebook)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Semua folder yang mungkin berisi .keras / .pkl (sesuai SCALER_DIR di notebook = "models")
MODEL_DIRS = [
    os.path.join(BASE_DIR, "models"),        # output notebook (SCALER_DIR)
    os.path.join(BASE_DIR, "models_LSTM"),   # folder LSTM lama
    os.path.join(BASE_DIR, "models_TCN"),    # bila TCN dipisah
]
MERGED_CANDIDATES = [
    os.path.join(BASE_DIR, "data", "merged"),   # kode skripsi/data/merged
    os.path.join(BASE_DIR, "..", "data", "merged"),
    "data/merged",
    "data/merged".replace("/", os.sep),
]
OUT_PATH = os.path.join(BASE_DIR, "predictions.json")

FEATURE_COLS = [
    "Open_indodax", "High_indodax", "Low_indodax", "Close_indodax", "Volume_indodax",
    "Open_binance", "High_binance", "Low_binance", "Close_binance", "Volume_binance",
]


def find_merged_dir():
    for d in MERGED_CANDIDATES:
        if os.path.isdir(d):
            files = os.listdir(d)
            if any(f.endswith("_merged.csv") for f in files):
                return d
    return None


def find_file(filename):
    """Cari file di semua MODEL_DIRS, kembalikan path pertama yang ada (atau None)."""
    for d in MODEL_DIRS:
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return p
    return None


def model_file_names(model, asset, horizon):
    """Penamaan file per model, PERSIS seperti di notebook.

    Notebook (train_lstm_for_horizon):
        {asset}_LSTM_h{h}.keras        + target_scaler_{asset}_h{h}.pkl
    Notebook (train_tcn_for_horizon):
        {asset}_TCN_h{h}.keras         + target_scaler_TCN_{asset}_h{h}.pkl
    """
    if model == "TCN":
        return f"{asset}_TCN_h{horizon}.keras", f"target_scaler_TCN_{asset}_h{horizon}.pkl"
    return f"{asset}_{model}_h{horizon}.keras", f"target_scaler_{asset}_h{horizon}.pkl"


def fetch_live_merged():
    """Ambil data harian via ccxt.

    - Binance memakai data-api.binance.vision (api.binance.com diblokir di
      runner GitHub US, HTTP 451).
    - Candle hari berjalan (belum selesai) dibuang, agar prediksi memakai
      harga penutupan harian yang lengkap.
    """
    import ccxt
    print("[INFO] fetch live via ccxt ...")
    indodax = ccxt.indodax({"enableRateLimit": True})
    # api.binance.com diblokir di beberapa region (termasuk runner GitHub US).
    binance = ccxt.binance({
        "options": {"defaultType": "spot", "fetchMarkets": ["spot"]},
        "urls": {"api": {"public": "https://data-api.binance.vision/api/v3"}},
        "enableRateLimit": True,
    })

    # Candle yang tanggalnya >= hari ini (UTC) dianggap belum selesai.
    today_utc = datetime.now(timezone.utc).date()

    def fetch(exchange, symbol, limit=1000):
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=limit)
        df = pd.DataFrame(ohlcv, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["Tanggal"] = pd.to_datetime(df["Timestamp"], unit="ms")
        df = df[df["Tanggal"].dt.date < today_utc]
        return df[["Tanggal", "Open", "High", "Low", "Close", "Volume"]].reset_index(drop=True)

    usdt_idr = fetch(indodax, "USDT/IDR")
    if usdt_idr.empty:
        raise RuntimeError("USDT/IDR kosong setelah membuang candle belum selesai")

    merged = {}
    for asset in ASSETS:
        df_indo = fetch(indodax, f"{asset}/IDR")
        df_bin = fetch(binance, f"{asset}/USDT")
        df_fx = df_bin.merge(
            usdt_idr[["Tanggal", "Close"]].rename(columns={"Close": "Kurs"}),
            on="Tanggal", how="left",
        )
        for c in ["Open", "High", "Low", "Close"]:
            df_fx[f"{c}_IDR"] = df_fx[c] * df_fx["Kurs"]
        df_fx["Volume_IDR"] = df_fx["Volume"] * df_fx["Close_IDR"]
        df_idr = df_fx[["Tanggal", "Open_IDR", "High_IDR", "Low_IDR", "Close_IDR", "Volume_IDR"]].copy()
        df_idr.columns = ["Tanggal", "Open", "High", "Low", "Close", "Volume"]
        m = pd.merge(df_indo, df_idr, on="Tanggal", how="inner",
                     suffixes=("_indodax", "_binance"))
        m = m.sort_values("Tanggal").reset_index(drop=True)
        if m.empty:
            raise RuntimeError(f"{asset}: hasil merge kosong")
        merged[asset] = m
        print(f"  {asset}: {len(m)} baris, terakhir {m['Tanggal'].iloc[-1].date()}")
    return merged


def load_merged():
    d = find_merged_dir()
    if d is None:
        return fetch_live_merged(), None
    print(f"[INFO] memakai CSV dari: {d}")
    today_utc = datetime.now(timezone.utc).date()
    merged = {}
    for asset in ASSETS:
        p = os.path.join(d, f"{asset}_merged.csv")
        if not os.path.exists(p):
            print(f"[WARN] {p} tidak ada, lewati {asset}")
            continue
        df = pd.read_csv(p, parse_dates=["Tanggal"])
        df = df[df["Tanggal"].dt.date < today_utc]
        merged[asset] = df.sort_values("Tanggal").reset_index(drop=True)
    return merged, d


def covariance_for_horizon(merged, horizon, lookback=LOOKBACK_DAYS):
    """Mirror get_covariance_matrix(): cov harian dari 90d terakhir, diskala x horizon."""
    rets = []
    for asset in ASSETS:
        df = merged[asset].sort_values("Tanggal").tail(lookback + 1)
        r = df["Close_indodax"].pct_change().dropna().values[-lookback:]
        rets.append(r)
    cov_daily = np.cov(np.array(rets))
    return cov_daily * horizon


def optimize_portfolio(mu, cov, rf_h):
    """Mirror optimize_markowitz(): max Sharpe, sum(w)=1, w>=MIN_WEIGHT."""
    try:
        from scipy.optimize import minimize
    except ImportError:
        n = len(mu)
        w = np.array([1.0 / n] * n)
        pr, ps = float(w @ mu), float(np.sqrt(w @ cov @ w))
        return {"weights": dict(zip(ASSETS, w.tolist())), "expected_return": pr,
                "risk": ps, "sharpe": float((pr - rf_h) / ps) if ps else 0.0,
                "note": "scipy belum terinstal -> equal-weight fallback"}

    n = len(mu)

    def neg_sharpe(w):
        port_std = np.sqrt(w @ cov @ w)
        if port_std == 0:
            return 0.0
        return -((w @ mu) - rf_h) / port_std

    res = minimize(neg_sharpe, np.array([1 / n] * n), method="SLSQP",
                   bounds=[(MIN_WEIGHT, 1)] * n,
                   constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1})
    w = res.x
    pr, ps = float(w @ mu), float(np.sqrt(w @ cov @ w))
    return {"weights": dict(zip(ASSETS, [float(x) for x in w])),
            "expected_return": pr, "risk": ps,
            "sharpe": float((pr - rf_h) / ps) if ps else 0.0}


def predict_model(model, load_model, merged):
    """Prediksi satu model (LSTM atau TCN) untuk semua aset + horizon.

    Window & scaler fitur sama persis untuk keduanya (dipakai bersama),
    hanya nama file .keras dan target_scaler yang berbeda.
    """
    block = {}
    for asset in ASSETS:
        if asset not in merged:
            print(f"[WARN] lewati {asset} (data merged kosong)")
            continue
        df = merged[asset]
        missing = [c for c in FEATURE_COLS + ["Close_indodax"] if c not in df.columns]
        if missing:
            print(f"[ERROR] {asset}: kolom hilang {missing}. Samakan dengan notebook.")
            sys.exit(1)

        scaler_path = find_file(f"scaler_{asset}.pkl")
        if not scaler_path:
            print(f"[ERROR] scaler_{asset}.pkl tidak ditemukan di {MODEL_DIRS}")
            sys.exit(1)
        scaler = joblib.load(scaler_path)

        last_window = df[FEATURE_COLS].values[-WINDOW_SIZE:]
        if len(last_window) < WINDOW_SIZE:
            print(f"[ERROR] {asset}: data hanya {len(last_window)} baris, butuh {WINDOW_SIZE}")
            sys.exit(1)
        X_future = scaler.transform(last_window).reshape(1, WINDOW_SIZE, len(FEATURE_COLS))
        last_date = pd.to_datetime(df["Tanggal"].iloc[-1])
        last_close = float(df["Close_indodax"].iloc[-1])

        hist = df[["Tanggal", "Close_indodax"]].tail(HISTORY_DAYS)
        forecast = {}
        for h in HORIZONS:
            model_name, tscaler_name = model_file_names(model, asset, h)
            mp, tp = find_file(model_name), find_file(tscaler_name)
            if not mp or not tp:
                print(f"[WARN] [{model}] {model_name} / {tscaler_name} belum ada, lewati {asset} h={h}")
                print(f"       -> latih dulu sel TCN di notebook, lalu copy .keras + target_scaler ke folder models/")
                continue
            net = load_model(mp)
            tscaler = joblib.load(tp)
            pred_scaled = net.predict(X_future, verbose=0).flatten()[0]
            price = float(tscaler.inverse_transform([[pred_scaled]])[0][0])
            target_date = (last_date + pd.Timedelta(days=h)).date().isoformat()
            forecast[str(h)] = {"date": target_date, "price": price}
            print(f"  [{model}] {asset} h={h}: Rp{price:,.0f} ({target_date})")

        block[asset] = {
            "last_close": last_close,
            "last_date": last_date.date().isoformat(),
            "history": {
                "dates": pd.to_datetime(hist["Tanggal"]).dt.strftime("%Y-%m-%d").tolist(),
                "close": [float(x) for x in hist["Close_indodax"].tolist()],
            },
            "forecast": forecast,
        }

    if not block:
        return None

    # --- Analisis per horizon (mirror sel Markowitz notebook) ---
    # mu_h = (pred_h - last)/last per aset; risiko aset = sqrt(diag(cov_h))
    last_prices = {a: float(merged[a]["Close_indodax"].iloc[-1]) for a in block}
    active = list(block.keys())
    analysis = {}
    rf_daily = BI_RATE_ANNUAL / 365
    for h in HORIZONS:
        if any(str(h) not in block[a]["forecast"] for a in active):
            print(f"[WARN] [{model}] horizon {h} tidak lengkap, lewati analisis")
            continue
        mu = np.array([(block[a]["forecast"][str(h)]["price"] - last_prices[a]) / last_prices[a]
                       for a in active])
        cov = covariance_for_horizon(merged, h)
        per_asset_risk = np.sqrt(np.diag(cov))
        pf = optimize_portfolio(mu, cov, rf_daily * h)
        analysis[str(h)] = {
            "assets": {
                a: {"last": last_prices[a],
                    "pred": block[a]["forecast"][str(h)]["price"],
                    "date": block[a]["forecast"][str(h)]["date"],
                    "expected_return": float(mu[i]),
                    "risk": float(per_asset_risk[i])}
                for i, a in enumerate(active)
            },
            "portfolio": pf,
            "rf": float(rf_daily * h),
            "cov": cov.tolist(),
            "mu": mu.tolist(),
        }
        er = ", ".join(f"{a}={analysis[str(h)]['assets'][a]['expected_return']:.2%}" for a in active)
        print(f"  [{model}] analisis h={h}: {er} | bobot={pf['weights']}")
    block["analysis"] = analysis
    return block


def is_generated_today(path=OUT_PATH):
    """Cek apakah predictions.json sudah di-generate hari ini (WIB)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        generated = data["meta"]["generated_at"]
        generated_date = datetime.fromisoformat(generated).astimezone(WIB).date()
        return generated_date == date.today()
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return False


def compute_backtest_metrics(merged, load_model):
    """Hitung MAE, RMSE, MAPE, R² untuk tiap model, horizon, dan aset pada data test."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    # Muat test CSV (yang punya kolom Target_hd) dari data/processed
    processed_dir = os.path.join(BASE_DIR, "data", "processed")
    test_dfs = {}
    if os.path.isdir(processed_dir):
        for asset in ASSETS:
            p = os.path.join(processed_dir, f"{asset}_test.csv")
            if os.path.exists(p):
                test_dfs[asset] = pd.read_csv(p, parse_dates=["Tanggal"]).sort_values("Tanggal").reset_index(drop=True)

    metrics = {}
    for model in MODELS:
        metrics[model] = {}
        for h in HORIZONS:
            metrics[model][str(h)] = {}
            for asset in ASSETS:
                if asset not in test_dfs:
                    continue
                test_df = test_dfs[asset]
                if "Target_%dd" % h not in test_df.columns:
                    continue

                model_path = find_file(f"{asset}_{model}_h{h}.keras")
                tscaler_path = find_file(
                    f"target_scaler_TCN_{asset}_h{h}.pkl" if model == "TCN"
                    else f"target_scaler_{asset}_h{h}.pkl"
                )
                if not model_path or not tscaler_path:
                    continue

                net = load_model(model_path)
                tscaler = joblib.load(tscaler_path)

                # PENTING: fitur di data/processed/*_test.csv SUDAH di-scale oleh
                # fit_scale() di notebook (MinMaxScaler fit pada train, lalu
                # transform ke train/val/test). Jadi jangan transform lagi di sini
                # — akan terjadi double scaling dan metrik jadi tidak sesuai notebook.
                # Kolom Target_hd sengaja TIDAK di-scale (lihat catatan di notebook).
                win = WINDOW_SIZE
                if len(test_df) < win + 1:
                    continue
                all_y_true, all_y_pred = [], []
                # Sama persis dengan create_sequences() di notebook: len(df) - window + 1
                for i in range(len(test_df) - win + 1):
                    x = test_df[FEATURE_COLS].values[i:i + win].reshape(1, win, len(FEATURE_COLS))
                    pred_scaled = net.predict(x, verbose=0).flatten()[0]
                    pred = tscaler.inverse_transform([[pred_scaled]])[0][0]
                    actual = test_df[f"Target_{h}d"].iloc[i + win - 1]
                    if pd.notna(actual):
                        all_y_true.append(actual)
                        all_y_pred.append(pred)

                if len(all_y_true) < 5:
                    continue

                mae = mean_absolute_error(all_y_true, all_y_pred)
                rmse = np.sqrt(mean_squared_error(all_y_true, all_y_pred))
                mape = np.mean(np.abs((np.array(all_y_true) - np.array(all_y_pred)) / np.array(all_y_true))) * 100
                r2 = r2_score(all_y_true, all_y_pred)
                metrics[model][str(h)][asset] = {"MAE": float(mae), "RMSE": float(rmse), "MAPE": float(mape), "R2": float(r2)}

    return metrics


def predict_all(force=False, strict=False):
    # Skip jika sudah terupdate hari ini (kecuali --force)
    if not force and is_generated_today():
        print("[SKIP] predictions.json sudah terupdate hari ini.")
        print("       Gunakan --force untuk fetch ulang.")
        return

    try:
        from tensorflow.keras.models import load_model
    except ImportError:
        print("[ERROR] tensorflow belum terinstal di environment ini.")
        print("        Jalankan di environment notebook: pip install tensorflow scikit-learn ccxt pandas scipy joblib")
        sys.exit(1)

    # Fetch live. Di mode strict (CI), kegagalan fetch membuat proses gagal
    # agar tidak diam-diam memakai data lama.
    try:
        print("[INFO] Mencoba fetch data live dari API...")
        merged = fetch_live_merged()
        print("[OK] Data live berhasil diambil.")
    except Exception as e:
        if strict:
            print(f"[ERROR] Fetch live gagal: {e}")
            print("        Mode strict aktif: tidak fallback ke CSV lama.")
            sys.exit(1)
        print(f"[WARN] Fetch live gagal: {e}")
        print("[INFO] Fallback ke CSV terbaru...")
        merged, _ = load_merged()
        if not merged:
            print("[ERROR] Tidak ada data live maupun CSV. Pastikan koneksi internet atau file CSV tersedia.")
            sys.exit(1)

    # Validasi kesegaran data.
    try:
        latest = max(df["Tanggal"].max() for df in merged.values())
        today_utc = datetime.now(timezone.utc).date()
        if latest.date() < (today_utc - timedelta(days=1)):
            msg = f"[WARN] Data terakhir {latest.date()} lebih lama dari kemarin ({today_utc - timedelta(days=1)})."
            if strict:
                print(f"[ERROR] {msg}")
                print("        Mode strict aktif: data dianggap basi.")
                sys.exit(1)
            print(msg)
    except Exception:
        pass

    # Hitung backtesting metrics
    print("\n=== Backtesting Metrics ===")
    backtest = compute_backtest_metrics(merged, load_model)
    for m in backtest:
        for h in backtest[m]:
            for a in backtest[m][h]:
                met = backtest[m][h][a]
                print(f"  [{m}] h={h} {a}: MAE={met['MAE']:,.0f} | RMSE={met['RMSE']:,.0f} | MAPE={met['MAPE']:.2f}% | R2={met['R2']:.4f}")

    out = {
        "meta": {
            "window_size": WINDOW_SIZE,
            "history_days": HISTORY_DAYS,
            "horizons": HORIZONS,
            "generated_at": datetime.now(WIB).isoformat(timespec="seconds"),
            "lookback_days": LOOKBACK_DAYS,
            "bi_rate_annual": BI_RATE_ANNUAL,
            "min_weight": MIN_WEIGHT,
        },
        "backtest": backtest,
        "models": {},
    }
    for model in MODELS:
        print(f"\n=== {model} ===")
        block = predict_model(model, load_model, merged)
        if block:
            out["models"][model] = block
        else:
            print(f"[WARN] tidak ada data untuk {model}, dilewati di predictions.json")

    available = list(out["models"].keys())
    print(f"\n[INFO] model tersedia di predictions.json: {available or 'TIDAK ADA'}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"[OK] tersimpan: {OUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate predictions.json untuk dashboard")
    parser.add_argument("--force", action="store_true", help="Paksa fetch ulang meski sudah terupdate hari ini")
    parser.add_argument("--strict", action="store_true", help="Gagal (bukan fallback) jika fetch live gagal atau data basi (untuk CI)")
    args = parser.parse_args()
    predict_all(force=args.force, strict=args.strict)
