from __future__ import annotations

import os
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
.case-hero {
    text-align: center;
    padding: 2rem 1rem 1.5rem;
    margin-bottom: 1.5rem;
    background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-surface-alt, var(--bg-surface)) 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
}
.case-hero-title {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    color: var(--text-primary);
    margin-bottom: 0.3rem;
}
.case-hero-subtitle {
    font-size: 0.95rem;
    color: var(--text-secondary);
    font-weight: 500;
    margin-bottom: 0.6rem;
}
.case-hero-desc {
    font-size: 0.88rem;
    color: var(--text-secondary);
    max-width: 600px;
    margin: 0 auto;
    line-height: 1.5;
}
.case-section-title {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin: 1.5rem 0 0.6rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--border);
}
.case-flow-row {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    flex-wrap: wrap;
    margin: 0.5rem 0;
}
.case-flow-step {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.35rem 0.7rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
}
.case-flow-arrow {
    color: var(--text-secondary);
    font-size: 0.75rem;
    font-weight: 600;
}
.case-domain-badge {
    display: inline-block;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.3rem 0.6rem;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text-primary);
    margin: 0.2rem;
}
.case-pending-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-left: 3px solid #a06800;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
}
.case-pending-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-primary);
}
.case-pending-meta {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-top: 0.2rem;
}
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
.case-evidence-badge {
    display: inline-block;
    border-radius: 4px;
    padding: 0.15rem 0.5rem;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.case-evidence-badge--real { background: #d4edda; color: #155724; }
.case-evidence-badge--deterministic { background: #fff3cd; color: #856404; }
.case-evidence-badge--synthetic { background: #e2e3e5; color: #383d41; }
</style>
"""


def _check_url(url: str, timeout: float = 3.0, headers: dict[str, str] | None = None) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers or {})
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

    # ── 1. HERO: What is CASE? ──
    version = health.get("version", "?")
    st.markdown(
        f'<div class="case-hero">'
        f'<div class="case-hero-title">{t("room_hero_title")}</div>'
        f'<div class="case-hero-subtitle">{t("room_hero_subtitle")} — v{version}</div>'
        f'<div class="case-hero-desc">{t("room_hero_desc")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 2. SYSTEM OVERVIEW ──
    st.markdown(f'<div class="case-section-title">{t("room_section_overview")}</div>', unsafe_allow_html=True)

    db_ok = health.get("database") == "ok"
    status_text = t("room_healthy") if health.get("status") == "ok" else t("room_degraded")

    st.markdown(
        f'<div class="case-status-panel">'
        f'<div class="case-status-row">'
        f'<span class="case-status-label">{t("room_uptime")}</span>'
        f'<span class="case-status-indicator">'
        f'<span class="case-status-dot case-status-dot--{"online" if api_ok else "offline"}"></span>'
        f'<span class="case-status-text--{"online" if api_ok else "offline"}">{status_text}</span>'
        f'</span>'
        f'</div>'
        f'<div class="case-status-row">'
        f'<span class="case-status-label">{t("room_version")}</span>'
        f'<span class="case-status-label" style="font-weight:600;">{version}</span>'
        f'</div>'
        f'<div class="case-status-row">'
        f'<span class="case-status-label">{t("room_database")}</span>'
        f'<span class="case-status-indicator">'
        f'<span class="case-status-dot case-status-dot--{"online" if db_ok else "offline"}"></span>'
        f'<span class="case-status-text--{"online" if db_ok else "offline"}">{"OK" if db_ok else t("room_offline_status")}</span>'
        f'</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 3. ACTIVE DOMAINS ──
    st.markdown(f'<div class="case-section-title">{t("room_section_domains")}</div>', unsafe_allow_html=True)

    domains = health.get("domains", [])
    domain_count = health.get("domain_count", len(domains))
    st.markdown(f'<div style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.5rem;">{t("room_domain_count").format(count=domain_count)}</div>', unsafe_allow_html=True)

    domain_html = ""
    for d in domains:
        domain_html += f'<span class="case-domain-badge">{d}</span>'
    if domain_html:
        st.markdown(domain_html, unsafe_allow_html=True)

    # ── 4. DECISION FLOW ──
    st.markdown(f'<div class="case-section-title">{t("room_section_flow")}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="case-flow-row">'
        f'<span class="case-flow-step">{t("room_flow_model")}</span>'
        f'<span class="case-flow-arrow">\u2192</span>'
        f'<span class="case-flow-step">{t("room_flow_validation")}</span>'
        f'<span class="case-flow-arrow">\u2192</span>'
        f'<span class="case-flow-step">{t("room_flow_risk")}</span>'
        f'<span class="case-flow-arrow">\u2192</span>'
        f'<span class="case-flow-step">{t("room_flow_decision")}</span>'
        f'<span class="case-flow-arrow">\u2192</span>'
        f'<span class="case-flow-step">{t("room_flow_audit")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 5. DECISION METRICS ──
    st.markdown(f'<div class="case-section-title">{t("room_section_metrics")}</div>', unsafe_allow_html=True)

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

    # ── 6. REQUIRES ATTENTION ──
    st.markdown(f'<div class="case-section-title">{t("room_section_pending")}</div>', unsafe_allow_html=True)

    pending = [d for d in decisions if d.get("lifecycle") in ("under_review", "escalated")]

    if not pending:
        st.markdown(
            f'<div style="font-size:0.85rem;color:var(--text-secondary);padding:0.5rem 0;">'
            f'{t("room_no_pending_attention")}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.5rem;">'
            f'{t("room_pending_count").format(count=len(pending))}'
            f'</div>',
            unsafe_allow_html=True,
        )
        for d in pending[:5]:
            st.markdown(
                f'<div class="case-pending-card">'
                f'<div class="case-pending-title">{d.get("case_id", "?")} \u2014 {d.get("action", "?")}</div>'
                f'<div class="case-pending-meta">{d.get("domain", "?")} | {d.get("lifecycle", "?")} | confidence {d.get("confidence", 0):.0%}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 7. PROVIDER STATUS ──
    st.markdown(f'<div class="case-section-title">{t("room_section_providers")}</div>', unsafe_allow_html=True)

    active_name = "mock"
    active_model = "mock"
    providers_list: list[dict[str, Any]] = []
    try:
        providers_data = client.list_providers_sync()
        active_name = providers_data.get("active_provider", "mock")
        providers_list = providers_data.get("providers", [])
        for p in providers_list:
            if p.get("name") == active_name:
                active_model = p.get("model", "mock")
                break
    except Exception:
        pass

    groq_api_key = os.environ.get("CASE_GROQ_API_KEY", "")
    if groq_api_key:
        groq_online = _check_url("https://api.groq.com/openai/v1/models", timeout=4.0, headers={"Authorization": f"Bearer {groq_api_key}"})
    else:
        groq_online = False
    ollama_online = _check_url("http://127.0.0.1:11434/api/tags", timeout=3.0)

    st.markdown(
        f'<div class="case-status-panel">'
        f'<div class="case-status-row">'
        f'<span class="case-status-label">{t("room_active_provider")}</span>'
        f'<span class="case-status-label" style="font-weight:600;">{active_name} ({active_model})</span>'
        f'</div>'
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Groq</span>'
        f'<span class="case-status-indicator">'
        f'<span class="case-status-dot case-status-dot--{"online" if groq_online else "offline"}"></span>'
        f'<span class="case-status-text--{"online" if groq_online else "offline"}">{"ONLINE" if groq_online else "NOT CONFIGURED" if not groq_api_key else "OFFLINE"}</span>'
        f'</span>'
        f'</div>'
        f'<div class="case-status-row">'
        f'<span class="case-status-label">Ollama</span>'
        f'<span class="case-status-indicator">'
        f'<span class="case-status-dot case-status-dot--{"online" if ollama_online else "offline"}"></span>'
        f'<span class="case-status-text--{"online" if ollama_online else "offline"}">{"ONLINE" if ollama_online else "UNAVAILABLE"}</span>'
        f'</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 8. EVIDENCE TYPE ──
    is_mock = active_name == "mock"
    st.markdown(
        f'<div style="margin-top:0.8rem;">'
        f'<span style="font-size:0.82rem;color:var(--text-secondary);font-weight:600;">{t("room_evidence_type")}: </span>'
        f'<span class="case-evidence-badge case-evidence-badge--{"deterministic" if is_mock else "real"}">'
        f'{t("room_evidence_deterministic") if is_mock else t("room_evidence_real")}'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 9. QUICK ACTIONS ──
    st.markdown(f'<div class="case-section-title">{t("room_quick_actions")}</div>', unsafe_allow_html=True)

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
