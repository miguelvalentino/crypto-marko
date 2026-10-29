"""Halaman Admin: kelola akun pengguna dashboard."""

import pandas as pd
import streamlit as st

import auth
import github_actions

current = auth.require_admin()

st.title("Admin")
st.caption("Kelola akun pengguna dashboard.")

flash = st.session_state.pop("_admin_flash", None)
if flash:
    kind, message = flash
    if kind == "success":
        st.success(message)
    else:
        st.error(message)


def rerun_with_flash(kind: str, message: str) -> None:
    st.session_state["_admin_flash"] = (kind, message)
    st.rerun()

# ========================= PEMBARUAN DATA =========================
st.subheader("Pembaruan data prediksi")

# Tampilkan waktu generate terakhir.
_last_generated = "-"
try:
    import json, os
    _pred_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "predictions.json",
    )
    with open(_pred_path, encoding="utf-8") as _f:
        _pred = json.load(_f)
    _last_generated = _pred.get("meta", {}).get("generated_at", "-")
except Exception:
    _last_generated = "-"

st.caption(f"Terakhir diperbarui: {_last_generated}")

if not github_actions.is_configured():
    st.warning(
        "Pembaruan otomatis belum dikonfigurasi. Tambahkan bagian `[github]` "
        "(token, owner, repo) di `.streamlit/secrets.toml`."
    )
else:
    col_btn, col_status = st.columns([1, 2], vertical_alignment="center")
    with col_btn:
        if st.button(
            "Perbarui data sekarang",
            type="primary",
            width="stretch",
            key="admin_btn_update_data",
        ):
            ok, msg = github_actions.trigger_update()
            if ok:
                st.session_state["_admin_flash"] = ("success", msg)
            else:
                st.session_state["_admin_flash"] = ("error", msg)
            st.rerun()
    with col_status:
        runs = github_actions.latest_runs(limit=3)
        if runs:
            latest = runs[0]
            label = github_actions.run_status_label(latest)
            st.caption(
                f"Run terakhir: {label} · {latest['created_at'][:19].replace('T', ' ')}"
            )
            if latest.get("html_url"):
                st.markdown(f"[Lihat di GitHub]({latest['html_url']})")
        else:
            st.caption("Belum ada riwayat run.")

    if st.button("Segarkan status", key="admin_btn_refresh_runs"):
        st.rerun()

st.divider()

st.subheader("Buat akun")

with st.form("form_buat_akun", clear_on_submit=True):
    col_username, col_email, col_password, col_role = st.columns([2, 2, 2, 1])
    new_username = col_username.text_input("Username")
    new_email = col_email.text_input("Email")
    new_password = col_password.text_input(
        "Password", type="password", help="Minimal 8 karakter."
    )
    new_role = col_role.selectbox("Role", ["user", "admin"])
    submitted = st.form_submit_button("Buat akun", type="primary")

if submitted:
    error = auth.create_user(new_username, new_email, new_password, new_role)
    if error:
        st.error(error)
    else:
        rerun_with_flash(
            "success",
            f"Akun '{auth.normalize_username(new_username)}' berhasil dibuat.",
        )

st.subheader("Daftar akun")

try:
    users = auth.list_users()
except auth.AuthError as exc:
    st.error(str(exc))
    st.stop()

if not users:
    st.info("Belum ada akun.")
    st.stop()


def format_time(value) -> str:
    if not value:
        return "-"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


table = pd.DataFrame(
    [
        {
            "Username": user["username"],
            "Email": user["email"],
            "Role": "Admin" if user["role"] == "admin" else "User",
            "Status": "Aktif" if user["is_active"] else "Nonaktif",
            "Dibuat": format_time(user["created_at"]),
            "Login terakhir": format_time(user["last_login_at"]),
        }
        for user in users
    ]
)

st.dataframe(table, hide_index=True, width="stretch")

st.subheader("Aksi akun")

labels = {
    f"{user['username']} — {user['role']}"
    + ("" if user["is_active"] else " (nonaktif)"): user
    for user in users
}
selected_label = st.selectbox(
    "Pilih akun", list(labels), key="admin_pilih_akun"
)
selected = labels[selected_label]
is_self = selected["id"] == current["id"]

st.caption(
    f"Username: {selected['username']} · Email: {selected['email']} · "
    f"Role: {'Admin' if selected['role'] == 'admin' else 'User'} · "
    f"Status: {'Aktif' if selected['is_active'] else 'Nonaktif'}"
)

col_role, col_password = st.columns(2, gap="medium")

with col_role:
    with st.container(border=True):
        st.markdown("**Role**")
        st.caption("Ubah hak akses akun. Sesi akun akan dicabut.")
        new_role = st.selectbox(
            "Role baru",
            ["user", "admin"],
            index=0 if selected["role"] == "user" else 1,
            key=f"admin_role_{selected['id']}",
            disabled=is_self,
        )
        if st.button(
            "Ubah role",
            key=f"admin_btn_role_{selected['id']}",
            width="stretch",
            disabled=is_self,
        ):
            error = auth.set_role(selected["id"], new_role)
            if error:
                st.error(error)
            else:
                rerun_with_flash(
                    "success", f"Role '{selected['username']}' diubah."
                )

with col_password:
    with st.container(border=True):
        st.markdown("**Reset password**")
        st.caption("Minimal 8 karakter. Semua sesi akun akan dicabut.")
        new_password = st.text_input(
            "Password baru",
            type="password",
            key=f"admin_pw_{selected['id']}",
        )
        if st.button(
            "Reset password",
            key=f"admin_btn_pw_{selected['id']}",
            width="stretch",
        ):
            error = auth.set_password(selected["id"], new_password)
            if error:
                st.error(error)
            elif is_self:
                # Sesi sendiri ikut dicabut: kembali ke halaman login.
                auth.logout()
            else:
                rerun_with_flash(
                    "success", f"Password '{selected['username']}' direset."
                )

with st.container(border=True):
    col_status, col_status_action = st.columns(
        [3, 1], vertical_alignment="center"
    )
    with col_status:
        status_text = "Aktif" if selected["is_active"] else "Nonaktif"
        st.markdown(f"**Status akun: {status_text}**")
        st.caption("Akun nonaktif tidak bisa login.")
    with col_status_action:
        if selected["is_active"]:
            if st.button(
                "Nonaktifkan akun",
                key=f"admin_btn_nonaktif_{selected['id']}",
                width="stretch",
                disabled=is_self,
            ):
                error = auth.set_active(selected["id"], False)
                if error:
                    st.error(error)
                else:
                    rerun_with_flash(
                        "success",
                        f"Akun '{selected['username']}' dinonaktifkan.",
                    )
        else:
            if st.button(
                "Aktifkan akun",
                key=f"admin_btn_aktif_{selected['id']}",
                width="stretch",
            ):
                error = auth.set_active(selected["id"], True)
                if error:
                    st.error(error)
                else:
                    rerun_with_flash(
                        "success",
                        f"Akun '{selected['username']}' diaktifkan.",
                    )
