from __future__ import annotations

import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
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
            result = client.list_cases_sync(limit=20, offset=0)
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
        {"label": t("audit_events"), "value": str(count), "icon": "☰", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not events:
        render_empty_state(t("audit_no_events", id=selected_id))
        return

    st.markdown(f"#### {t('audit_timeline')}")
    for event in events:
        with st.container(border=True):
            _render_translated_event(event)

    with st.expander(t("dc_technical"), expanded=False):
        st.json(events)


def _render_translated_event(event: dict) -> None:
    from html import escape as _esc

    from streamlit_app.ui.theme import event_type_color

    etype = event.get("event_type", "UNKNOWN")
    color = event_type_color(etype)
    ts = event.get("timestamp", "")
    actor = event.get("actor", "system")
    details = event.get("details", {})

    event_key = f"event_{etype}"
    translated = t(event_key)
    if translated == event_key:
        translated = etype.replace("_", " ").title()

    detail_parts = []
    if "actor" in details and details["actor"] != "system":
        detail_parts.append(f"Actor: {_esc(str(details['actor']))}")
    if "justification" in details and details["justification"]:
        detail_parts.append(f"Justificación: {_esc(str(details['justification']))}")
    if "original_action" in details:
        detail_parts.append(f"Era: {_esc(str(details['original_action']))}")
    if "new_action" in details:
        detail_parts.append(f"Ahora: {_esc(str(details['new_action']))}")
    if "action" in details and "new_action" not in details:
        detail_parts.append(f"Acción: {_esc(str(details['action']))}")
    if "lifecycle" in details:
        detail_parts.append(f"Estado: {_esc(str(details['lifecycle']))}")
    detail_str = " · ".join(detail_parts)
    detail_html = f'<div class="case-timeline-details">{detail_str}</div>' if detail_str else ""

    st.markdown(
        f'<div class="case-timeline-event">'
        f'<div class="case-timeline-dot" style="background:{color};"></div>'
        f'<div class="case-timeline-body">'
        f'<div class="case-timeline-type">{_esc(translated)}</div>'
        f'<div class="case-timeline-meta">{_esc(ts)} · {_esc(actor)}</div>'
        f'{detail_html}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
