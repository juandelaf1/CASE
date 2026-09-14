import streamlit as st

from streamlit_app.components.decision import (
    render_decision,
    render_error,
    render_evidence,
    render_manual_review,
)
from streamlit_app.components.state import get_client


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

    with st.form("triage_form"):
        col1, col2 = st.columns(2)
        with col1:
            case_id = st.text_input("Case ID", placeholder="e.g., URB-2026-001")
        with col2:
            domain = st.selectbox("Domain", domains)

        urgency = st.selectbox("Urgency", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)
        report_text = st.text_area(
            "Case Report",
            height=150,
            placeholder="Describe the operational case...",
        )

        with st.expander("Add Evidence (optional)"):
            evidence_items = []
            num_evidence = st.number_input(
                "Number of evidence items",
                min_value=0,
                max_value=5,
                value=0,
                key="num_evidence",
            )
            for i in range(num_evidence):
                st.markdown(f"**Evidence {i+1}**")
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
                        "id": f"ev-{i+1}",
                        "type": ev_type,
                        "content": ev_content.strip(),
                        "source": ev_source.strip() or "user_input",
                        "confidence": ev_confidence,
                        "extracted_at": "2026-09-14T12:00:00Z",
                    })

        submitted = st.form_submit_button("Submit for Triage")

    if submitted:
        if not case_id.strip():
            st.error("Case ID is required.")
            return
        if not report_text.strip():
            st.error("Report text is required.")
            return

        with st.spinner("Processing case..."):
            result = client.triage_sync(
                case_id=case_id.strip(),
                report_text=report_text.strip(),
                domain=domain,
                urgency=urgency,
                evidence=evidence_items if evidence_items else None,
            )

        if result.get("error"):
            detail = result.get("detail", {})
            if detail.get("requires_manual_review"):
                render_manual_review(detail)
            else:
                render_error(detail)
        else:
            data = result.get("data", {})
            render_decision(data)
            render_evidence(data)

            if st.button("View Audit Trail"):
                audit = client.get_audit_events_sync(case_id)
                events = audit.get("events", [])
                if events:
                    st.markdown("### Audit Trail")
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
                    st.info("No audit events for this case.")


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
