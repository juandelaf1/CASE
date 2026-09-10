from typing import Any

import streamlit as st


def render_decision(result: dict[str, Any]) -> None:
    action = result.get("action", "unknown")
    action_colors = {
        "approve": "🟢",
        "reject": "🔴",
        "escalate": "🟡",
    }
    icon = action_colors.get(action, "⚪")

    st.markdown(f"### {icon} Decision: {action.upper()}")
    st.markdown(f"**Reason:** {result.get('reason', 'N/A')}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Urgency", result.get("urgency", "N/A"))
    with col2:
        confidence = result.get("confidence", 0.0)
        st.metric("Confidence", f"{confidence:.2f}")
    with col3:
        st.metric("Processing Time", f"{result.get('processing_time_ms', 0):.0f} ms")


def render_evidence(result: dict[str, Any]) -> None:
    st.markdown("### Evidence")
    evidence_summary = result.get("evidence_summary", "")
    if evidence_summary:
        st.info(f"**Summary:** {evidence_summary}")


def render_audit_events(events: list[dict[str, Any]]) -> None:
    if not events:
        st.info("No audit events recorded.")
        return

    st.markdown("### Audit Trail")
    for event in events:
        event_type = event.get("event_type", "unknown")
        st.markdown(f"- **{event_type}** at {event.get('timestamp', 'N/A')}")


def render_manual_review(detail: dict[str, Any]) -> None:
    st.warning("**REQUIRES MANUAL REVIEW**")
    st.markdown(f"**Error:** {detail.get('error', 'Unknown error')}")
    st.markdown(f"**Category:** {detail.get('category', 'N/A')}")
    st.markdown(f"**Recoverable:** {detail.get('recoverable', False)}")
    st.markdown(f"**Retryable:** {detail.get('retryable', False)}")


def render_error(detail: dict[str, Any]) -> None:
    st.error(f"**Error:** {detail.get('error', 'Unknown error')}")
    st.markdown(f"**Category:** {detail.get('category', 'N/A')}")
    if detail.get("requires_manual_review"):
        render_manual_review(detail)
