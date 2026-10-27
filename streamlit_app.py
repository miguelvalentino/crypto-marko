"""Entry point aplikasi Streamlit.

Jalankan dengan:
    py -3.12 -m streamlit run streamlit_app.py
"""

from pathlib import Path

import streamlit as st

import auth
from auth_ui import render_auth
from common import init_state, inject_css
from theme_toggle import render_theme_toggle

# ========================= KONFIGURASI HALAMAN =========================
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

st.set_page_config(
    page_title="Marko | Dashboard Prediksi Aset Crypto",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
init_state()
render_theme_toggle()

# ========================= LOGIN (POSTGRESQL) =========================
if not auth.is_configured():
    auth.render_setup_needed()
    st.stop()

user = auth.current_user()
if user is None:
    render_auth()
    st.stop()

# ========================= BRAND =========================
st.logo(
    str(ASSETS_DIR / "marko-logo.png"),
    icon_image=str(ASSETS_DIR / "marko-icon.png"),
    size="large",
)

with st.sidebar:
    if st.button(
        "Logout",
        icon=":material/logout:",
        width="stretch",
        help="Keluar dari akun dan kembali ke halaman login.",
    ):
        st.session_state["auth_view"] = "login"
        auth.logout()

# ========================= NAVIGASI =========================
pages = [
    st.Page(
        "views/dashboard.py",
        title="Dashboard",
        icon=":material/space_dashboard:",
        default=True,
    ),
    st.Page(
        "views/evaluasi_model.py",
        title="Evaluasi Model",
        icon=":material/analytics:",
    ),
    st.Page(
        "views/information.py",
        title="Information",
        icon=":material/info:",
    ),
    st.Page(
        "views/about.py",
        title="About",
        icon=":material/article:",
    ),
    st.Page(
        "views/profile.py",
        title="Profile",
        icon=":material/account_circle:",
    ),
]

if user["role"] == "admin":
    pages.append(
        st.Page(
            "views/admin.py",
            title="Admin",
            icon=":material/admin_panel_settings:",
        )
    )

nav = st.navigation(pages)
nav.run()
