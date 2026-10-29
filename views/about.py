"""Halaman About: Identitas Penelitian, Profil Pengembang, Alur Perancangan, dan Tech Stack."""

import streamlit as st

st.markdown(
    """
    <style>
        /* Pastikan seluruh container ber-border di dalam kolom otomatis sama tinggi */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
        }
        [data-testid="column"] > div {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
        }
        [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"] {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
        }
        [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"] > div {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# HEADER & IDENTITAS SKRIPSI
st.title("Tentang Penelitian & Aplikasi")
st.caption("Dokumentasi perancangan sistem, profil pengembang, dan batasan penelitian skripsi.")

with st.container(border=True):
    st.markdown("### Identitas Tugas Akhir / Skripsi")
    st.markdown(
        """
        **Judul Penelitian:**  
        Perbandingan Algoritma TCN dan Long Short-Term Memory untuk Prediksi Harga dalam Optimasi Portofolio Markowitz pada Cryptocurrency Blue-Chip di Bursa Lokal

        **Perguruan Tinggi:**  
        Program Studi Teknik Informatika
        Fakultas Teknologi Informasi — Universitas Tarumanagara  
        **Tahun Akademik:** 2023
        """
    )

st.write("")

st.subheader("Profil di Balik Perancangan")
st.write("Sistem ini dikembangkan sebagai bagian dari penelitian tugas akhir sarjana.")

col_author, col_supervisor = st.columns(2)

with col_author:
    with st.container(border=True, height=270):
        st.markdown("#### Pengembang")
        st.markdown(
            """
            * **Nama Lengkap:** Miguel Valentino William
            * **Nomor Induk Mahasiswa (NIM):** 535230111
            * **Program Studi:** Teknik Informatika
            * **Fokus Peminatan:** Data Science
            * **Email:** miguel.535230111@stu.untar.ac.id
            """
        )

with col_supervisor:
    with st.container(border=True, height=270):
        st.markdown("#### Dosen Pembimbing")
        st.markdown(
            """
            * **Dosen Pembimbing I:**  
              **Tony, S.Kom., M.Kom., Ph.D** 

            * **Dosen Pembimbing Pendamping:**  
              **Irvan Lewenusa, S.Kom., M.Kom**  
            """
        )

st.write("")

st.subheader("Alur Perancangan Sistem")
st.write(
    "Tahapan metodologi penelitian dari ekstraksi data hingga penerapan sistem interaktif:"
)

col_step1, col_step2, col_step3 = st.columns(3)
with col_step1:
    with st.container(border=True, height=240):
        st.markdown("##### 1. Pengumpulan Data")
        st.caption("Data Ingestion & Extraction")
        st.markdown(
            """
            * Ekstraksi data historis harian dari **Indodax** (pasar IDR) dan **Binance** (pasar global).
            * Pengambilan 10 fitur OHLCV (*Open, High, Low, Close, Volume*).
            """
        )

with col_step2:
    with st.container(border=True, height=240):
        st.markdown("##### 2. Pra-pemrosesan Data")
        st.caption("Data Cleaning & Sequencing")
        st.markdown(
            r"""
            * Penggabungan (*merged*) data lintas bursa berdasarkan stempel waktu.
            * Normalisasi `MinMaxScaler` pada data latih.
            * Pembentukan sekuens *sliding window* 30 hari dan target $H \in \{1, 3, 7, 14, 30\}$.
            """
        )

with col_step3:
    with st.container(border=True, height=240):
        st.markdown("##### 3. Pelatihan Model")
        st.caption("Deep Learning Training")
        st.markdown(
            """
            * Pembangunan arsitektur **LSTM (64 unit)** dan **TCN (4 blok dilasi)**.
            * Pelatihan dengan Early Stopping dan optimasi Adam ($lr=0.0005$).
            * Evaluasi metrik MAE, RMSE, MAPE, dan $R^2$.
            """
        )

col_step4, col_step5, col_step6 = st.columns(3)
with col_step4:
    with st.container(border=True, height=240):
        st.markdown("##### 4. Optimasi Portofolio")
        st.caption("Modern Portfolio Theory")
        st.markdown(
            """
            * Konversi harga proyeksi ke *Expected Return* harian.
            * Estimasi risiko dari matriks kovariansi 90 hari.
            * Alokasi bobot optimal Markowitz berbasis rasio Sharpe maksimal.
            """
        )

with col_step5:
    with st.container(border=True, height=240):
        st.markdown("##### 5. Pengembangan Web")
        st.caption("Dashboard Marko Implementation")
        st.markdown(
            """
            * Desain antarmuka pengguna berbasis **Streamlit**.
            * Visualisasi interaktif tren harga dan titik proyeksi dengan **Plotly**.
            * Autentikasi pengguna berbasis peran (*Admin & User*) via PostgreSQL.
            """
        )

with col_step6:
    with st.container(border=True, height=240):
        st.markdown("##### 6. Pengujian & Deployment")
        st.caption("System Validation & Release")
        st.markdown(
            """
            * Pengujian fungsionalitas fitur dan simulasi modal.
            * Validasi hasil kalkulasi bobot portofolio.
            * Penyiapan *environment deployment* untuk produksi cloud.
            """
        )

st.write("")

st.subheader("Batasan & Ruang Lingkup Penelitian")

with st.expander("Lihat Rincian Batasan Masalah Penelitian", expanded=True):
    st.markdown(
        """
        Untuk menjaga fokus dan keakuratan analisis, penelitian ini memiliki batasan-batasan berikut:
        1. **Aset Penelitian:** Dibatasi pada 3 cryptocurrency dengan likuiditas tinggi, yaitu **Bitcoin (BTC)**, **Ethereum (ETH)**, dan **Solana (SOL)**.
        2. **Interval Waktu Data:** Menggunakan data deret waktu harian (*daily timeframe*), tidak mencakup fluktuasi jangka sangat pendek (*intraday / tick data*).
        3. **Variabel Prediksi:** Menggunakan analisis data teknikal historis harga dan volume (OHLCV) dari bursa Indodax dan Binance, tanpa memperhitungkan variabel fundamental atau analisis sentimen berita/media sosial.
        4. **Asumsi Portofolio:** Simulasi alokasi dana dan peramalan mengabaikan biaya transaksi (*trading fee*), pajak, serta *slippage* eksekusi pasar riil.
        """
    )

st.write("")

st.subheader("Teknologi & Tools yang Digunakan")

col_tech1, col_tech2, col_tech3, col_tech4 = st.columns(4)
with col_tech1:
    with st.container(border=True):
        st.markdown("**Bahasa & Web**")
        st.caption("Python 3.12")
        st.caption("Streamlit Framework")
with col_tech2:
    with st.container(border=True):
        st.markdown("**Deep Learning**")
        st.caption("TensorFlow / Keras")
        st.caption("Scikit-Learn")
with col_tech3:
    with st.container(border=True):
        st.markdown("**Data & Optimasi**")
        st.caption("Pandas & NumPy")
        st.caption("SciPy Optimize")
with col_tech4:
    with st.container(border=True):
        st.markdown("**Database & Visual**")
        st.caption("PostgreSQL & bcrypt")
        st.caption("Plotly Interactive Graph")

st.write("")

st.divider()

with st.container(border=True):
    st.markdown("#### Pernyataan Pelepasan Tanggung Jawab (*Disclaimer*)")
    st.caption(
        "Aplikasi **Marko** ini dirancang dan dibangun semata-mata untuk keperluan akademis "
        "dan penelitian tugas akhir sarjana (skripsi). Segala bentuk proyeksi harga, kalkulasi metrik, "
        "dan rekomendasi alokasi bobot portofolio merupakan hasil estimasi komputasi model "
        "dan **BUKAN merupakan nasihat keuangan (*financial advice*), ajakan, atau rekomendasi "
        "investasi riil**. Penulis dan pihak universitas tidak bertanggung jawab atas keputusan "
        "finansial yang diambil oleh pihak mana pun."
    )

col_footer_l, col_footer_r = st.columns([8, 2])
with col_footer_l:
    st.caption("© 2024-2025 Marko Dashboard. Hak Cipta Penelitian Tugas Akhir.")
with col_footer_r:
    st.caption("Versi Aplikasi: **v1.0.0 (Build Skripsi)**")
