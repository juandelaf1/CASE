from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_action_badge,
    render_backend_offline,
    render_empty_state,
    render_lifecycle_badge,
    render_metric_cards,
    render_risk_badge,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
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

    try:
        pending_data = client.list_pending_review_sync(limit=100)
    except Exception:
        render_backend_offline()
        return

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

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(f"#### {t('room_pending_decisions')}")
        if not pending_decisions:
            render_empty_state(t("room_no_pending"))
        else:
            for d in pending_decisions[:10]:
                case_id = d.get("case_id", t("common_n_a"))
                decision_id = d.get("decision_id", t("common_n_a"))
                action = d.get("action", t("common_n_a"))
                urgency = d.get("urgency", t("common_n_a"))
                confidence = d.get("confidence", 0)
                lifecycle = d.get("lifecycle", "ai_proposed")

                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{case_id}**")
                        st.caption(f"ID: `{decision_id[:16]}...`")
                    with c2:
                        render_risk_badge(urgency)
                        st.caption(f"{confidence:.0%} {t('field_confidence').lower()}")
                    with c3:
                        render_lifecycle_badge(lifecycle)
                        st.caption(action.replace("_", " ").title())

    with col2:
        st.markdown(f"#### {t('room_system_status')}")

        try:
            providers_data = client.list_providers_sync()
            active = providers_data.get("active_provider", "unknown")
            providers = providers_data.get("providers", [])
            st.success(t("room_connected", provider=active.upper()))
            for p in providers:
                name = p.get("name", "unknown")
                model = p.get("model", "unknown")
                is_mock = p.get("is_mock", False)
                status = t("dc_provider_demo") if is_mock else t("dc_provider_live", model=model)
                st.caption(f"\u2022 {name}: {model} ({status})")
        except Exception:
            st.warning(t("room_provider_info"))

        st.markdown("---")
        st.markdown(f"#### {t('room_quick_actions')}")
        if st.button(t("room_open_dc"), use_container_width=True):
            st.session_state["current_page"] = "decision_center"
            st.rerun()
        if st.button(t("room_browse"), use_container_width=True):
            st.session_state["current_page"] = "cases"
            st.rerun()
