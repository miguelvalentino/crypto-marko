"""Buat tabel autentikasi dan akun admin pertama.

Jalankan setelah database PostgreSQL ``prediksi_markowitz`` siap:

    py -3.12 setup_auth.py

DSN dibaca dari (urutan prioritas): argumen ``--dsn``, environment
``AUTH_DB_DSN``, lalu ``.streamlit/secrets.toml``.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
import tomllib
from pathlib import Path

import bcrypt
import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"
SECRETS_FILE = BASE_DIR / ".streamlit" / "secrets.toml"

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,49}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BCRYPT_ROUNDS = 12
MIN_PASSWORD_LENGTH = 8


def resolve_dsn(cli_value: str | None) -> str:
    if cli_value:
        return cli_value.strip()

    env_value = os.environ.get("AUTH_DB_DSN", "").strip()
    if env_value:
        return env_value

    if SECRETS_FILE.exists():
        try:
            data = tomllib.loads(SECRETS_FILE.read_text(encoding="utf-8"))
            return str(data.get("auth_db", {}).get("dsn", "")).strip()
        except (tomllib.TOMLDecodeError, OSError):
            pass

    return ""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


def run_schema(conn) -> None:
    """Jalankan schema.sql per statement (psycopg tidak menerima multi-query)."""
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)


def ask_credentials(args) -> tuple[str, str, str]:
    username = (
        args.admin_username or input("Username admin [admin]: ").strip() or "admin"
    ).lower()
    if not USERNAME_RE.match(username):
        sys.exit(
            "Username harus 3-50 karakter: huruf, angka, titik, garis bawah, "
            "atau strip."
        )

    email = (args.admin_email or input("Email admin: ").strip()).lower()
    if not EMAIL_RE.match(email):
        sys.exit("Masukkan alamat email admin yang valid.")

    if args.admin_password:
        password = args.admin_password
    else:
        password = getpass.getpass("Password admin: ")
        confirm = getpass.getpass("Ulangi password: ")
        if password != confirm:
            sys.exit("Password tidak sama.")

    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password minimal {MIN_PASSWORD_LENGTH} karakter.")
    if len(password.encode("utf-8")) > 72:
        sys.exit("Password terlalu panjang (maksimal 72 byte).")

    return username, email, password


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Buat tabel auth dan akun admin pertama di schema public."
    )
    parser.add_argument("--dsn", help="DSN PostgreSQL (opsional).")
    parser.add_argument("--admin-username", help="Username admin (default: admin).")
    parser.add_argument("--admin-email", help="Email admin.")
    parser.add_argument(
        "--admin-password",
        help="Password admin (opsional; jika kosong akan ditanya).",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Perbarui akun admin jika username/email sudah ada.",
    )
    args = parser.parse_args()

    dsn = resolve_dsn(args.dsn)
    if not dsn:
        sys.exit(
            "DSN belum tersedia. Isi .streamlit/secrets.toml, set "
            "AUTH_DB_DSN, atau gunakan --dsn."
        )

    username, email, password = ask_credentials(args)

    try:
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            print(
                f"Terhubung ke database '{conn.info.dbname}' "
                f"({conn.info.host}:{conn.info.port})."
            )
            run_schema(conn)

            existing = conn.execute(
                """
                SELECT id, username, email
                FROM public.users
                WHERE lower(username) = %s OR lower(email) = %s
                ORDER BY CASE WHEN lower(username) = %s THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (username, email, username),
            ).fetchone()

            if existing:
                if not args.update:
                    print(
                        f"Akun '{existing['username']}' <{existing['email']}> "
                        "sudah ada. Gunakan --update untuk mengganti data dan "
                        "memastikan role admin."
                    )
                    return
                conn.execute(
                    """
                    UPDATE public.users
                    SET username = %s, email = %s, password_hash = %s,
                        role = 'admin', is_active = TRUE,
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (username, email, hash_password(password), existing["id"]),
                )
                conn.execute(
                    "DELETE FROM public.sessions WHERE user_id = %s",
                    (existing["id"],),
                )
                print(f"Akun admin '{username}' <{email}> diperbarui.")
            else:
                conn.execute(
                    """
                    INSERT INTO public.users
                        (username, email, password_hash, role)
                    VALUES (%s, %s, %s, 'admin')
                    """,
                    (username, email, hash_password(password)),
                )
                print(f"Akun admin '{username}' <{email}> dibuat.")
    except psycopg.OperationalError as exc:
        sys.exit(f"Tidak dapat terhubung ke database: {exc}")
    except psycopg.errors.UniqueViolation as exc:
        sys.exit(
            "Username atau email sudah dipakai akun lain. "
            f"Detail: {exc.diag.message_detail or exc}"
        )
    except psycopg.Error as exc:
        sys.exit(f"Gagal menyiapkan database: {exc}")

    print("Selesai. Jalankan: py -3.12 -m streamlit run streamlit_app.py")


if __name__ == "__main__":
    main()
