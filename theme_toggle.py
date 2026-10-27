"""Tombol pengubah tema (dark / light) di pojok kiri bawah.

Streamlit tidak menyediakan API untuk mengganti tema dari kode Python.
Karena itu tombol ini menulis preferensi ke ``localStorage`` (kunci yang
dipakai Streamlit) lalu memuat ulang halaman.
"""

import streamlit as st

THEME_HTML = """
<style>
    #theme-toggle {
        position: fixed;
        left: 1rem;
        bottom: 1rem;
        z-index: 1000000;
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: rgba(128, 128, 128, 0.18);
        border: 1px solid rgba(128, 128, 128, 0.35);
        color: inherit;
        cursor: pointer;
        transition: background 0.2s, border-color 0.2s;
    }
    #theme-toggle:hover {
        background: rgba(128, 128, 128, 0.32);
        border-color: rgba(128, 128, 128, 0.55);
    }
    #theme-toggle .theme-icon {
        font-family: "Material Symbols Rounded";
        font-size: 20px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-feature-settings: "liga";
        -webkit-font-smoothing: antialiased;
        font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
    }
</style>
<button id="theme-toggle" type="button" title="Ganti tema" aria-label="Ganti tema">
    <span class="theme-icon" id="theme-icon-sun" aria-hidden="true">light_mode</span>
    <span class="theme-icon" id="theme-icon-moon" aria-hidden="true">dark_mode</span>
</button>
<script>
(function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;

    var PREFIX = "stActiveTheme-";
    var GLOBAL_KEY = "appThemeChoice";

    function currentKey() {
        return PREFIX + window.location.pathname + "-v2";
    }

    function syncTheme() {
        var stored = localStorage.getItem(GLOBAL_KEY);
        if (!stored) return;

        var cur = localStorage.getItem(currentKey());
        var guardKey = "appThemeSynced-" + window.location.pathname;

        if (cur === stored) {
            sessionStorage.setItem(guardKey, "1");
            return;
        }

        if (sessionStorage.getItem(guardKey)) {
            // Sudah disinkronkan di halaman ini: anggap user mengganti tema
            // lewat menu Settings Streamlit, lalu jadikan pilihan baru sebagai acuan.
            localStorage.setItem(GLOBAL_KEY, cur);
            for (var i = 0; i < localStorage.length; i++) {
                var k = localStorage.key(i);
                if (k && k.indexOf(PREFIX) === 0) localStorage.setItem(k, cur);
            }
            return;
        }

        sessionStorage.setItem(guardKey, "1");
        localStorage.setItem(currentKey(), stored);
        window.location.reload();
    }

    function preference() {
        try {
            return JSON.parse(localStorage.getItem(currentKey()) || '\"System\"');
        } catch (e) {
            return "System";
        }
    }

    function isDark() {
        var p = preference();
        if (p === "Dark") return true;
        if (p === "Light") return false;
        return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    }

    function paint() {
        var dark = isDark();
        var sun = document.getElementById("theme-icon-sun");
        var moon = document.getElementById("theme-icon-moon");
        if (sun) sun.style.display = dark ? "block" : "none";
        if (moon) moon.style.display = dark ? "none" : "block";
        var label = dark ? "Mode terang" : "Mode gelap";
        btn.title = label;
        btn.setAttribute("aria-label", label);
    }

    function setTheme(next) {
        var value = JSON.stringify(next);
        localStorage.setItem(GLOBAL_KEY, value);
        var keys = [];
        for (var i = 0; i < localStorage.length; i++) {
            var k = localStorage.key(i);
            if (k && k.indexOf(PREFIX) === 0) keys.push(k);
        }
        keys.forEach(function (k) { localStorage.setItem(k, value); });
        localStorage.setItem(currentKey(), value);
        window.location.reload();
    }

    btn.addEventListener("click", function () {
        setTheme(isDark() ? "Light" : "Dark");
    });

    syncTheme();
    paint();
})();
</script>
"""


def render_theme_toggle():
    """Tampilkan tombol bulat dark/light di pojok kiri bawah."""
    st.html(THEME_HTML, unsafe_allow_javascript=True)
