"""Helper untuk memicu GitHub Actions workflow dari aplikasi Streamlit.

Dipakai oleh halaman Admin untuk tombol "Perbarui data sekarang".
Konfigurasi disimpan di .streamlit/secrets.toml:

    [github]
    token = "ghp_..."          # PAT dengan scope actions:write
    owner = "miguelvalentino"
    repo = "crypto-marko"
    workflow = "update-predictions.yml"   # opsional, default ini
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


def _config() -> dict[str, str]:
    try:
        gh = st.secrets["github"]
    except Exception:
        gh = {}
    return {
        "token": os.environ.get("GITHUB_TOKEN", str(gh.get("token", "") or "")).strip(),
        "owner": os.environ.get("GITHUB_OWNER", str(gh.get("owner", "") or "")).strip(),
        "repo": os.environ.get("GITHUB_REPO", str(gh.get("repo", "") or "")).strip(),
        "workflow": os.environ.get(
            "GITHUB_WORKFLOW", str(gh.get("workflow", "update-predictions.yml") or "update-predictions.yml")
        ).strip(),
    }


def is_configured() -> bool:
    c = _config()
    return bool(c["token"] and c["owner"] and c["repo"])


def _headers() -> dict[str, str]:
    c = _config()
    return {
        "Authorization": f"Bearer {c['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def trigger_update(bi_rate: str | None = None) -> tuple[bool, str]:
    """Picu workflow_dispatch. Kembalikan (sukses, pesan)."""
    c = _config()
    if not is_configured():
        return False, (
            "GitHub Actions belum dikonfigurasi. Tambahkan [github] token/owner/repo "
            "di .streamlit/secrets.toml."
        )

    url = (
        f"https://api.github.com/repos/{c['owner']}/{c['repo']}"
        f"/actions/workflows/{c['workflow']}/dispatches"
    )
    payload: dict[str, Any] = {"ref": "main"}
    inputs: dict[str, Any] = {"force": True}
    if bi_rate:
        inputs["bi_rate"] = bi_rate
    payload["inputs"] = inputs

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    except requests.RequestException as exc:
        return False, f"Gagal menghubungi GitHub: {exc}"

    if resp.status_code == 204:
        return True, "Workflow dipicu. Cek tab Actions untuk status."
    if resp.status_code == 404:
        return False, "Workflow atau repo tidak ditemukan. Periksa nama file workflow."
    if resp.status_code == 403:
        return False, "Token tidak punya izin (butuh scope actions:write)."
    if resp.status_code == 422:
        return False, f"Parameter tidak valid: {resp.text[:200]}"
    return False, f"GitHub merespons {resp.status_code}: {resp.text[:200]}"


def latest_runs(limit: int = 5) -> list[dict]:
    """Ambil daftar run terbaru workflow. Kembalikan list kosong jika gagal."""
    c = _config()
    if not is_configured():
        return []
    url = (
        f"https://api.github.com/repos/{c['owner']}/{c['repo']}"
        f"/actions/workflows/{c['workflow']}/runs"
    )
    try:
        resp = requests.get(
            url, headers=_headers(), params={"per_page": limit}, timeout=15
        )
    except requests.RequestException:
        return []
    if resp.status_code != 200:
        return []
    runs = resp.json().get("workflow_runs", [])
    return [
        {
            "id": r["id"],
            "status": r["status"],          # queued | in_progress | completed
            "conclusion": r.get("conclusion"),  # success | failure | cancelled | None
            "event": r.get("event"),
            "created_at": r["created_at"],
            "html_url": r["html_url"],
        }
        for r in runs
    ]


def run_status_label(run: dict) -> str:
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status != "completed":
        return "Berjalan" if status == "in_progress" else "Antri"
    return {
        "success": "Sukses",
        "failure": "Gagal",
        "cancelled": "Dibatalkan",
    }.get(conclusion or "", conclusion or "-")