from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_metric_cards,
)

_SYSTEM_CSS = """
<style>
.case-status-panel {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.case-status-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-bottom: 0.8rem;
}
.case-status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.45rem 0;
    border-bottom: 1px solid var(--border);
}
.case-status-row:last-child { border-bottom: none; }
.case-status-label {
    font-size: 0.92rem;
    color: var(--text-primary);
    font-weight: 500;
}
.case-status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.82rem;
    font-weight: 600;
}
.case-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}
.case-status-dot--online { background: #1a7a4a; }
.case-status-dot--offline { background: #b82e2e; }
.case-status-text--online { color: #1a7a4a; }
.case-status-text--offline { color: #b82e2e; }
.case-provider-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.case-provider-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.35rem 0;
}
.case-provider-key {
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-weight: 500;
}
.case-provider-value {
    font-size: 0.9rem;
    color: var(--text-primary);
    font-weight: 600;
}
</style>
"""


def _check_url(url: str, timeout: float = 3.0) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


def _render_status_row(label: str, is_online: bool) -> None:
    status_cls = "online" if is_online else "offline"
    status_text = t("room_online") if is_online else t("room_offline_status")
    st.markdown(
        f'<div class="case-status-row">'
        f'<span class="case-status-label">{label}</span>'
        f'<span class="case-status-indicator">'
        f'<span class="case-status-dot case-status-dot--{status_cls}"></span>'
        f'<span class="case-status-text--{status_cls}">{status_text}</span>'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(_SYSTEM_CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-title">{t("room_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("room_subtitle")}</div>', unsafe_allow_html=True)

    client = get_client()

    # ── Gate: backend must be reachable ──
    try:
        health = client.health_sync()
        api_ok = health.get("status") in ("ok", "degraded")
    except Exception:
        api_ok = False

    if not api_ok:
        render_backend_offline()
        return

    # ── 1. SYSTEM STATUS ──
    st.markdown('<div class="case-status-panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="case-status-title">{t("room_section_system")}</div>', unsafe_allow_html=True)

    fastapi_online = True
    sqlite_online = health.get("database") == "ok"
    _render_status_row(t("room_fastapi"), fastapi_online)
    _render_status_row(t("room_sqlite"), sqlite_online)

    groq_online = False
    ollama_online = False
    try:
        providers_data = client.list_providers_sync()
        for p in providers_data.get("providers", []):
            name = p.get("name", "").lower()
            is_mock = p.get("is_mock", False)
            if "groq" in name:
                groq_online = not is_mock
            elif "ollama" in name:
                ollama_online = not is_mock
    except Exception:
        pass

    if groq_online:
        groq_online = _check_url("https://api.groq.com/models", timeout=4.0)
    if ollama_online:
        ollama_online = _check_url("http://localhost:11434/api/tags", timeout=3.0)

    _render_status_row(t("room_groq"), groq_online)
    _render_status_row(t("room_ollama"), ollama_online)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 2. DECISION METRICS ──
    st.markdown(f'<div class="case-status-title" style="margin-top:1rem;">{t("room_section_metrics")}</div>', unsafe_allow_html=True)

    decisions: list[dict[str, Any]] = []
    try:
        cases_data = client.list_cases_sync(limit=500, offset=0)
        decisions = cases_data.get("decisions", [])
    except Exception:
        decisions = []

    total = len(decisions)
    auto_approve = 0
    human_review = 0
    escalated = 0
    rejected = 0
    modified = 0

    for d in decisions:
        lifecycle = d.get("lifecycle", "")
        has_override = d.get("human_override") is not None

        if lifecycle == "approved" and not has_override:
            auto_approve += 1
        elif lifecycle == "under_review":
            human_review += 1
        elif lifecycle == "escalated":
            escalated += 1
        elif lifecycle == "rejected":
            rejected += 1
        elif lifecycle == "modified":
            modified += 1

    render_metric_cards([
        {"label": t("room_total_cases"), "value": str(total), "icon": "\u2139", "color": "#1a7a7a"},
        {"label": t("room_auto_approve"), "value": str(auto_approve), "icon": "\u2714", "color": "#1a7a4a"},
        {"label": t("room_human_review"), "value": str(human_review), "icon": "\u2611", "color": "#a06800"},
        {"label": t("room_escalated"), "value": str(escalated), "icon": "\u26a0", "color": "#b82e2e"},
        {"label": t("room_rejected"), "value": str(rejected), "icon": "\u2718", "color": "#b82e2e"},
        {"label": t("room_modified"), "value": str(modified), "icon": "\u270e", "color": "#6a3fb5"},
    ])

    # ── 3. PROVIDER STATUS ──
    st.markdown(f'<div class="case-status-title" style="margin-top:1rem;">{t("room_section_providers")}</div>', unsafe_allow_html=True)

    active_name = t("common_n_a")
    active_model = t("common_n_a")
    providers_list: list[dict[str, Any]] = []
    try:
        providers_data = client.list_providers_sync()
        active_name = providers_data.get("active_provider", t("common_n_a"))
        providers_list = providers_data.get("providers", [])
        for p in providers_list:
            if p.get("name") == active_name:
                active_model = p.get("model", t("common_n_a"))
                break
    except Exception:
        pass

    st.markdown(
        f'<div class="case-provider-card">'
        f'<div class="case-provider-row">'
        f'<span class="case-provider-key">{t("room_active_provider")}</span>'
        f'<span class="case-provider-value">{active_name}</span>'
        f'</div>'
        f'<div class="case-provider-row">'
        f'<span class="case-provider-key">{t("room_model")}</span>'
        f'<span class="case-provider-value">{active_model}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for p in providers_list:
        name = p.get("name", t("common_n_a"))
        is_mock = p.get("is_mock", False)
        online = not is_mock
        if "groq" in name.lower():
            online = groq_online
        elif "ollama" in name.lower():
            online = ollama_online
        _render_status_row(name, online)

    # ── 4. QUICK ACTIONS ──
    st.markdown(f'<div class="case-status-title" style="margin-top:1rem;">{t("room_quick_actions")}</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(t("room_open_dc"), use_container_width=True):
            st.session_state["current_page"] = "decision_center"
            st.rerun()
    with c2:
        if st.button(t("room_go_cases"), use_container_width=True):
            st.session_state["current_page"] = "cases"
            st.rerun()
    with c3:
        if st.button(t("room_open_review"), use_container_width=True):
            st.session_state["current_page"] = "review"
            st.rerun()
