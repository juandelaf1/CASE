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
        case_id = st.text_input("Case ID", placeholder="e.g., URB-2026-001")
        domain = st.selectbox("Domain", domains)
        urgency = st.selectbox("Urgency", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)
        report_text = st.text_area(
            "Case Report",
            height=150,
            placeholder="Describe the operational case...",
        )
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
                    for event in events:
                        st.markdown(
                            f"- **{event.get('event_type', 'unknown')}** — "
                            f"{event.get('timestamp', 'N/A')}"
                        )
                else:
                    st.info("No audit events for this case.")
