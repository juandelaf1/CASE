from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_audit_event,
    render_backend_offline,
    render_empty_state,
    render_metric_cards,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("audit_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("audit_subtitle")}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("audit_desc")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    col1, col2 = st.columns([3, 1])
    with col1:
        case_id = st.text_input(t("audit_case_id"), placeholder=t("audit_case_ph"))
    with col2:
        st.write("")
        st.write("")
        load = st.button(t("audit_load"), type="primary", use_container_width=True)

    if case_id and load:
        try:
            with st.spinner(t("audit_loading")):
                result = client.get_audit_events_sync(case_id)
        except Exception:
            render_backend_offline()
            return

        events = result.get("events", [])
        count = result.get("count", 0)

        render_metric_cards([
            {"label": t("audit_events"), "value": str(count), "icon": "\u2630", "color": "#1a7a7a"},
        ])

        st.markdown("<br>", unsafe_allow_html=True)

        if not events:
            render_empty_state(t("audit_no_events", id=case_id))
        else:
            event_type_filter = st.multiselect(
                t("audit_filter"),
                options=sorted({e.get("event_type", "") for e in events}),
                default=[],
            )
            filtered = events
            if event_type_filter:
                filtered = [e for e in events if e.get("event_type") in event_type_filter]

            st.markdown(f"#### {t('audit_timeline')}")
            for event in filtered:
                with st.container(border=True):
                    render_audit_event(event)

            with st.expander(t("dc_technical"), expanded=False):
                st.json(events)
    elif not case_id:
        render_empty_state(t("audit_empty"))
