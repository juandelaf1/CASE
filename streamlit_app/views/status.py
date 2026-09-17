from __future__ import annotations

import os

import httpx
import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t

_STATUS_CSS = """
<style>
.case-status-page {
    max-width: 800px;
}
.case-status-section {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.case-status-section-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-bottom: 0.9rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.case-status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border);
}
.case-status-row:last-child { border-bottom: none; }
.case-status-label {
    font-size: 0.92rem;
    color: var(--text-primary);
    font-weight: 500;
}
.case-status-value {
    font-size: 0.88rem;
    font-weight: 600;
}
.case-status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.4rem;
}
.case-status-dot--online { background: #1a7a4a; }
.case-status-dot--offline { background: #b82e2e; }
.case-status-dot--unknown { background: #a06800; }
.case-status-text--online { color: #1a7a4a; }
.case-status-text--offline { color: #b82e2e; }
.case-status-text--unknown { color: #a06800; }
.case-domain-tag {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    background: var(--brand-teal-light);
    color: var(--brand-teal);
    margin: 0.2rem 0.3rem 0.2rem 0;
}
.case-provider-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--border);
}
.case-provider-card:last-child { border-bottom: none; }
.case-provider-name {
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--text-primary);
}
.case-provider-detail {
    font-size: 0.82rem;
    color: var(--text-muted);
}
</style>
"""


def _status_dot(online: bool) -> str:
    cls = "online" if online else "offline"
    label = "ONLINE" if online else "OFFLINE"
    return (
        f'<span class="case-status-dot case-status-dot--{cls}"></span>'
        f'<span class="case-status-text--{cls}">{label}</span>'
    )


def _unknown_dot(label: str = "DESCONOCIDO") -> str:
    return (
        f'<span class="case-status-dot case-status-dot--unknown"></span>'
        f'<span class="case-status-text--unknown">{label}</span>'
    )


def _check_groq_health() -> tuple[bool, str]:
    api_key = os.environ.get("CASE_GROQ_API_KEY", "")
    if not api_key:
        return False, "API key no configurada (CASE_GROQ_API_KEY)"
    try:
        base_url = os.environ.get("CASE_GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        model = os.environ.get("CASE_GROQ_MODEL", "qwen/qwen3.8-27b")
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if response.status_code == 200:
                return True, model
            return False, f"Error HTTP {response.status_code}"
    except Exception as exc:
        return False, f"Error de conexion: {exc}"


def _check_ollama_health() -> tuple[bool, str]:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if models:
                    return True, f"{model} ({len(models)} modelos disponibles)"
                return True, model
            return False, f"Error HTTP {response.status_code}"
    except Exception:
        return False, "Ollama no disponible en localhost:11434"


def render() -> None:
    st.markdown(_STATUS_CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-title">{t("status_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("status_subtitle")}</div>', unsafe_allow_html=True)

    client = get_client()

    api_online = False
    version = "N/A"
    db_status = "desconocido"
    db_path = "N/A"
    try:
        health = client.health_sync()
        api_online = health.get("status") == "ok"
        version = health.get("version", "N/A")
        db_status = health.get("database", "desconocido")
        db_path = health.get("db_path", "N/A")
    except Exception:
        pass

    # ── Section 1: API Status ──
    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="case-status-section-title">{t("room_system_status")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">API</span>'
        f'<span class="case-status-value">{_status_dot(api_online)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Version</span>'
        f'<span class="case-status-value">{version}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if not api_online:
        st.error(t("offline_title"))
        st.caption(t("offline_start_api"))
        return

    # ── Section 2: Database ──
    db_online = db_status == "ok"
    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="case-status-section-title">{t("room_sqlite")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Estado</span>'
        f'<span class="case-status-value">{_status_dot(db_online)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Ruta</span>'
        f'<span class="case-status-value">{db_path}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Detalle</span>'
        f'<span class="case-status-value">{db_status}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Section 3: Providers ──
    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="case-status-section-title">{t("pl_configured")}</div>',
        unsafe_allow_html=True,
    )

    groq_ok, groq_detail = _check_groq_health()
    ollama_ok, ollama_detail = _check_ollama_health()

    providers_data = {}
    try:
        providers_data = client.list_providers_sync()
    except Exception:
        pass

    provider_list = providers_data.get("providers", [])
    active_provider = providers_data.get("active_provider", "unknown")

    provider_checks = [
        ("Groq", groq_ok, groq_detail),
        ("Ollama", ollama_ok, ollama_detail),
        ("Mock", True, "Siempre disponible (demo determinista)"),
    ]

    for name, ok, detail in provider_checks:
        is_active = name.lower() == active_provider.lower()
        active_badge = " \u25cf" if is_active else ""
        status_html = _status_dot(ok)
        st.markdown(
            f'<div class="case-provider-card">'
            f'<div>'
            f'<div class="case-provider-name">{name}{active_badge}</div>'
            f'<div class="case-provider-detail">{detail}</div>'
            f'</div>'
            f'<div class="case-status-value">{status_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Section 4: Configuration ──
    try:
        domains = client.list_domains_sync()
    except Exception:
        domains = []

    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="case-status-section-title">{t("pl_config")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Dominios registrados</span>'
        f'<span class="case-status-value">{len(domains)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if domains:
        tags_html = "".join(
            f'<span class="case-domain-tag">{d}</span>' for d in domains
        )
        st.markdown(
            f'<div style="padding:0.4rem 0;">{tags_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Proveedor activo</span>'
        f'<span class="case-status-value">{active_provider}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Version</span>'
        f'<span class="case-status-value">{version}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Section 5: System Info ──
    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="case-status-section-title">{t("room_section_system")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Que es CASE</span>'
        f'<span class="case-status-value" style="font-weight:400; max-width:60%; text-align:right;">'
        f'Plataforma de orquestacion de decisiones con supervision humana</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Proveedores</span>'
        f'<span class="case-status-value" style="font-weight:400; max-width:60%; text-align:right;">'
        f'Groq (nube), Ollama (local), Mock (demo)</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Persistencia</span>'
        f'<span class="case-status-value" style="font-weight:400; max-width:60%; text-align:right;">'
        f'SQLite para decisiones y auditoria</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Seguridad</span>'
        f'<span class="case-status-value" style="font-weight:400; max-width:60%; text-align:right;">'
        f'Nunca muestra API keys o secretos</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
