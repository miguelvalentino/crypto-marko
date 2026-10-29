"""Autentikasi akun lokal (PostgreSQL) untuk aplikasi Streamlit.

Akun disimpan di schema ``public`` pada tabel ``users``. Password di-hash
dengan bcrypt; sesi disimpan di server dan token sesi dikirim ke browser
lewat cookie.

Login menerima email **atau** username. Profil memakai kolom ``username``
dan ``email``; tidak ada kolom ``name``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import bcrypt
import psycopg
import streamlit as st
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

SESSION_COOKIE = "markowitz_session"
SESSION_HOURS = 12
MAX_FAILED_ATTEMPTS = 5
FAILURE_WINDOW_MINUTES = 15
BCRYPT_ROUNDS = 12
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72

# Username disimpan dalam huruf kecil: 3-50 karakter.
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,49}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_DUMMY_HASH = bcrypt.hashpw(
    b"dummy-password", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
).decode("utf-8")


class AuthError(Exception):
    """Kesalahan autentikasi yang aman ditampilkan ke pengguna."""


def get_dsn() -> str:
    """Ambil DSN dari environment, lalu dari .streamlit/secrets.toml."""
    dsn = os.environ.get("AUTH_DB_DSN", "").strip()
    if dsn:
        return dsn
    try:
        return str(st.secrets["auth_db"]["dsn"]).strip()
    except Exception:
        return ""


def is_configured() -> bool:
    """True jika DSN database sudah tersedia."""
    return bool(get_dsn())


@contextmanager
def _connect():
    """Buka koneksi PostgreSQL; commit saat blok selesai tanpa error."""
    dsn = get_dsn()
    if not dsn:
        raise AuthError("Database autentikasi belum dikonfigurasi.")
    try:
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
            yield conn
    except psycopg.OperationalError as exc:
        raise AuthError("Tidak dapat terhubung ke database autentikasi.") from exc


# ========================= VALIDASI =========================
def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _username_error(username: str) -> str | None:
    if not USERNAME_RE.match(username):
        return (
            "Username harus 3-50 karakter dan hanya berisi huruf, angka, "
            "titik, garis bawah, atau strip."
        )
    return None


def _email_error(email: str) -> str | None:
    if not EMAIL_RE.match(email):
        return "Masukkan alamat email yang valid."
    return None


def _password_error(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password minimal {MIN_PASSWORD_LENGTH} karakter."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "Password terlalu panjang (maksimal 72 byte)."
    return None


def _role_error(role: str) -> str | None:
    if role not in ("user", "admin"):
        return "Role tidak valid."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verifikasi bcrypt; hash lama yang tidak valid dianggap gagal."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), stored_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


# ========================= LOGIN =========================
def _record_attempt(conn, identifier: str, success: bool) -> None:
    conn.execute(
        "INSERT INTO public.login_attempts (identifier, success) VALUES (%s, %s)",
        (identifier, success),
    )
    # Bersihkan riwayat lama agar tabel tidak terus membesar.
    conn.execute(
        "DELETE FROM public.login_attempts "
        "WHERE attempted_at < now() - interval '30 days'"
    )


def _too_many_failures(conn, identifier: str) -> bool:
    row = conn.execute(
        """
        SELECT count(*) AS n
        FROM public.login_attempts
        WHERE lower(identifier) = %s
          AND success = FALSE
          AND attempted_at > now() - make_interval(mins => %s)
        """,
        (identifier, FAILURE_WINDOW_MINUTES),
    ).fetchone()
    return bool(row and row["n"] >= MAX_FAILED_ATTEMPTS)


def authenticate(identifier: str, password: str) -> tuple[dict | None, str | None]:
    """Cek kredensial email/username dan password.

    Mengembalikan ``(user, None)`` jika valid, atau ``(None, pesan_error)``.
    """
    identifier = (identifier or "").strip().lower()
    if not identifier or not password:
        return None, "Email/username dan password wajib diisi."

    try:
        with _connect() as conn:
            if _too_many_failures(conn, identifier):
                return (
                    None,
                    "Terlalu banyak percobaan gagal. "
                    f"Coba lagi dalam {FAILURE_WINDOW_MINUTES} menit.",
                )

            row = conn.execute(
                """
                SELECT id, username, email, password_hash, role, is_active
                FROM public.users
                WHERE lower(username) = %s OR lower(email) = %s
                """,
                (identifier, identifier),
            ).fetchone()

            if row is None:
                # Tetap jalankan bcrypt agar waktu respons tidak membocorkan
                # apakah akun ada atau tidak.
                bcrypt.checkpw(
                    password.encode("utf-8"), _DUMMY_HASH.encode("utf-8")
                )
                _record_attempt(conn, identifier, False)
                return None, "Email/username atau password salah."

            if not _verify_password(password, row["password_hash"]):
                _record_attempt(conn, identifier, False)
                return None, "Email/username atau password salah."

            if not row["is_active"]:
                _record_attempt(conn, identifier, False)
                return None, "Akun ini dinonaktifkan. Hubungi admin."

            conn.execute(
                "UPDATE public.users SET last_login_at = now() WHERE id = %s",
                (row["id"],),
            )
            _record_attempt(conn, identifier, True)
            return (
                {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "role": row["role"],
                },
                None,
            )
    except AuthError as exc:
        return None, str(exc)
    except psycopg.Error:
        logger.exception("Gagal melakukan autentikasi")
        return None, "Terjadi kesalahan pada database."


# ========================= SESI =========================
def _cookie_value_from_header(name: str = SESSION_COOKIE) -> str | None:
    """Ambil cookie dari header Cookie (jalan di lokal; di Cloud proxy bisa membuangnya)."""
    try:
        cookie_header = st.context.headers.get("cookie", "") or ""
    except Exception:
        return None
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        part = part.strip()
        if "=" in part:
            key, _, value = part.partition("=")
            if key.strip() == name and value.strip():
                return value.strip()
    return None


# ========================= COOKIE DARI BROWSER (CLOUD) =========================
# Streamlit Community Cloud hanya meneruskan cookie yang ada di allowlist ke
# aplikasi. Cookie ``markowitz_session`` bukan bagian dari allowlist, sehingga
# tidak terbaca lewat header. Karena cookie ditulis lewat JavaScript, kita baca
# ulang dari ``document.cookie`` dengan komponen v2 (tanpa dependensi tambahan)
# yang berjalan di DOM halaman aplikasi.
_COOKIE_READER_JS = '''
export default function(component) {
    const { setStateValue } = component;
    function getCookie(name) {
        const escaped = name.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
        const match = document.cookie.match(new RegExp('(?:^|; )' + escaped + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : '';
    }
    const token = getCookie('markowitz_session');
    setStateValue('state', { token: token, ready: true });
}
'''

_cookie_reader_component = None


def _get_cookie_reader():
    global _cookie_reader_component
    if _cookie_reader_component is None:
        try:
            _cookie_reader_component = st.components.v2.component(
                "markowitz_cookie_reader", js=_COOKIE_READER_JS
            )
        except Exception:
            logger.exception("Gagal mendaftarkan komponen pembaca cookie")
            _cookie_reader_component = None
    return _cookie_reader_component


_BROWSER_COOKIE_KEY = "_auth_browser_cookie_token"
_BROWSER_COOKIE_READY_KEY = "_auth_browser_cookie_ready"


def _read_browser_cookie():
    reader = _get_cookie_reader()
    if reader is None:
        # Tidak bisa baca dari browser; jangan blokir aplikasi.
        return True, None
    try:
        result = reader(key="markowitz_cookie_reader_instance", on_state_change=lambda: None)
    except Exception:
        logger.exception("Gagal membaca cookie dari browser")
        return True, None
    state = getattr(result, "state", None)
    if not isinstance(state, dict) or not state.get("ready"):
        return False, None
    token = state.get("token")
    return True, (token.strip() if isinstance(token, str) and token.strip() else None)


def sync_browser_cookie():
    """Sinkronkan cookie browser ke session_state. Panggil sekali di awal run."""
    ready, token = _read_browser_cookie()
    st.session_state[_BROWSER_COOKIE_READY_KEY] = ready
    if ready:
        st.session_state[_BROWSER_COOKIE_KEY] = token or ""


def is_browser_cookie_ready():
    return bool(st.session_state.get(_BROWSER_COOKIE_READY_KEY, False))


_COOKIE_PENDING_KEY = "_auth_cookie_pending"


def _write_cookie(value: str, max_age: int) -> None:
    """Tulis atau hapus cookie sesi lewat JavaScript, tanpa reload halaman."""
    st.html(
        f"""
        <script>
        (function () {{
            document.cookie = "{SESSION_COOKIE}={value}; path=/; "
                + "max-age={max_age}; SameSite=Lax";
            document.cookie = "demo_session=; path=/; max-age=0; SameSite=Lax";
            document.cookie = "demo_profile=; path=/; max-age=0; SameSite=Lax";
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _queue_cookie(value: str, max_age: int) -> None:
    """Jadwalkan penulisan cookie pada rerun berikutnya.

    ``st.rerun()`` membuang elemen yang sudah dirender pada run saat ini,
    jadi script cookie harus dijalankan setelah rerun, bukan sebelumnya.
    """
    st.session_state[_COOKIE_PENDING_KEY] = (value, max_age)


def flush_pending_cookie() -> None:
    """Tulis cookie yang dijadwalkan. Panggil sekali di awal setiap run."""
    pending = st.session_state.pop(_COOKIE_PENDING_KEY, None)
    if pending:
        value, max_age = pending
        _write_cookie(value, max_age)


def start_session(user: dict) -> None:
    """Buat sesi server, simpan token, lalu tampilkan dashboard tanpa reload."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)

    try:
        with _connect() as conn:
            conn.execute("DELETE FROM public.sessions WHERE expires_at <= now()")
            conn.execute(
                """
                INSERT INTO public.sessions (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user["id"], token_hash, expires_at),
            )
    except AuthError as exc:
        st.error(str(exc))
        st.stop()
    except psycopg.Error:
        logger.exception("Gagal membuat sesi")
        st.error("Tidak dapat membuat sesi login. Coba lagi.")
        st.stop()

    st.session_state["_auth_user"] = user
    st.session_state["_auth_token_hash"] = token_hash
    # Cookie ditulis pada rerun berikutnya, setelah dashboard dirender.
    _queue_cookie(token, SESSION_HOURS * 3600)
    # Rerun langsung membuat dashboard tampil pada klik pertama, tanpa
    # memuat ulang halaman (penyebab bug "klik Masuk dua kali").
    st.rerun()


def _current_token_hash() -> str | None:
    """Ambil hash token sesi aktif dari state atau cookie."""
    token_hash = st.session_state.get("_auth_token_hash")
    if token_hash:
        return token_hash

    token = _cookie_value_from_header(SESSION_COOKIE)
    if not token:
        token = st.session_state.get(_BROWSER_COOKIE_KEY)
        if not token:
            token = None
    if not token:
        return None

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    st.session_state["_auth_token_hash"] = token_hash
    return token_hash


def current_user() -> dict | None:
    """Ambil pengguna dari sesi yang sedang aktif (cookie + database).

    Sesi divalidasi ulang ke database setiap kali dipanggil agar perubahan
    role, penonaktifan akun, atau reset password langsung berlaku.
    """
    token_hash = _current_token_hash()

    if not token_hash:
        # Tanpa token (misalnya pengujian yang menyetel state langsung),
        # gunakan state yang ada bila tersedia.
        return st.session_state.get("_auth_user")

    try:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.email, u.role
                FROM public.sessions s
                JOIN public.users u ON u.id = s.user_id
                WHERE s.token_hash = %s
                  AND s.expires_at > now()
                  AND u.is_active
                """,
                (token_hash,),
            ).fetchone()
    except AuthError:
        return None
    except psycopg.Error:
        logger.exception("Gagal memeriksa sesi")
        return None

    if row is None:
        st.session_state.pop("_auth_user", None)
        st.session_state.pop("_auth_token_hash", None)
        return None

    st.session_state["_auth_user"] = row
    st.session_state["_auth_token_hash"] = token_hash
    return row


def logout() -> None:
    """Hapus sesi di server dan bersihkan token lokal."""
    token_hash = _current_token_hash()
    if token_hash:
        try:
            with _connect() as conn:
                conn.execute(
                    "DELETE FROM public.sessions WHERE token_hash = %s",
                    (token_hash,),
                )
        except (AuthError, psycopg.Error):
            logger.exception("Gagal menghapus sesi")

    st.session_state.pop("_auth_user", None)
    st.session_state.pop("_auth_token_hash", None)
    st.session_state.pop(_BROWSER_COOKIE_KEY, None)
    st.session_state[_BROWSER_COOKIE_READY_KEY] = True
    # Hapus cookie pada rerun berikutnya; sesi di server sudah dihapus, jadi
    # cookie basi pun tidak bisa dipakai lagi.
    _queue_cookie("", 0)
    st.rerun()


def require_admin() -> dict:
    """Hentikan halaman jika pengguna bukan admin."""
    user = current_user()
    if user is None:
        st.error("Silakan masuk terlebih dahulu.")
        st.stop()
    if user["role"] != "admin":
        st.error("Halaman ini hanya dapat diakses oleh admin.")
        st.stop()
    return user


# ========================= KELOLA AKUN =========================
def list_users() -> list[dict]:
    """Daftar seluruh akun, admin lebih dulu."""
    with _connect() as conn:
        return conn.execute(
            """
            SELECT id, username, email, role, is_active, created_at, last_login_at
            FROM public.users
            ORDER BY CASE WHEN role = 'admin' THEN 0 ELSE 1 END, username
            """
        ).fetchall()


def create_user(
    username: str,
    email: str,
    password: str,
    role: str = "user",
) -> str | None:
    """Buat akun baru. Mengembalikan pesan error atau None jika berhasil."""
    username = normalize_username(username)
    email = normalize_email(email)
    error = (
        _username_error(username)
        or _email_error(email)
        or _password_error(password)
        or _role_error(role)
    )
    if error:
        return error

    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO public.users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (username, email, hash_password(password), role),
            )
        return None
    except psycopg.errors.UniqueViolation as exc:
        constraint = getattr(exc.diag, "constraint_name", "") or ""
        if "email" in constraint:
            return "Email sudah dipakai."
        if "username" in constraint:
            return "Username sudah dipakai."
        return "Username atau email sudah dipakai."
    except AuthError as exc:
        return str(exc)
    except psycopg.Error:
        logger.exception("Gagal membuat akun")
        return "Gagal membuat akun."


def update_profile(user_id: int, username: str, email: str) -> str | None:
    """Perbarui username dan email akun yang sedang masuk."""
    username = normalize_username(username)
    email = normalize_email(email)
    error = _username_error(username) or _email_error(email)
    if error:
        return error

    try:
        with _connect() as conn:
            updated = conn.execute(
                """
                UPDATE public.users
                SET username = %s, email = %s, updated_at = now()
                WHERE id = %s
                """,
                (username, email, user_id),
            ).rowcount
            if not updated:
                return "Akun tidak ditemukan."
    except psycopg.errors.UniqueViolation as exc:
        constraint = getattr(exc.diag, "constraint_name", "") or ""
        if "email" in constraint:
            return "Email sudah dipakai akun lain."
        if "username" in constraint:
            return "Username sudah dipakai akun lain."
        return "Username atau email sudah dipakai akun lain."
    except AuthError as exc:
        return str(exc)
    except psycopg.Error:
        logger.exception("Gagal memperbarui profil")
        return "Gagal memperbarui profil."

    current = st.session_state.get("_auth_user")
    if current and current.get("id") == user_id:
        current["username"] = username
        current["email"] = email
    return None


def change_password(
    user_id: int,
    old_password: str,
    new_password: str,
    keep_token_hash: str | None = None,
) -> str | None:
    """Ganti password sendiri dengan verifikasi password lama.

    Sesi saat ini dipertahankan; sesi di perangkat lain dicabut.
    """
    error = _password_error(new_password)
    if error:
        return error
    if not old_password:
        return "Password lama wajib diisi."

    keep_token = keep_token_hash or _current_token_hash()

    try:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT password_hash
                FROM public.users
                WHERE id = %s AND is_active
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                return "Akun tidak ditemukan atau sudah dinonaktifkan."

            if not _verify_password(old_password, row["password_hash"]):
                return "Password lama salah."

            if _verify_password(new_password, row["password_hash"]):
                return "Password baru harus berbeda dari password lama."

            conn.execute(
                """
                UPDATE public.users
                SET password_hash = %s, updated_at = now()
                WHERE id = %s
                """,
                (hash_password(new_password), user_id),
            )

            if keep_token:
                conn.execute(
                    """
                    DELETE FROM public.sessions
                    WHERE user_id = %s AND token_hash <> %s
                    """,
                    (user_id, keep_token),
                )
            else:
                conn.execute(
                    "DELETE FROM public.sessions WHERE user_id = %s",
                    (user_id,),
                )
        return None
    except AuthError as exc:
        return str(exc)
    except psycopg.Error:
        logger.exception("Gagal mengganti password")
        return "Gagal mengganti password."


def set_password(user_id: int, password: str) -> str | None:
    """Reset password oleh admin dan cabut semua sesi akun tersebut."""
    error = _password_error(password)
    if error:
        return error

    try:
        with _connect() as conn:
            updated = conn.execute(
                """
                UPDATE public.users
                SET password_hash = %s, updated_at = now()
                WHERE id = %s
                """,
                (hash_password(password), user_id),
            ).rowcount
            if not updated:
                return "Akun tidak ditemukan."
            conn.execute(
                "DELETE FROM public.sessions WHERE user_id = %s", (user_id,)
            )
        return None
    except AuthError as exc:
        return str(exc)
    except psycopg.Error:
        logger.exception("Gagal mengganti password")
        return "Gagal mengganti password."


def _active_admin_count(conn) -> int:
    row = conn.execute(
        "SELECT count(*) AS n FROM public.users "
        "WHERE role = 'admin' AND is_active = TRUE"
    ).fetchone()
    return int(row["n"]) if row else 0


def set_active(user_id: int, active: bool) -> str | None:
    """Aktifkan/nonaktifkan akun. Admin terakhir tidak boleh dinonaktifkan."""
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT role, is_active FROM public.users WHERE id = %s",
                (user_id,),
            ).fetchone()
            if row is None:
                return "Akun tidak ditemukan."

            if (
                not active
                and row["role"] == "admin"
                and row["is_active"]
                and _active_admin_count(conn) <= 1
            ):
                return "Tidak bisa menonaktifkan admin terakhir."

            conn.execute(
                """
                UPDATE public.users
                SET is_active = %s, updated_at = now()
                WHERE id = %s
                """,
                (active, user_id),
            )
            if not active:
                conn.execute(
                    "DELETE FROM public.sessions WHERE user_id = %s", (user_id,)
                )
        return None
    except AuthError as exc:
        return str(exc)
    except psycopg.Error:
        logger.exception("Gagal mengubah status akun")
        return "Gagal mengubah status akun."


def set_role(user_id: int, role: str) -> str | None:
    """Ubah role akun dan cabut sesinya agar role baru langsung berlaku."""
    error = _role_error(role)
    if error:
        return error

    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT role, is_active FROM public.users WHERE id = %s",
                (user_id,),
            ).fetchone()
            if row is None:
                return "Akun tidak ditemukan."

            if (
                row["role"] == "admin"
                and role != "admin"
                and row["is_active"]
                and _active_admin_count(conn) <= 1
            ):
                return "Tidak bisa menurunkan admin terakhir."

            conn.execute(
                "UPDATE public.users SET role = %s, updated_at = now() WHERE id = %s",
                (role, user_id),
            )
            conn.execute(
                "DELETE FROM public.sessions WHERE user_id = %s", (user_id,)
            )
        return None
    except AuthError as exc:
        return str(exc)
    except psycopg.Error:
        logger.exception("Gagal mengubah role")
        return "Gagal mengubah role."


# ========================= TAMPILAN =========================
def render_setup_needed() -> None:
    """Tampilan saat database autentikasi belum dikonfigurasi."""
    st.markdown(
        "<style>[data-testid='stSidebar'], "
        "[data-testid='stSidebarCollapsedControl'] {display: none;}</style>",
        unsafe_allow_html=True,
    )
    _, middle, _ = st.columns([1, 1.3, 1])
    with middle:
        st.write("")
        st.write("")
        st.title("Setup database diperlukan")
        st.write(
            "Aplikasi belum terhubung ke database PostgreSQL, jadi dashboard "
            "belum bisa dibuka."
        )
        st.markdown(
            """
            1. Salin `.streamlit/secrets.toml.example` menjadi
               `.streamlit/secrets.toml`.
            2. Isi `dsn` dengan koneksi ke database `prediksi_markowitz`.
            3. Jalankan `py -3.12 setup_auth.py` untuk menyiapkan tabel
               `public.users`, `public.sessions`, dan akun admin.
            """
        )
        st.code(
            "Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml",
            language="powershell",
        )
        st.code("py -3.12 setup_auth.py", language="powershell")
