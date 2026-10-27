-- Skema autentikasi aplikasi (PostgreSQL, schema public).
-- Aman dijalankan pada database prediksi_markowitz yang sudah memiliki
-- tabel public.users: tabel lama tidak dihapus, hanya dilengkapi.

CREATE TABLE IF NOT EXISTS public.users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'user'
                                 CHECK (role IN ('user', 'admin')),
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ
);

-- Lengkapi tabel users lama yang belum memiliki kolom status/login.
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Username/email unik tanpa membedakan huruf besar/kecil.
CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx
    ON public.users (lower(username));
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_idx
    ON public.users (lower(email));

CREATE TABLE IF NOT EXISTS public.sessions (
    id         BIGSERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    token_hash TEXT        NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_user_idx
    ON public.sessions (user_id);
CREATE INDEX IF NOT EXISTS sessions_expires_idx
    ON public.sessions (expires_at);

CREATE TABLE IF NOT EXISTS public.login_attempts (
    id           BIGSERIAL PRIMARY KEY,
    identifier   TEXT        NOT NULL,
    success      BOOLEAN     NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS login_attempts_lookup_idx
    ON public.login_attempts (lower(identifier), attempted_at DESC);
