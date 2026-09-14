from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_action_badge,
    render_audit_event,
    render_case_decision,
    render_down_arrow,
    render_empty_state,
    render_field_row,
    render_lifecycle_badge,
    render_metric_cards,
    render_model_proposal,
    render_risk_badge,
    render_section_close,
    render_section_header,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Case Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Inspect case lifecycle, decisions, and audit trail</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    tab_list, tab_search = st.tabs(["All Cases", "Search by ID"])

    with tab_list:
        _render_list(client)

    with tab_search:
        _render_search(client)


def _render_list(client: CASEClient) -> None:
    if "case_page_offset" not in st.session_state:
        st.session_state.case_page_offset = 0

    offset = st.session_state.case_page_offset
    page_size = 20

    with st.spinner("Loading cases..."):
        result = client.list_cases_sync(limit=page_size, offset=offset)

    decisions = result.get("decisions", [])
    total = result.get("total", 0)

    render_metric_cards([
        {"label": "Total Cases", "value": str(total), "icon": "\U0001f4cb", "color": "#4f8cf7"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not decisions:
        render_empty_state("No cases in the system yet. Submit a case in the Triage page.")
        return

    for d in decisions:
        _render_case_row(d)

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if offset > 0:
            if st.button("\u2190 Previous", use_container_width=True):
                st.session_state.case_page_offset = max(0, offset - page_size)
                st.rerun()
    with col_info:
        start = offset + 1
        end = min(offset + page_size, total)
        st.caption(f"Showing {start}-{end} of {total}")
    with col_next:
        if offset + page_size < total:
            if st.button("Next \u2192", use_container_width=True):
                st.session_state.case_page_offset = offset + page_size
                st.rerun()


def _render_search(client: CASEClient) -> None:
    case_id = st.text_input("Case ID", placeholder="CASE-XXXXXXXX")
    if st.button("Search", type="primary", use_container_width=True) and case_id:
        with st.spinner(f"Loading case {case_id}..."):
            result = client.get_case_sync(case_id)

        if result.get("error"):
            st.warning(result.get("detail", "Case not found"))
            return

        decision = result.get("decision", {})
        audit_events = result.get("audit_events", [])
        audit_count = result.get("audit_count", 0)

        _render_case_detail(decision, audit_events, audit_count)


def _render_case_row(d: dict) -> None:
    case_id = d.get("case_id", "N/A")
    decision_id = d.get("decision_id", "N/A")
    domain = d.get("domain", "N/A")
    action = d.get("action", "N/A")
    urgency = d.get("urgency", "N/A")
    lifecycle = d.get("lifecycle", "ai_proposed")
    confidence = d.get("confidence", 0)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        with c1:
            st.markdown(f"**{case_id}**")
            st.caption(f"Domain: `{domain}`")
        with c2:
            render_action_badge(action)
            st.caption(f"{confidence:.0%} confidence")
        with c3:
            render_risk_badge(urgency)
        with c4:
            render_lifecycle_badge(lifecycle)

        if st.button("View Details", key=f"detail_{decision_id}", use_container_width=True):
            st.session_state["selected_case_id"] = case_id
            st.rerun()

    if st.session_state.get("selected_case_id") == case_id:
        with st.spinner("Loading case detail..."):
            result = _get_client().get_case_sync(case_id)
        if not result.get("error"):
            decision = result.get("decision", {})
            audit_events = result.get("audit_events", [])
            audit_count = result.get("audit_count", 0)
            _render_case_detail(decision, audit_events, audit_count)
        st.session_state.pop("selected_case_id", None)


def _render_case_detail(decision: dict, audit_events: list[dict], audit_count: int) -> None:
    case_id = decision.get("case_id", "N/A")
    domain = decision.get("domain", "N/A")
    ms = decision.get("processing_time_ms", 0)

    st.markdown("---")
    st.markdown(f"#### Case {case_id}")

    render_metric_cards([
        {"label": "Case ID", "value": case_id, "icon": "\U0001f4cb", "color": "#4f8cf7"},
        {"label": "Domain", "value": domain, "icon": "\U0001f3af", "color": "#a78bfa"},
        {"label": "Processing", "value": f"{ms:.1f} ms", "icon": "\u23f1\ufe0f", "color": "#22d3ee"},
        {"label": "Audit Events", "value": str(audit_count), "icon": "\U0001f4dd", "color": "#fb923c"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    original_ai = decision.get("original_ai_proposal")
    if original_ai:
        render_model_proposal(original_ai)
        render_down_arrow()
    else:
        render_section_header("MODEL PROPOSAL", "LLM", "case-section-proposal")
        st.caption("No separate AI proposal recorded.")
        render_section_close()
        render_down_arrow()

    render_section_header("VALIDATION", "\u2713", "case-section-validation")
    confidence = decision.get("confidence", 0)
    lifecycle = decision.get("lifecycle", "ai_proposed")
    urgency = decision.get("urgency", "N/A")
    render_field_row("Confidence", f"{confidence:.0%}")
    render_field_row("Urgency", urgency)
    render_field_row("Lifecycle", lifecycle.replace("_", " ").upper())
    render_section_close()
    render_down_arrow()

    render_case_decision(decision)

    human_override = decision.get("human_override")
    if human_override:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Human Override")
        with st.container(border=True):
            render_field_row("Actor", human_override.get("actor", "N/A"))
            render_field_row("Justification", human_override.get("justification", "N/A"))
            render_field_row("Original Action", human_override.get("original_action", "N/A"))
            render_field_row("Original Urgency", human_override.get("original_urgency", "N/A"))

    if audit_events:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"#### Audit Trail ({audit_count} events)")
        for event in audit_events:
            with st.container(border=True):
                render_audit_event(event)

    with st.expander("Raw Decision JSON"):
        st.json(decision)
