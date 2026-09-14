from __future__ import annotations

from typing import Any

import streamlit as st


def render_decision(result: dict[str, Any]) -> None:
    action = result.get("action", "unknown")
    action_labels = {
        "approve": ("Approved", "Case approved for action."),
        "reject": ("Rejected", "Case does not meet criteria."),
        "escalate": ("Escalated", "Case requires higher-level review."),
    }
    action_icons = {"approve": "green", "reject": "red", "escalate": "orange"}

    label, description = action_labels.get(action, (action.upper(), ""))
    color = action_icons.get(action, "gray")

    st.markdown(f":{color}[**{label}**] — {description}")

    reason = result.get("reason", "")
    if reason:
        st.markdown(f"**Reason:** {reason}")

    col1, col2, col3 = st.columns(3)
    with col1:
        reported = result.get("reported_urgency")
        effective = result.get("urgency", "N/A")
        if reported and reported != effective:
            st.metric("Urgency", effective, delta=f"from {reported}", delta_color="off")
        else:
            st.metric("Urgency", effective)
    with col2:
        confidence = result.get("confidence", 0.0)
        st.metric("AI Confidence", f"{confidence:.0%}")
    with col3:
        ms = result.get("processing_time_ms", 0)
        st.metric("Processed", f"{ms:.0f} ms")

    case_id = result.get("case_id")
    external_ref = result.get("external_reference")
    if case_id or external_ref:
        with st.container():
            parts = []
            if case_id:
                parts.append(f"Case: `{case_id}`")
            if external_ref:
                parts.append(f"Reference: `{external_ref}`")
            st.caption(" · ".join(parts))


def render_evidence(result: dict[str, Any]) -> None:
    evidence_summary = result.get("evidence_summary", "")
    if evidence_summary:
        st.info(f"**Evidence Analysis:** {evidence_summary}")


def render_manual_review(detail: dict[str, Any]) -> None:
    st.warning("**Manual Review Required**")
    error_msg = detail.get("error", "Unknown error")
    st.markdown(f"**Reason:** {error_msg}")


def render_error(detail: dict[str, Any]) -> None:
    error_msg = detail.get("error", "Unknown error")
    st.error(f"**Could not process case:** {error_msg}")
