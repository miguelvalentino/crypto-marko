"""Halaman Profile: informasi akun, edit profil, dan ganti password."""

import streamlit as st

import auth

user = auth.current_user()
if user is None:
    st.error("Sesi login tidak ditemukan. Silakan masuk kembali.")
    st.stop()

st.title("Profile")
st.caption("Informasi akun. Perubahan disimpan ke database.")

flash = st.session_state.pop("_profile_flash", None)
if flash:
    st.success(flash)

with st.container(border=True):
    col_username, col_email = st.columns(2)
    with col_username:
        st.caption("Username")
        st.markdown(f"**{user['username']}**")
    with col_email:
        st.caption("Email")
        st.markdown(f"**{user['email']}**")

st.subheader("Ubah profil")

with st.form("form_profile", border=False, enter_to_submit=False):
    col_username, col_email = st.columns(2)
    username = col_username.text_input("Username", value=user["username"])
    email = col_email.text_input("Email", value=user["email"])
    submitted_profile = st.form_submit_button(
        "Simpan perubahan", type="primary"
    )

if submitted_profile:
    error = auth.update_profile(user["id"], username, email)
    if error:
        st.error(error)
    else:
        st.session_state["_profile_flash"] = "Profil berhasil diperbarui."
        st.rerun()

st.divider()
st.subheader("Ubah password")
st.caption(
    "Masukkan password lama untuk mengganti password. "
    "Sesi di perangkat lain akan dikeluarkan."
)

with st.form("form_change_password", border=False, enter_to_submit=False):
    old_password = st.text_input(
        "Password lama", type="password", key="profile_old_password"
    )
    new_password = st.text_input(
        "Password baru",
        type="password",
        key="profile_new_password",
        help="Minimal 8 karakter.",
    )
    confirm_password = st.text_input(
        "Konfirmasi password baru",
        type="password",
        key="profile_confirm_password",
    )
    submitted_password = st.form_submit_button(
        "Simpan password", type="primary"
    )

if submitted_password:
    if not old_password or not new_password or not confirm_password:
        st.error("Semua field password wajib diisi.")
    elif new_password != confirm_password:
        st.error("Password baru dan konfirmasi tidak sama.")
    elif new_password == old_password:
        st.error("Password baru harus berbeda dari password lama.")
    else:
        error = auth.change_password(user["id"], old_password, new_password)
        if error:
            st.error(error)
        else:
            st.session_state["_profile_flash"] = (
                "Password berhasil diubah. Sesi di perangkat lain telah "
                "dikeluarkan."
            )
            st.rerun()

st.caption("Jika Anda lupa password, hubungi admin untuk reset password.")
