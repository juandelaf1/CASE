from __future__ import annotations

import json

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_case_decision,
    render_down_arrow,
    render_field_row,
    render_metric_cards,
    render_model_proposal,
    render_section_close,
    render_section_header,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Triage</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Submit a case and inspect the full decision pipeline</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()
    domains = client.list_domains_sync()

    tab_submit, tab_lookup = st.tabs(["New Case", "Lookup Case"])

    with tab_submit:
        _render_submit(client, domains)

    with tab_lookup:
        _render_lookup(client)


def _render_submit(client: CASEClient, domains: list[str]) -> None:
    with st.form("triage_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            report_text = st.text_area(
                "Report Text",
                height=120,
                placeholder="Describe the case to triage...",
            )
        with col2:
            domain = st.selectbox("Domain", options=domains if domains else ["default"])
            urgency = st.selectbox("Urgency", options=["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)

        metadata_raw = st.text_area("Metadata (JSON, optional)", height=68, placeholder='{"key": "value"}')
        submitted = st.form_submit_button("Submit Case", type="primary", use_container_width=True)

    if submitted:
        if not report_text.strip():
            st.error("Report text is required")
            return

        metadata = None
        if metadata_raw.strip():
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                st.error("Invalid JSON in metadata")
                return

        with st.spinner("Processing through CASE pipeline..."):
            result = client.triage_sync(
                report_text=report_text,
                domain=domain,
                urgency=urgency,
                metadata=metadata,
            )

        if result.get("error"):
            detail = result.get("detail", {})
            st.error(f"Error: {detail.get('error', 'Unknown error')}")
            st.caption(f"Category: {detail.get('category', 'N/A')}")
            return

        data = result["data"]
        st.session_state["last_triage"] = data
        _render_triage_result(data)


def _render_lookup(client: CASEClient) -> None:
    case_id = st.text_input("Case ID", placeholder="CASE-XXXXXXXX")
    if st.button("Lookup", type="primary") and case_id:
        with st.spinner("Fetching case..."):
            pending = client.list_pending_review_sync(limit=200)
            for d in pending.get("decisions", []):
                if d.get("case_id") == case_id:
                    st.session_state["last_triage"] = d
                    _render_triage_result(d)
                    return
        st.warning(f"No decision found for {case_id}")


def _render_triage_result(data: dict) -> None:
    case_id = data.get("case_id", "N/A")
    domain = data.get("domain", "N/A")
    ms = data.get("processing_time_ms", 0)

    render_metric_cards([
        {"label": "Case ID", "value": case_id, "icon": "\U0001f4cb", "color": "#4f8cf7"},
        {"label": "Domain", "value": domain, "icon": "\U0001f3af", "color": "#a78bfa"},
        {"label": "Processing", "value": f"{ms:.1f} ms", "icon": "\u23f1\ufe0f", "color": "#22d3ee"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    original_ai = data.get("original_ai_proposal")
    if original_ai:
        render_model_proposal(original_ai)
        render_down_arrow()
    else:
        render_section_header("MODEL PROPOSAL", "LLM", "case-section-proposal")
        st.caption("No separate AI proposal recorded — decision was produced directly.")
        render_section_close()
        render_down_arrow()

    render_section_header("VALIDATION", "\u2713", "case-section-validation")
    confidence = data.get("confidence", 0)
    lifecycle = data.get("lifecycle", "ai_proposed")
    urgency = data.get("urgency", "N/A")

    render_field_row("Confidence", f"{confidence:.0%}")
    render_field_row("Urgency", urgency)
    render_field_row("Lifecycle", lifecycle.replace("_", " ").upper())
    render_section_close()
    render_down_arrow()

    render_case_decision(data)

    human_override = data.get("human_override")
    if human_override:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Human Override")
        with st.container(border=True):
            render_field_row("Actor", human_override.get("actor", "N/A"))
            render_field_row("Justification", human_override.get("justification", "N/A"))
            render_field_row("Original Action", human_override.get("original_action", "N/A"))
            render_field_row("Original Urgency", human_override.get("original_urgency", "N/A"))

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Raw Response"):
        st.json(data)
