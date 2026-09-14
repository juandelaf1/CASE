from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_empty_state,
    render_lifecycle_badge,
    render_metric_cards,
    render_risk_badge,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Control Room</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Real-time overview of CASE decision operations</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    pending_data = client.list_pending_review_sync(limit=100)
    pending_count = pending_data.get("count", 0)
    pending_decisions = pending_data.get("decisions", [])

    domains = client.list_domains_sync()

    auto_count = 0
    review_count = 0
    escalate_count = 0
    for d in pending_decisions:
        action = d.get("action", "")
        if "approve" in action:
            auto_count += 1
        elif "human" in action:
            review_count += 1
        elif "escalat" in action:
            escalate_count += 1

    render_metric_cards([
        {"label": "Pending Review", "value": str(pending_count), "icon": "\u23f1\ufe0f", "color": "#fbbf24"},
        {"label": "Auto-Approve", "value": str(auto_count), "icon": "\u2705", "color": "#34d399"},
        {"label": "Human Review", "value": str(review_count), "icon": "\U0001f464", "color": "#fb923c"},
        {"label": "Escalated", "value": str(escalate_count), "icon": "\u26a0\ufe0f", "color": "#f87171"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### Pending Decisions")
        if not pending_decisions:
            render_empty_state("No pending decisions")
        else:
            for d in pending_decisions[:10]:
                decision_id = d.get("decision_id", "N/A")
                case_id = d.get("case_id", "N/A")
                action = d.get("action", "N/A")
                urgency = d.get("urgency", "N/A")
                confidence = d.get("confidence", 0)
                lifecycle = d.get("lifecycle", "ai_proposed")

                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{case_id}**")
                        st.caption(f"Decision: `{decision_id[:16]}...`")
                    with c2:
                        render_risk_badge(urgency)
                        st.caption(f"{confidence:.0%} confidence")
                    with c3:
                        render_lifecycle_badge(lifecycle)
                        st.caption(action.replace("_", " ").title())

    with col2:
        st.markdown("#### Available Domains")
        if not domains:
            render_empty_state("No domains registered")
        else:
            for domain in domains:
                st.markdown(f"- `{domain}`")

        st.markdown("#### API Status")
        try:
            health = client.health_sync()
            st.success(f"Connected — v{health.get('version', '?')}")
        except Exception:
            st.error("API unreachable")
