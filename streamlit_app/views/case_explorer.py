from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_action_badge,
    render_audit_event,
    render_backend_offline,
    render_empty_state,
    render_field_row,
    render_lifecycle_badge,
    render_metric_cards,
    render_section_close,
    render_section_header,
)

_PAGE_SIZE = 20


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("cases_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("cases_subtitle")}</div>', unsafe_allow_html=True)

    client = get_client()
    _render_cases(client)


def _render_cases(client: CASEClient) -> None:
    if "case_page_offset" not in st.session_state:
        st.session_state.case_page_offset = 0
    if "case_search_query" not in st.session_state:
        st.session_state.case_search_query = ""
    if "case_filter_domain" not in st.session_state:
        st.session_state.case_filter_domain = "all"
    if "case_filter_lifecycle" not in st.session_state:
        st.session_state.case_filter_lifecycle = "all"
    if "selected_case_id" not in st.session_state:
        st.session_state.selected_case_id = None

    search_col, domain_col, lifecycle_col = st.columns([3, 2, 2])
    with search_col:
        st.session_state.case_search_query = st.text_input(
            t("cases_search_id"),
            value=st.session_state.case_search_query,
            placeholder=t("cases_search_ph"),
            key="case_search_input",
        )
    with domain_col:
        pass
    with lifecycle_col:
        pass

    try:
        with st.spinner(t("cases_loading")):
            result = client.list_cases_sync(limit=200, offset=0)
    except Exception:
        render_backend_offline()
        return

    all_decisions = result.get("decisions", [])

    all_domains = sorted({d.get("domain", t("common_n_a")) for d in all_decisions if d.get("domain")})
    all_lifecycles = sorted({d.get("lifecycle", t("common_n_a")) for d in all_decisions if d.get("lifecycle")})

    with domain_col:
        domain_options = ["all"] + all_domains
        domain_labels = {v: (t("cases_all") if v == "all" else v) for v in domain_options}
        selected_domain = st.selectbox(
            t("triage_domain"),
            options=domain_options,
            format_func=lambda x: domain_labels[x],
            index=domain_options.index(st.session_state.case_filter_domain) if st.session_state.case_filter_domain in domain_options else 0,
            key="case_domain_select",
        )
        st.session_state.case_filter_domain = selected_domain

    with lifecycle_col:
        lifecycle_options = ["all"] + all_lifecycles
        lifecycle_labels = {v: (t("cases_all") if v == "all" else v.replace("_", " ").upper()) for v in lifecycle_options}
        selected_lifecycle = st.selectbox(
            t("field_lifecycle"),
            options=lifecycle_options,
            format_func=lambda x: lifecycle_labels[x],
            index=lifecycle_options.index(st.session_state.case_filter_lifecycle) if st.session_state.case_filter_lifecycle in lifecycle_options else 0,
            key="case_lifecycle_select",
        )
        st.session_state.case_filter_lifecycle = selected_lifecycle

    filtered = all_decisions

    if st.session_state.case_search_query:
        q = st.session_state.case_search_query.strip().lower()
        filtered = [d for d in filtered if q in d.get("case_id", "").lower()]

    if selected_domain != "all":
        filtered = [d for d in filtered if d.get("domain") == selected_domain]

    if selected_lifecycle != "all":
        filtered = [d for d in filtered if d.get("lifecycle") == selected_lifecycle]

    total = len(filtered)

    render_metric_cards([
        {"label": t("cases_total"), "value": str(total), "icon": "\u2611", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered:
        render_empty_state(t("cases_empty"))
        return

    offset = st.session_state.case_page_offset
    page = filtered[offset:offset + _PAGE_SIZE]

    for d in page:
        if _render_case_card(d):
            st.session_state.selected_case_id = d.get("case_id")
            st.rerun()

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

    if st.session_state.selected_case_id:
        _render_case_detail(client, st.session_state.selected_case_id)


def _render_case_card(d: dict[str, Any]) -> bool:
    case_id = d.get("case_id", t("common_n_a"))
    domain = d.get("domain", t("common_n_a"))
    action = d.get("action", t("common_n_a"))
    lifecycle = d.get("lifecycle", "ai_proposed")
    confidence = d.get("confidence", 0)
    provider_info = d.get("provider_info", {})
    provider = provider_info.get("provider", t("common_n_a"))
    latency = provider_info.get("latency_ms", 0)
    report_text = d.get("report_text", "")
    label_text = report_text[:60] + "..." if len(report_text) > 60 else report_text
    if not label_text:
        label_text = f"{domain} — {case_id}"

    clicked = False
    with st.container(border=True):
        c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 1, 1, 1, 1])

        with c1:
            st.markdown(f"**{label_text}**")
            st.caption(case_id)

        with c2:
            render_action_badge(action)
            st.caption(f"{domain}")

        with c3:
            render_lifecycle_badge(lifecycle)

        with c4:
            st.caption(f"{confidence:.0%}")

        with c5:
            st.caption(provider)
            if latency:
                st.caption(f"{latency:.0f}ms")

        with c6:
            if st.button(t("cases_view_details"), key=f"detail_{case_id}", use_container_width=True):
                clicked = True

    st.markdown("<br>", unsafe_allow_html=True)
    return clicked


def _render_case_detail(client: CASEClient, case_id: str) -> None:
    try:
        with st.spinner(t("cases_loading_detail")):
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

    domain = decision.get("domain", t("common_n_a"))
    ms = decision.get("processing_time_ms", 0)
    action = decision.get("action", t("common_n_a"))
    lifecycle = decision.get("lifecycle", t("common_n_a"))
    confidence = decision.get("confidence", 0)
    urgency = decision.get("urgency", t("common_n_a"))
    provider_info = decision.get("provider_info", {})
    provider = provider_info.get("provider", t("common_n_a"))

    st.markdown("---")
    st.markdown(f"#### {t('triage_case_id')}: {case_id}")

    render_metric_cards([
        {"label": t("triage_domain"), "value": domain, "icon": "\u25ce", "color": "#6a4fa0"},
        {"label": t("field_action"), "value": action.upper(), "icon": "\u2611", "color": "#1a7a7a"},
        {"label": t("field_confidence"), "value": f"{confidence:.0%}", "icon": "\u25ce", "color": "#a06800"},
        {"label": t("field_processing_time"), "value": f"{ms:.1f} ms", "icon": "\u23f1", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    render_section_header(t("sec_final_decision"), "", "case-section-decision")
    render_action_badge(action)
    st.markdown("<br>", unsafe_allow_html=True)
    render_field_row(t("field_action"), action)
    render_field_row(t("field_urgency"), urgency)
    render_field_row(t("field_lifecycle"), lifecycle.replace("_", " ").upper())
    render_field_row(t("field_confidence"), f"{confidence:.0%}")
    render_field_row(t("field_provider"), provider)
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
