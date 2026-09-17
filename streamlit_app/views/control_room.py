from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_empty_state,
    render_lifecycle_badge,
    render_metric_cards,
    render_risk_badge,
)

_SYSTEM_STATUS_CSS = """
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
.case-decision-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--border);
    gap: 0.8rem;
}
.case-decision-row:last-child { border-bottom: none; }
.case-decision-id {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-primary);
}
.case-decision-meta {
    font-size: 0.82rem;
    color: var(--text-muted);
}
.case-decision-badges {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-shrink: 0;
}
</style>
"""


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def _render_status_row(label: str, is_online: bool) -> None:
    status_cls = "online" if is_online else "offline"
    status_text = "ONLINE" if is_online else "OFFLINE"
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
    st.markdown(_SYSTEM_STATUS_CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-title">{t("room_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("room_subtitle")}</div>', unsafe_allow_html=True)

    client = _get_client()

    try:
        health = client.health_sync()
        api_ok = health.get("status") == "ok"
    except Exception:
        api_ok = False

    if not api_ok:
        render_backend_offline()
        return

    st.markdown('<div class="case-status-panel">', unsafe_allow_html=True)
    st.markdown('<div class="case-status-title">CASE SYSTEM STATUS</div>', unsafe_allow_html=True)
    _render_status_row("FastAPI", True)
    _render_status_row("SQLite", True)

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

    _render_status_row("Groq", groq_online)
    _render_status_row("Ollama", ollama_online)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        pending_data = client.list_pending_review_sync(limit=100)
    except Exception:
        pending_data = {"count": 0, "decisions": []}

    pending_count = pending_data.get("count", 0)
    pending_decisions = pending_data.get("decisions", [])

    auto_count = 0
    review_count = 0
    escalate_count = 0
    for d in pending_decisions:
        action = d.get("action", "")
        if "approve" in action:
            auto_count += 1
        elif "reject" in action:
            review_count += 1
        elif "escalat" in action:
            escalate_count += 1

    render_metric_cards([
        {"label": t("room_pending_review"), "value": str(pending_count), "icon": "\u23f3", "color": "#a06800"},
        {"label": t("room_auto_approve"), "value": str(auto_count), "icon": "\u2714", "color": "#1a7a4a"},
        {"label": t("room_human_review"), "value": str(review_count), "icon": "\u2611", "color": "#a06800"},
        {"label": t("room_escalated"), "value": str(escalate_count), "icon": "\u26a0", "color": "#b82e2e"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"#### {t('room_pending_decisions')}")
    if not pending_decisions:
        render_empty_state(t("room_no_pending"))
    else:
        for d in pending_decisions[:10]:
            case_id = d.get("case_id", t("common_n_a"))
            decision_id = d.get("decision_id", t("common_n_a"))
            action = d.get("action", t("common_n_a"))
            urgency = d.get("urgency", t("common_n_a"))
            lifecycle = d.get("lifecycle", "ai_proposed")

            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(f'<div class="case-decision-id">{case_id}</div>', unsafe_allow_html=True)
                    st.caption(f"ID: `{decision_id[:16]}...`")
                with c2:
                    render_risk_badge(urgency)
                    st.caption(action.replace("_", " ").title())
                with c3:
                    render_lifecycle_badge(lifecycle)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### {t('room_quick_actions')}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(t("room_open_dc"), use_container_width=True):
            st.session_state["current_page"] = "decision_center"
            st.rerun()
    with c2:
        if st.button(t("room_browse"), use_container_width=True):
            st.session_state["current_page"] = "cases"
            st.rerun()
