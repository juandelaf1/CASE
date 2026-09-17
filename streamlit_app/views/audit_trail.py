from __future__ import annotations

import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_audit_event,
    render_backend_offline,
    render_empty_state,
    render_metric_cards,
)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("audit_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("audit_subtitle")}</div>', unsafe_allow_html=True)

    client = get_client()

    try:
        with st.spinner(t("cases_loading")):
            result = client.list_cases_sync(limit=10, offset=0)
    except Exception:
        render_backend_offline()
        return

    cases = result.get("decisions", [])

    if not cases:
        render_empty_state(t("cases_empty"))
        return

    case_options = {d.get("case_id", ""): d for d in cases if d.get("case_id")}
    case_ids = list(case_options.keys())

    def _format_case(cid: str) -> str:
        d = case_options[cid]
        domain = d.get("domain", t("common_n_a"))
        action = d.get("action", t("common_n_a"))
        return f"{cid} — {domain} — {action.upper()}"

    selected_id = st.selectbox(
        t("audit_case_id"),
        options=case_ids,
        format_func=_format_case,
        key="audit_case_select",
    )

    if not selected_id:
        render_empty_state(t("audit_empty"))
        return

    try:
        with st.spinner(t("audit_loading")):
            audit_result = client.get_audit_events_sync(selected_id)
    except Exception:
        render_backend_offline()
        return

    events = audit_result.get("events", [])
    count = audit_result.get("count", 0)

    render_metric_cards([
        {"label": t("audit_events"), "value": str(count), "icon": "\u2630", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not events:
        render_empty_state(t("audit_no_events", id=selected_id))
        return

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
