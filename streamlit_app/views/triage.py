from __future__ import annotations

import streamlit as st

from streamlit_app.components.decision import (
    render_decision,
    render_error,
    render_evidence,
    render_manual_review,
)
from streamlit_app.components.state import get_client

URGENCY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

DOMAIN_DESCRIPTIONS = {
    "urban_operations": "Urban infrastructure and services",
    "logistics": "Supply chain and transportation",
    "infrastructure": "Critical infrastructure assessment",
}


def render() -> None:
    st.header("Decision Center")

    client = get_client()

    try:
        domains = client.list_domains_sync()
    except Exception:
        st.error("Cannot connect to CASE API. Please ensure the backend is running.")
        return

    if not domains:
        st.warning("No domains available.")
        return

    _render_case_form(client, domains)
    _render_audit_section(client)


def _render_case_form(client, domains: list[str]) -> None:
    with st.form("triage_form"):
        domain = st.selectbox(
            "Domain",
            domains,
            format_func=lambda d: DOMAIN_DESCRIPTIONS.get(d, d),
        )

        report_text = st.text_area(
            "Case Report",
            height=150,
            placeholder="Describe the operational case...",
            help="Required. The system will analyze this report.",
        )

        urgency = st.selectbox(
            "Reported Urgency",
            URGENCY_OPTIONS,
            index=1,
            help="Your assessment of how urgent this case is.",
        )

        evidence_items = _render_evidence_section()

        external_reference = st.text_input(
            "External Reference (optional)",
            placeholder="e.g., TICKET-2026-001",
            help="Your own reference number for this case.",
        )

        submitted = st.form_submit_button("Submit for Triage")

    if submitted:
        if not report_text.strip():
            st.error("Please provide a case report.")
            return

        with st.spinner("Analyzing case..."):
            result = client.triage_sync(
                report_text=report_text.strip(),
                domain=domain,
                urgency=urgency,
                external_reference=external_reference.strip() if external_reference else None,
                evidence=evidence_items if evidence_items else None,
            )

        if result.get("error"):
            detail = result.get("detail", {})
            if isinstance(detail, dict) and detail.get("requires_manual_review"):
                render_manual_review(detail)
            else:
                render_error(detail)
        else:
            data = result.get("data", {})
            render_decision(data)
            render_evidence(data)

            st.session_state["last_case_id"] = data.get("case_id")


def _render_evidence_section() -> list[dict]:
    st.markdown("**Evidence**")
    evidence_items: list[dict] = []

    if "evidence_count" not in st.session_state:
        st.session_state.evidence_count = 0

    col_add, col_clear = st.columns([1, 1])
    with col_add:
        if st.form_submit_button("+ Add evidence", use_container_width=True):
            st.session_state.evidence_count += 1
            st.rerun()
    with col_clear:
        if st.session_state.evidence_count > 0 and st.form_submit_button("Clear all", use_container_width=True):
            st.session_state.evidence_count = 0
            st.rerun()

    for i in range(st.session_state.evidence_count):
        with st.container():
            st.markdown(f"**Evidence {i + 1}**")
            ev_col1, ev_col2 = st.columns(2)
            with ev_col1:
                ev_type = st.selectbox(
                    "Type",
                    ["text", "image", "document", "sensor"],
                    key=f"ev_type_{i}",
                )
                ev_source = st.text_input(
                    "Source",
                    placeholder="e.g., field_inspector",
                    key=f"ev_source_{i}",
                )
            with ev_col2:
                ev_content = st.text_area(
                    "Content",
                    height=68,
                    placeholder="Evidence description...",
                    key=f"ev_content_{i}",
                )
                ev_confidence = st.slider(
                    "Confidence",
                    0.0,
                    1.0,
                    0.9,
                    key=f"ev_conf_{i}",
                )
            if ev_content.strip():
                evidence_items.append({
                    "id": f"ev-{i + 1}",
                    "type": ev_type,
                    "content": ev_content.strip(),
                    "source": ev_source.strip() or "user_input",
                    "confidence": ev_confidence,
                    "extracted_at": "2026-09-14T12:00:00Z",
                })

    return evidence_items


def _render_audit_section(client) -> None:
    case_id = st.session_state.get("last_case_id")
    if not case_id:
        return

    with st.expander("Audit Trail", expanded=False):
        try:
            audit = client.get_audit_events_sync(case_id)
            events = audit.get("events", [])
            if events:
                for event in events:
                    event_type = event.get("event_type", "unknown")
                    timestamp = event.get("timestamp", "N/A")
                    actor = event.get("actor", "system")
                    details = event.get("details", {})

                    st.markdown(f"**{event_type}** — {timestamp} (by {actor})")
                    if details:
                        summary = _summarize_event_details(event_type, details)
                        if summary:
                            st.caption(summary)
            else:
                st.info("No audit events recorded.")
        except Exception:
            st.info("Could not load audit events.")


def _summarize_event_details(event_type: str, details: dict) -> str:
    if event_type == "AI_GENERATED":
        return f"Action: {details.get('action')}, Confidence: {details.get('confidence')}"
    if event_type == "AUTOMATION_ASSESSED":
        risk = details.get("risk_level", "unknown")
        decision = details.get("automation_decision", "unknown")
        factors = details.get("factors", [])
        return f"Risk: {risk}, Decision: {decision}, Factors: {', '.join(factors)}"
    if event_type in ("AUTO_APPROVED", "AUTO_HUMAN_REVIEW", "AUTO_ESCALATED"):
        return details.get("justification", "")
    if event_type == "FINAL_DECISION":
        return f"Action: {details.get('action')}, Lifecycle: {details.get('lifecycle')}"
    if event_type == "HITL_MODIFIED":
        return f"Actor: {details.get('actor')}, Changed: {details.get('original_action')} → {details.get('new_action')}"
    if event_type == "HITL_APPROVED":
        return f"Actor: {details.get('actor')}, Justification: {details.get('justification', '')}"
    return ""
