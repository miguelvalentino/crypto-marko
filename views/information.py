"""Halaman Information: Panduan Fitur Dashboard, Informasi Dataset, dan Spesifikasi Model."""

from pathlib import Path
import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def render_feature_image(filename: str, caption: str):
    """Tampilkan foto jika file ada di folder assets, atau placeholder jika belum ada."""
    img_path = ASSETS_DIR / filename
    if img_path.exists():
        st.image(str(img_path), caption=caption, width="stretch")
    else:
        st.info(
            f"📸 **Template Foto:** Masukkan tangkapan layar ke `assets/{filename}` "
            f"untuk menampilkan gambar di sini.",
            icon=":material/add_photo_alternate:",
        )


st.title("Pusat Informasi Penelitian")
st.caption(
    "Panduan komprehensif mengenai fitur-fitur pada dashboard Marko, "
    "karakteristik dataset yang digunakan, dan spesifikasi arsitektur model prediksi."
)

tab_fitur, tab_dataset, tab_model = st.tabs([
    "Fitur Dashboard",
    "Informasi Dataset",
    "Spesifikasi Model",
])

with tab_fitur:
    st.subheader("Panduan & Fungsi Fitur Dashboard")
    st.markdown(
        "Dashboard **Marko** dirancang untuk membantu investor dan peneliti dalam "
        "menganalisis tren harga cryptocurrency serta merumuskan strategi alokasi portofolio optimal."
    )

    with st.expander("1. Pemilih Model & Cryptocurrency", expanded=True):
        st.markdown(
            """
            * **Pilihan Model (`LSTM` / `TCN`):** Mengganti arsitektur deep learning yang digunakan untuk memproyeksikan harga masa depan dan menghitung analisis portofolio.
            * **Pilihan Cryptocurrency (`BTC` / `ETH` / `SOL`):** Menentukan aset kripto yang ingin diamati tren grafik historis dan metrik performanya secara detail.
            """
        )
        render_feature_image(
            "fitur1_pemilih_model.png",
            "Tangkapan Layar: Kontrol Pemilihan Model Deep Learning & Cryptocurrency",
        )

    with st.expander("2. Grafik Prediksi Interaktif", expanded=True):
        st.markdown(
            """
            * **Garis Aktual (*Actual - 60 hari*):** Menampilkan pergerakan harga penutupan (*Close Price*) riil selama 60 hari terakhir dari bursa Indodax (IDR).
            * **Garis Proyeksi (*Predicted*):** Garis putus-putus titik proyeksi masa depan pada beberapa horizon waktu ($H+1, H+3, H+7, H+14,$ dan $H+30$).
            * **Ringkasan Nilai:** Menyajikan harga penutupan terakhir beserta rincian estimasi harga untuk masing-masing horizon secara cepat.
            """
        )
        render_feature_image(
            "fitur2_grafik_prediksi.png",
            "Tangkapan Layar: Grafik Tren Harga Aktual (60 hari) dan Proyeksi Multi-Horizon",
        )

    with st.expander("3. Pemilihan Horizon Prediksi & Evaluasi Model", expanded=True):
        st.markdown(
            """
            * **Tombol Horizon (1, 3, 7, 14, 30 hari):** Menentukan rentang target perkiraan waktu yang digunakan untuk bagian evaluasi akurasi, perhitungan expected return, dan optimasi portofolio.
            * **Metrik Evaluasi Backtesting:**
                * **MAE (*Mean Absolute Error*):** Rata-rata selisih absolut antara harga aktual dan harga prediksi dalam satuan Rupiah (semakin kecil semakin akurat).
                * **RMSE (*Root Mean Squared Error*):** Mengukur deviasi prediksi dengan memberikan penalti lebih besar pada selisih ekstrim (satuan Rupiah).
                * **MAPE (*Mean Absolute Percentage Error*):** Rata-rata persentase kesalahan relatif. Metrik ini dapat dibandingkan langsung antar aset karena independen terhadap skala nominal harga.
                * **$R^2$ (*R-Squared Score*):** Menunjukkan seberapa baik variasi pergerakan harga mampu dijelaskan oleh model. Nilai mendekati 1 menandakan prediksi sangat mendekati tren sebenarnya.
            """
        )
        render_feature_image(
            "fitur3_evaluasi_model.png",
            "Tangkapan Layar: Pilihan Horizon Waktu dan Metrik Akurasi Model",
        )

    with st.expander("4. Analisis per Aset (Expected Return & Risiko)", expanded=True):
        st.markdown(
            r"""
            * **Expected Return ($\mu$):** Estimasi persentase imbal hasil aset berdasarkan proyeksi harga model relatif terhadap harga penutupan terakhir:
              $$\mu = \frac{\text{Harga Prediksi} - \text{Harga Terakhir}}{\text{Harga Terakhir}} \times 100\%$$
            * **Risiko ($\sigma$):** Volatilitas pergerakan aset yang dihitung dari deviasi standar matriks kovariansi data historis 90 hari disesuaikan dengan panjang horizon.
            """
        )
        render_feature_image(
            "fitur4_analisis_aset.png",
            "Tangkapan Layar: Tabel Expected Return & Risiko Volatilitas per Koin",
        )

    with st.expander("5. Rekomendasi Bobot Portofolio Markowitz", expanded=True):
        st.markdown(
            r"""
            * **Slider Batas Minimum Bobot:** Pengguna dapat membatasi alokasi minimum (default 20%) untuk memastikan tidak ada aset yang memiliki alokasi 0% (*diversifikasi terjamin*).
            * **Optimasi Rasio Sharpe:** Sistem mencari komposisi bobot $(W_{\text{BTC}}, W_{\text{ETH}}, W_{\text{SOL}})$ yang memaksimalkan *Sharpe Ratio* terhadap suku bunga bebas risiko (*Risk-Free Rate* berbasis BI Rate tahunan ~5.75%).
            * **Indikator Portofolio:** Menampilkan perkiraan total expected return portofolio, total risiko, dan nilai *Sharpe Ratio*.
            """
        )
        render_feature_image(
            "fitur5_bobot_markowitz.png",
            "Tangkapan Layar: Rekomendasi Alokasi Bobot Portofolio Markowitz",
        )

    with st.expander("6. Simulasi Modal Investasi", expanded=True):
        st.markdown(
            """
            * **Input Modal Awal (Rp):** Masukkan besaran modal yang ingin disimulasikan.
            * **Kalkulasi Alokasi:** Sistem secara otomatis membagi dana ke masing-masing koin berdasarkan bobot Markowitz, menghitung unit koin yang didapat, memproyeksikan nilai akhir portofolio, dan menampilkan estimasi laba/rugi (*PnL* nominal dan persentase).
            """
        )
        render_feature_image(
            "fitur6_simulasi_modal.png",
            "Tangkapan Layar: Formulir Input Modal dan Hasil Simulasi Investasi",
        )

with tab_dataset:
    st.subheader("Karakteristik & Struktur Dataset")
    st.markdown(
        "Dataset yang digunakan dalam penelitian ini merupakan data deret waktu (*time-series*) "
        "harga cryptocurrency gabungan (*merged*) dari dua bursa terkemuka."
    )

    col_data1, col_data2 = st.columns(2)
    with col_data1:
        st.markdown(
            """
            #### Aset Cryptocurrency
            1. **Bitcoin (BTC):** Aset kripto utama dengan kapitalisasi pasar terbesar di dunia.
            2. **Ethereum (ETH):** Platform smart contract dan aset kripto terbesar kedua.
            3. **Solana (SOL):** Blockchain generasi baru berkecepatan tinggi dengan volatilitas tinggi.
            """
        )
    with col_data2:
        st.markdown(
            """
            #### Sumber Dataset
            * **Indodax (Pasar Domestik IDR):** Menjadi pasar target utama prediksi harga dalam mata uang Rupiah.
            * **Binance (Pasar Global USDT):** Berperan sebagai fitur input eksternal untuk menangkap sentimen dan likuiditas pasar global.
            * **Bank Indonesia (Kurs Bunga BI):** Berfungsi untuk menghitung nilai dari Sharpe Ratio.
            """
        )

    st.markdown("---")
    st.markdown("#### Fitur Input (10 Fitur Teknikal)")
    st.markdown(
        "Setiap sampel input model dibentuk dari data transaksi harian (OHLCV) pada kedua bursa:"
    )

    df_fitur = [
        {"No": 1, "Nama Fitur": "Open_indodax", "Bursa": "Indodax (IDR)", "Deskripsi": "Harga pembukaan harian di Indodax"},
        {"No": 2, "Nama Fitur": "High_indodax", "Bursa": "Indodax (IDR)", "Deskripsi": "Harga tertinggi harian di Indodax"},
        {"No": 3, "Nama Fitur": "Low_indodax", "Bursa": "Indodax (IDR)", "Deskripsi": "Harga terendah harian di Indodax"},
        {"No": 4, "Nama Fitur": "Close_indodax", "Bursa": "Indodax (IDR)", "Deskripsi": "Harga penutupan harian di Indodax (Target Utama)"},
        {"No": 5, "Nama Fitur": "Volume_indodax", "Bursa": "Indodax (IDR)", "Deskripsi": "Volume perdagangan harian di Indodax"},
        {"No": 6, "Nama Fitur": "Open_binance", "Bursa": "Binance (USDT)", "Deskripsi": "Harga pembukaan harian di pasar global Binance"},
        {"No": 7, "Nama Fitur": "High_binance", "Bursa": "Binance (USDT)", "Deskripsi": "Harga tertinggi harian di pasar global Binance"},
        {"No": 8, "Nama Fitur": "Low_binance", "Bursa": "Binance (USDT)", "Deskripsi": "Harga terendah harian di pasar global Binance"},
        {"No": 9, "Nama Fitur": "Close_binance", "Bursa": "Binance (USDT)", "Deskripsi": "Harga penutupan harian di pasar global Binance"},
        {"No": 10, "Nama Fitur": "Volume_binance", "Bursa": "Binance (USDT)", "Deskripsi": "Volume perdagangan harian di pasar global Binance"},
    ]
    st.dataframe(df_fitur, width="stretch", hide_index=True)

    st.markdown("---")
    st.markdown("#### Pengolahan Data (*Preprocessing*)")
    st.markdown(
        r"""
        * **Window Size (Lookback Period):** **30 hari**. Model menerima input urutan data 30 hari ke belakang ($30 \times 10$ fitur) untuk memprediksi harga masa depan.
        * **Normalisasi Fitur:** Menggunakan `MinMaxScaler` yang disesuaikan (*fit*) hanya pada data latih (*training set*) untuk mencegah kebocoran data (*data leakage*).
        * **Inverse Transform:** Nilai prediksi output diskalakan kembali ke harga asli Rupiah menggunakan scaler khusus target pada masing-masing horizon.
        * **Multi-Horizon Forecasting:** Model dilatih secara terpisah untuk memprediksi 5 titik horizon waktu ($H+1, H+3, H+7, H+14,$ dan $H+30$).
        """
    )

with tab_model:
    st.subheader("Spesifikasi Teknis & Arsitektur Model")
    st.markdown(
        "Penelitian ini mengimplementasikan dua arsitektur *Deep Learning* untuk peramalan harga deret waktu. "
        "Berikut adalah rincian spesifikasi lapisan arsitektur, parameter, dan konfigurasi pelatihan yang digunakan:"
    )

    col_lstm, col_tcn = st.columns(2)

    with col_lstm:
        st.markdown(
            """
            ### 1. Arsitektur LSTM (Long Short-Term Memory)
            Model berbasis recurrent neural network untuk menangani ketergantungan temporal sekuensial.

            * **Dimensi Input:** `(Batch, 30, 10)` — *30 time steps × 10 fitur OHLCV*
            * **Lapisan 1 (LSTM Layer):** **64 unit**, memproses sekuens temporal dan meneruskan representasi status akhir (*return_sequences=False*).
            * **Lapisan 2 (Dropout Layer):** **Tingkat 0.2 (20%)**, untuk regularisasi dan mencegah *overfitting*.
            * **Lapisan 3 (Dense Layer):** **32 unit**, fungsi aktivasi **ReLU** untuk menangkap hubungan non-linear.
            * **Lapisan 4 (Output Layer):** **1 unit (Dense Linear)**, menghasilkan nilai harga skalar terprediksi.
            """
        )

    with col_tcn:
        st.markdown(
            r"""
            ### 2. Arsitektur TCN (Temporal Convolutional Network)
            Model berbasis konvolusi temporal 1D dengan sambungan residual dan filter kausal terdilatasi.

            * **Dimensi Input:** `(Batch, 30, 10)` — *30 time steps × 10 fitur OHLCV*
            * **Blok Residual (4 Tingkat Dilasi):**
                * Menggunakan dilation rate: $d \in \{1, 2, 4, 8\}$
                * Tiap blok berisi: `Conv1D(64 filters, kernel_size=3, padding="causal", activation="relu")` $\rightarrow$ `Dropout(0.2)` $\rightarrow$ `Conv1D(64 filters, kernel_size=3, padding="causal", activation="relu")`
                * Dilengkapi jalan pintas (*residual shortcut/Add*) dengan penyesuaian dimensi 1×1 jika diperlukan.
            * **Lapisan Pooling:** `GlobalAveragePooling1D` untuk merangkum representasi temporal.
            * **Lapisan Dense:** **32 unit**, fungsi aktivasi **ReLU**.
            * **Lapisan Output:** **1 unit (Dense Linear)** untuk nilai estimasi harga.
            """
        )

    st.markdown("---")
    st.markdown("####Konfigurasi Hyperparameter Pelatihan (*Training Setup*)")
    st.markdown(
        "Kedua model dilatih dengan lingkungan dan protokol hyperparameter yang setara (*fair comparison*):"
    )

    df_hyperparams = [
        {"Komponen / Hyperparameter": "Window Size (Lookback)", "Nilai / Pengaturan": "30 hari (30 time steps)"},
        {"Komponen / Hyperparameter": "Jumlah Fitur Input", "Nilai / Pengaturan": "10 fitur (OHLCV Indodax & Binance)"},
        {"Komponen / Hyperparameter": "Fungsi Optimasi (Optimizer)", "Nilai / Pengaturan": "Adam (Adaptive Moment Estimation)"},
        {"Komponen / Hyperparameter": "Tingkat Pembelajaran (Learning Rate)", "Nilai / Pengaturan": "0.0005 (5e-4)"},
        {"Komponen / Hyperparameter": "Fungsi Kerugian (Loss Function)", "Nilai / Pengaturan": "MSE (Mean Squared Error)"},
        {"Komponen / Hyperparameter": "Jumlah Epoch Maksimum", "Nilai / Pengaturan": "100 Epochs"},
        {"Komponen / Hyperparameter": "Ukuran Batch (Batch Size)", "Nilai / Pengaturan": "8"},
        {"Komponen / Hyperparameter": "Mekanisme Penghentian Dini (Early Stopping)", "Nilai / Pengaturan": "Monitor 'val_loss', Patience = 15, Restore Best Weights"},
        {"Komponen / Hyperparameter": "Pembagian Data (Train / Val / Test)", "Nilai / Pengaturan": "70% Latih / 15% Validasi / 15% Uji"},
    ]
    st.dataframe(df_hyperparams, width="stretch", hide_index=True)

    st.markdown("---")
    st.markdown("#### Ringkasan Komparasi Teknis: LSTM vs TCN")

    df_komparasi = [
        {
            "Parameter Teknis": "Unit / Filter Utama",
            "LSTM (Long Short-Term Memory)": "64 Hidden Units (LSTM Cell)",
            "TCN (Temporal Convolutional Network)": "64 Filters per Conv1D (4 Residual Blocks)",
        },
        {
            "Parameter Teknis": "Mekanisme Temporal",
            "LSTM (Long Short-Term Memory)": "Gated Recurrent (Forget, Input, Output)",
            "TCN (Temporal Convolutional Network)": "Dilated Causal Convolutions (Dilations: 1, 2, 4, 8; Kernel: 3)",
        },
        {
            "Parameter Teknis": "Regularisasi",
            "LSTM (Long Short-Term Memory)": "Dropout 20% setelah layer LSTM",
            "TCN (Temporal Convolutional Network)": "Dropout 20% di dalam tiap Residual Block",
        },
        {
            "Parameter Teknis": "Fully Connected Layers",
            "LSTM (Long Short-Term Memory)": "Dense(32, ReLU) → Dense(1)",
            "TCN (Temporal Convolutional Network)": "GlobalAvgPool1D → Dense(32, ReLU) → Dense(1)",
        },
        {
            "Parameter Teknis": "Sifat Komputasi",
            "LSTM (Long Short-Term Memory)": "Sekuensial berurutan langkah per langkah",
            "TCN (Temporal Convolutional Network)": "Paralel menyeluruh di seluruh urutan input",
        },
        {
            "Parameter Teknis": "Pencegahan Kebocoran Waktu",
            "LSTM (Long Short-Term Memory)": "Alami dari arah rekursif waktu",
            "TCN (Temporal Convolutional Network)": "Dipaksa melalui Causal Padding",
        },
    ]
    st.dataframe(df_komparasi, width="stretch", hide_index=True)
