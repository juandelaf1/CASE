from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_action_badge,
    render_audit_event,
    render_backend_offline,
    render_empty_state,
    render_field_row,
    render_lifecycle_badge,
    render_metric_cards,
    render_risk_badge,
    render_section_close,
    render_section_header,
)

_PAGE_SIZE = 20


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("cases_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("cases_subtitle")}</div>', unsafe_allow_html=True)

    client = _get_client()

    tab_list, tab_search = st.tabs([t("cases_all"), t("cases_search")])

    with tab_list:
        _render_list(client)

    with tab_search:
        _render_search(client)


def _render_list(client: CASEClient) -> None:
    if "case_page_offset" not in st.session_state:
        st.session_state.case_page_offset = 0

    offset = st.session_state.case_page_offset

    try:
        with st.spinner(t("cases_loading")):
            result = client.list_cases_sync(limit=_PAGE_SIZE, offset=offset)
    except Exception:
        render_backend_offline()
        return

    decisions = result.get("decisions", [])
    total = result.get("total", 0)

    render_metric_cards([
        {"label": t("cases_total"), "value": str(total), "icon": "\u2611", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not decisions:
        render_empty_state(t("cases_empty"))
        return

    for d in decisions:
        _render_case_card(d)

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if offset > 0:
            if st.button(t("cases_prev"), use_container_width=True, key="cases_prev_btn"):
                st.session_state.case_page_offset = max(0, offset - _PAGE_SIZE)
                st.rerun()
    with col_info:
        start = offset + 1
        end = min(offset + _PAGE_SIZE, total)
        st.caption(t("cases_showing", start=str(start), end=str(end), total=str(total)))
    with col_next:
        if offset + _PAGE_SIZE < total:
            if st.button(t("cases_next"), use_container_width=True, key="cases_next_btn"):
                st.session_state.case_page_offset = offset + _PAGE_SIZE
                st.rerun()


def _render_case_card(d: dict[str, Any]) -> None:
    case_id = d.get("case_id", t("common_n_a"))
    domain = d.get("domain", t("common_n_a"))
    action = d.get("action", t("common_n_a"))
    urgency = d.get("urgency", t("common_n_a"))
    lifecycle = d.get("lifecycle", "ai_proposed")
    confidence = d.get("confidence", 0)
    provider_info = d.get("provider_info", {})
    provider = provider_info.get("provider", t("common_n_a"))
    latency = provider_info.get("latency_ms", 0)

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])

        with c1:
            st.markdown(f"**{case_id}**")
            st.caption(f"{t('triage_domain')}: {domain}")

        with c2:
            render_action_badge(action)
            st.caption(f"{confidence:.0%} {t('field_confidence').lower()}")

        with c3:
            render_risk_badge(urgency)

        with c4:
            render_lifecycle_badge(lifecycle)

        with c5:
            st.caption(provider)
            if latency:
                st.caption(f"{latency:.0f}ms")

    st.markdown("<br>", unsafe_allow_html=True)


def _render_search(client: CASEClient) -> None:
    case_id = st.text_input(t("cases_search_id"), placeholder=t("cases_search_ph"))

    if st.button(t("cases_search_btn"), type="primary", use_container_width=True) and case_id:
        try:
            with st.spinner(t("cases_loading_case", id=case_id)):
                result = client.get_case_sync(case_id)
        except Exception:
            render_backend_offline()
            return

        if result.get("error"):
            st.warning(result.get("detail", t("cases_not_found")))
            return

        decision = result.get("decision", {})
        audit_events = result.get("audit_events", [])
        audit_count = result.get("audit_count", 0)

        _render_case_detail(decision, audit_events, audit_count)


def _render_case_detail(decision: dict[str, Any], audit_events: list[dict[str, Any]], audit_count: int) -> None:
    case_id = decision.get("case_id", t("common_n_a"))
    domain = decision.get("domain", t("common_n_a"))
    ms = decision.get("processing_time_ms", 0)

    st.markdown("---")
    st.markdown(f"#### {t('triage_case_id')}: {case_id}")

    render_metric_cards([
        {"label": t("triage_case_id"), "value": case_id, "icon": "\u2611", "color": "#1a7a7a"},
        {"label": t("triage_domain"), "value": domain, "icon": "\u25ce", "color": "#6a4fa0"},
        {"label": t("field_processing_time"), "value": f"{ms:.1f} ms", "icon": "\u23f1", "color": "#1a7a7a"},
        {"label": t("audit_events"), "value": str(audit_count), "icon": "\u2630", "color": "#a06800"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    action = decision.get("action", t("common_n_a"))
    lifecycle = decision.get("lifecycle", t("common_n_a"))
    confidence = decision.get("confidence", 0)
    urgency = decision.get("urgency", t("common_n_a"))

    render_section_header(t("sec_final_decision"), "", "case-section-decision")
    render_action_badge(action)
    st.markdown("<br>", unsafe_allow_html=True)
    render_field_row(t("field_action"), action)
    render_field_row(t("field_urgency"), urgency)
    render_field_row(t("field_lifecycle"), lifecycle.replace("_", " ").upper())
    render_field_row(t("field_confidence"), f"{confidence:.0%}")
    render_field_row(t("field_reason"), decision.get("reason", t("common_n_a"))[:300])
    render_section_close()

    human_override = decision.get("human_override")
    if human_override:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_header(t("sec_human_override"), "", "case-section-governance")
        render_field_row(t("field_actor"), human_override.get("actor", t("common_n_a")))
        render_field_row(t("field_justification"), human_override.get("justification", t("common_n_a")))
        render_field_row(t("field_original_action"), human_override.get("original_action", t("common_n_a")))
        render_field_row(t("field_original_urgency"), human_override.get("original_urgency", t("common_n_a")))
        render_section_close()

    if audit_events:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"#### {t('cases_audit_trail', count=str(audit_count))}")
        for event in audit_events:
            with st.container(border=True):
                render_audit_event(event)

    with st.expander(t("dc_technical"), expanded=False):
        st.json(decision)
