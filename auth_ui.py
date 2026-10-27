"""Halaman Login dan Create Account.

Login dan pembuatan akun terhubung ke PostgreSQL melalui ``auth.py``.
Forgot Password tidak disediakan; user yang lupa password menghubungi admin.
"""

from pathlib import Path

import streamlit as st

import auth

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

AUTH_CSS = """
<style>
    /* Halaman auth tampil tanpa sidebar dan header Streamlit. */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    header[data-testid="stHeader"] {
        display: none !important;
    }

    [data-testid="stAppViewContainer"] .block-container {
        padding-top: 12vh !important;
        padding-bottom: 4rem !important;
    }

    /* Cahaya hijau halus di belakang kartu; hanya aktif saat belum login. */
    [data-testid="stAppViewContainer"] {
        background-image: radial-gradient(
            ellipse 120% 60% at 50% -10%,
            rgba(125, 255, 155, 0.10),
            transparent 60%
        );
        background-repeat: no-repeat;
    }

    /* Kartu auth: netral terhadap tema terang & gelap. */
    .st-key-auth_page {
        max-width: 380px;
        margin: 0 auto;
        padding: 1.75rem 1.5rem 1.5rem;
        background: rgba(128, 128, 128, 0.07);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-top: 2px solid #7dff9b;
        border-radius: 8px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.16);
    }

    /* Logo brand di atas judul, dipusatkan di dalam kartu. */
    .st-key-auth_logo {
        align-items: center;
        margin-bottom: -0.5rem;
    }
    .st-key-auth_logo [data-testid="stImage"] {
        margin-bottom: 0;
    }

    .st-key-auth_page [data-testid="stVerticalBlock"] {
        gap: 0.75rem;
    }

    /* Header kartu: label brand, judul, subjudul. */
    .auth-brand {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%;
        text-align: center;
        margin-bottom: 0.35rem;
    }
    .auth-brand > * {
        width: 100%;
        text-align: center;
        margin-left: auto;
        margin-right: auto;
    }
    /* Streamlit menambahkan tautan jangkar ke heading markdown; ikon 16px itu
       ikut terhitung sehingga teks judul bergeser dari pusat kartu. */
    .st-key-auth_page .auth-brand [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    .auth-eyebrow {
        display: block;
        font-size: 10.5px;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        opacity: 0.55;
        margin-bottom: 0.4rem;
    }
    /* Selector diperkuat agar tidak kalah dari style markdown Streamlit. */
    .st-key-auth_page .auth-brand .auth-title {
        font-size: 22px !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        letter-spacing: normal !important;
        margin: 0 0 0.4rem 0 !important;
        padding: 0 !important;
        border: none !important;
    }
    .st-key-auth_page .auth-brand .auth-subtitle {
        font-size: 13px !important;
        font-weight: 400 !important;
        line-height: 1.45 !important;
        opacity: 0.7;
        margin: 0 !important;
    }

    /* Label field lebih kecil dan tenang. */
    .st-key-auth_page [data-testid="stWidgetLabel"] p {
        font-size: 12.5px;
        font-weight: 500;
        opacity: 0.85;
        margin-bottom: 0.2rem;
    }

    /* Input mengikuti tema, hanya border dan fokus yang diatur. */
    .st-key-auth_page [data-testid="stTextInputRootElement"] {
        background: transparent !important;
        border: 1px solid rgba(128, 128, 128, 0.4) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    .st-key-auth_page [data-testid="stTextInputRootElement"] > div {
        background: transparent !important;
        border-radius: 8px !important;
    }
    .st-key-auth_page input[data-testid="stTextInputField"] {
        background: transparent !important;
        color: inherit !important;
    }
    .st-key-auth_page input[data-testid="stTextInputField"]::placeholder {
        color: inherit;
        opacity: 0.55;
    }
    .st-key-auth_page [data-testid="stTextInputRootElement"] svg {
        color: inherit !important;
        fill: currentColor !important;
        opacity: 0.7;
    }
    .st-key-auth_page [data-testid="stTextInputRootElement"]:focus-within {
        border-color: rgba(125, 255, 155, 0.75) !important;
        box-shadow: 0 0 0 3px rgba(125, 255, 155, 0.15) !important;
    }

    /* Tombol utama form: penuh selebar kartu, teks gelap di atas hijau. */
    .st-key-auth_page [data-testid="stFormSubmitButton"] {
        margin-top: 0.9rem;
    }
    .st-key-auth_page [data-testid="stFormSubmitButton"] button {
        width: 100%;
        font-weight: 600;
        color: #0b0b0b !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .st-key-auth_page [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 20px rgba(125, 255, 155, 0.25);
    }
    .st-key-auth_page [data-testid="stFormSubmitButton"] button:active {
        transform: translateY(0);
        box-shadow: none;
    }

    /* Pesan validasi tetap di dalam alur kartu. */
    .st-key-auth_page [data-testid="stAlert"],
    .st-key-auth_page [data-testid="stAlertContainer"] {
        border-radius: 8px;
    }

    /* Tautan navigasi antar halaman auth tampil sebagai teks di tengah. */
    .st-key-auth_links {
        margin-top: 0.35rem;
        /* Container flex Streamlit rata kiri; regangkan agar tautan di tengah. */
        align-items: stretch !important;
        gap: 0.15rem !important;
    }
    .st-key-auth_links [data-testid="stVerticalBlock"] {
        gap: 0.15rem;
    }
    /* Wrapper tombol ikut selebar kartu agar teks tautan di tengah. */
    .st-key-auth_links [data-testid="stElementContainer"] {
        width: 100% !important;
    }
    .st-key-auth_links [data-testid="stButton"] {
        width: 100%;
    }
    .st-key-auth_page .stButton [data-testid="stBaseButton-tertiary"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        color: inherit !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 0 !important;
        min-height: 0 !important;
        width: 100% !important;
        justify-content: center !important;
        text-align: center !important;
        opacity: 0.75;
    }
    .st-key-auth_page .stButton [data-testid="stBaseButton-tertiary"]:hover {
        background: transparent !important;
        color: inherit !important;
        text-decoration: underline;
        opacity: 1;
    }
    .st-key-auth_page .stButton [data-testid="stBaseButton-tertiary"] p {
        font-size: 13px !important;
    }

    /* Keterangan lupa password di bawah form login. */
    .st-key-auth_links [data-testid="stCaptionContainer"] {
        width: 100%;
        text-align: center;
        opacity: 0.7;
        margin-bottom: 0.4rem !important;
    }
    .st-key-auth_links [data-testid="stCaptionContainer"] p {
        font-size: 12.5px;
        margin: 0;
    }

    /* Disclaimer di luar kartu, sejajar lebarnya dengan kartu. */
    .st-key-auth_footer {
        max-width: 380px;
        margin: 1.25rem auto 0;
    }
    .st-key-auth_footer [data-testid="stCaptionContainer"] {
        text-align: center;
        opacity: 0.55;
    }
    .st-key-auth_footer [data-testid="stCaptionContainer"] p {
        font-size: 12px;
    }

    @media (max-width: 420px) {
        [data-testid="stAppViewContainer"] .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .st-key-auth_page {
            padding: 1.5rem 1.15rem 1.25rem;
        }
    }
</style>
"""


def _brand(title: str, subtitle: str) -> None:
    """Header kartu auth: logo, label brand, judul halaman, dan subjudul."""
    with st.container(key="auth_logo"):
        st.image(
            str(ASSETS_DIR / "marko-icon.png"),
            width=52,
            alt="Logo Marko",
        )
    st.markdown(
        f"""
        <div class="auth-brand">
            <span class="auth-eyebrow">Markowitz Lab</span>
            <h1 class="auth-title">{title}</h1>
            <p class="auth-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _go(view: str) -> None:
    st.session_state["auth_view"] = view
    st.rerun()


def _render_login() -> None:
    _brand("Masuk", "Masuk untuk membuka dashboard prediksi aset crypto.")

    flash = st.session_state.pop("_auth_flash", None)
    if flash:
        st.success(flash)

    with st.form("form_login", border=False, enter_to_submit=False):
        identifier = st.text_input(
            "Email atau username",
            placeholder="nama@email.com atau username",
            key="login_identifier",
            icon=":material/person:",
            autocomplete="username",
        )
        password = st.text_input(
            "Kata sandi",
            type="password",
            key="login_password",
            icon=":material/lock:",
            autocomplete="current-password",
        )
        submitted = st.form_submit_button(
            "Masuk",
            type="primary",
            icon=":material/login:",
            width="stretch",
        )

    if submitted:
        if not identifier.strip() or not password:
            st.error("Email/username dan kata sandi wajib diisi.")
        else:
            user, error = auth.authenticate(identifier, password)
            if error:
                st.error(error)
            else:
                auth.start_session(user)

    with st.container(key="auth_links"):
        st.caption("Lupa kata sandi? Hubungi admin untuk reset.")
        if st.button("Buat akun", key="login_go_create", type="tertiary"):
            _go("create")


def _render_create_account() -> None:
    _brand("Buat akun", "Lengkapi data berikut untuk membuat akun baru.")

    with st.form("form_create_account", border=False, enter_to_submit=False):
        username = st.text_input(
            "Username",
            placeholder="contoh: Himalawa",
            key="create_username",
            icon=":material/person:",
            autocomplete="username",
        )
        email = st.text_input(
            "Email",
            placeholder="nama@email.com",
            key="create_email",
            type="email",
            autocomplete="email",
        )
        password = st.text_input(
            "Kata sandi",
            type="password",
            key="create_password",
            icon=":material/lock:",
            autocomplete="new-password",
            help="Minimal 8 karakter.",
        )
        confirm = st.text_input(
            "Konfirmasi kata sandi",
            type="password",
            key="create_confirm",
            icon=":material/lock:",
            autocomplete="new-password",
        )
        submitted = st.form_submit_button(
            "Buat akun",
            type="primary",
            icon=":material/person_add:",
            width="stretch",
        )

    if submitted:
        if (
            not username.strip()
            or not email.strip()
            or not password
            or not confirm
        ):
            st.error("Semua field wajib diisi.")
        elif password != confirm:
            st.error("Kata sandi dan konfirmasi tidak sama.")
        else:
            error = auth.create_user(username, email, password, role="user")
            if error:
                st.error(error)
            else:
                st.session_state["_auth_flash"] = (
                    "Akun berhasil dibuat. Silakan masuk."
                )
                _go("login")

    with st.container(key="auth_links"):
        if st.button("Kembali ke login", key="create_back", type="tertiary"):
            _go("login")


def render_auth() -> None:
    """Tampilkan halaman login atau create account."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    view = st.session_state.get("auth_view", "login")
    with st.container(key="auth_page"):
        if view == "create":
            _render_create_account()
        else:
            _render_login()

    with st.container(key="auth_footer"):
        st.caption(
            "Prototipe penelitian — bukan nasihat atau rekomendasi investasi."
        )
