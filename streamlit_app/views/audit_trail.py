from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_audit_event,
    render_empty_state,
    render_metric_cards,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Audit Trail</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Complete event log for case decisions and human actions</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    col1, col2 = st.columns([3, 1])
    with col1:
        case_id = st.text_input("Case ID", placeholder="Enter CASE-XXXXXXXX to view audit events")
    with col2:
        st.write("")
        st.write("")
        load = st.button("Load Events", type="primary", use_container_width=True)

    if case_id and load:
        with st.spinner("Loading audit events..."):
            result = client.get_audit_events_sync(case_id)

        events = result.get("events", [])
        count = result.get("count", 0)

        render_metric_cards([
            {"label": "Events", "value": str(count), "icon": "\U0001f4cb", "color": "#4f8cf7"},
        ])

        st.markdown("<br>", unsafe_allow_html=True)

        if not events:
            render_empty_state(f"No audit events for {case_id}")
        else:
            event_type_filter = st.multiselect(
                "Filter by event type",
                options=sorted({e.get("event_type", "") for e in events}),
                default=[],
            )
            filtered = events
            if event_type_filter:
                filtered = [e for e in events if e.get("event_type") in event_type_filter]

            for event in filtered:
                with st.container(border=True):
                    render_audit_event(event)

            with st.expander("Raw Events"):
                st.json(events)
    elif not case_id:
        render_empty_state("Enter a Case ID to view its audit trail")
