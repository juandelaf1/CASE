from __future__ import annotations

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
.case-status-text--online { color: #1a7a4a; }
.case-status-text--offline { color: #b82e2e; }
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
.case-provider-model {
    font-size: 0.82rem;
    color: var(--text-muted);
}
</style>
"""


def render() -> None:
    st.markdown(_STATUS_CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-title">{t("triage_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("room_system_status")}</div>', unsafe_allow_html=True)

    client = get_client()

    api_online = False
    version = "N/A"
    try:
        health = client.health_sync()
        api_online = health.get("status") == "ok"
        version = health.get("version", "N/A")
    except Exception:
        pass

    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="case-status-section-title">{t("room_system_status")}</div>', unsafe_allow_html=True)

    status_cls = "online" if api_online else "offline"
    status_text = "ONLINE" if api_online else "OFFLINE"
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">API</span>'
        f'<span class="case-status-value">'
        f'<span class="case-status-dot case-status-dot--{status_cls}"></span>'
        f'<span class="case-status-text--{status_cls}">{status_text}</span>'
        f'</span>'
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

    db_online = api_online
    db_cls = "online" if db_online else "offline"
    db_text = "ONLINE" if db_online else "OFFLINE"
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">SQLite</span>'
        f'<span class="case-status-value">'
        f'<span class="case-status-dot case-status-dot--{db_cls}"></span>'
        f'<span class="case-status-text--{db_cls}">{db_text}</span>'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if not api_online:
        st.error(t("offline_title"))
        return

    try:
        domains = client.list_domains_sync()
    except Exception:
        domains = []

    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="case-status-section-title">{t("pl_config")}</div>', unsafe_allow_html=True)
    if domains:
        for d in domains:
            st.markdown(f'<span class="case-domain-tag">{d}</span>', unsafe_allow_html=True)
    else:
        st.caption(t("common_n_a"))
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        providers_data = client.list_providers_sync()
        providers = providers_data.get("providers", [])
        active = providers_data.get("active_provider", "unknown")
    except Exception:
        providers = []
        active = "unknown"

    st.markdown('<div class="case-status-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="case-status-section-title">{t("pl_configured")}</div>', unsafe_allow_html=True)
    if providers:
        for p in providers:
            name = p.get("name", "unknown")
            model = p.get("model", "unknown")
            is_mock = p.get("is_mock", False)
            is_active = name.lower() == active.lower()
            status_label = t("dc_provider_demo") if is_mock else model
            active_badge = " \u25cf" if is_active else ""
            st.markdown(
                f'<div class="case-provider-card">'
                f'<div>'
                f'<div class="case-provider-name">{name}{active_badge}</div>'
                f'<div class="case-provider-model">{status_label}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption(t("common_n_a"))
    st.markdown("</div>", unsafe_allow_html=True)
