from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient


def get_hitl_client() -> CASEClient:
    if "hitl_client" not in st.session_state:
        st.session_state.hitl_client = CASEClient()
    return st.session_state.hitl_client


def hitl_list() -> list[dict[str, Any]]:
    """Display pending HITL decisions and return the list of decisions."""
    client = get_hitl_client()

    st.subheader("HITL — Pending Review")

    try:
        response = client.list_pending_review_sync()
    except Exception as e:
        st.warning(f"Cannot connect to HITL API: {e}")
        return []

    decisions = response.get("decisions", [])
    count = response.get("count", 0)

    if count == 0:
        st.info("No pending HITL decisions.")
        return decisions

    st.info(f"Pending decisions: {count}")
    return decisions


def hitl_detail(decision_id: str) -> None:
    """Display a single HITL decision with action buttons."""
    client = get_hitl_client()

    st.subheader(f"Decision: {decision_id}")

    try:
        decision_data = client.get_decision_sync(decision_id)
    except Exception as e:
        st.error(f"Failed to fetch decision: {e}")
        return

    if decision_data.get("error"):
        st.error(f"Decision not found: {decision_id}")
        return

    lifecycle = decision_data.get("lifecycle", "")

    st.markdown(f"**Lifecycle:** `{lifecycle}`")
    if decision_data.get("original_ai_proposal"):
        original = decision_data["original_ai_proposal"]
        st.markdown(f"**Original AI Proposal:** action={original.get('action')}, urgency={original.get('urgency')}, confidence={original.get('confidence')}")
    if decision_data.get("human_override"):
        override = decision_data["human_override"]
        st.markdown(f"**Human Override:** actor={override.get('actor')}, justification={override.get('justification')}, original_action={override.get('original_action')}")

    st.markdown("---")
    st.markdown("### Actions")

    if lifecycle in ("ai_proposed", "under_review"):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Approve", key=f"approve_{decision_id}"):
                justification = st.text_input("Justification", key=f"just_{decision_id}")
                if st.button("Confirm Approve", key=f"conf_approve_{decision_id}"):
                    try:
                        result = client.approve_decision_sync(decision_id, justification=justification)
                        st.success(f"Approved: {result.get('decision_id')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to approve: {e}")

        with col2:
            if st.button("Reject", key=f"reject_{decision_id}"):
                justification = st.text_input("Justification (Reject)", key=f"just_rej_{decision_id}")
                if st.button("Confirm Reject", key=f"conf_reject_{decision_id}"):
                    try:
                        result = client.reject_decision_sync(decision_id, justification=justification)
                        st.success(f"Rejected: {result.get('decision_id')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to reject: {e}")

        with col3:
            if st.button("Escalate", key=f"escalate_{decision_id}"):
                justification = st.text_input("Justification (Escalate)", key=f"just_esc_{decision_id}")
                if st.button("Confirm Escalate", key=f"conf_esc_{decision_id}"):
                    try:
                        result = client.escalate_decision_sync(decision_id, justification=justification)
                        st.success(f"Escalated: {result.get('decision_id')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to escalate: {e}")

        st.markdown("---")
        st.markdown("### Start Review")
        if lifecycle == "ai_proposed":
            justification = st.text_input("Justification for Review", key=f"just_rev_{decision_id}")
            if st.button("Submit Review", key=f"submit_rev_{decision_id}"):
                try:
                    result = client.start_review_sync(decision_id, justification=justification)
                    st.success(f"Under Review: {result.get('decision_id')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start review: {e}")
    elif lifecycle == "modified":
        st.success("Decision has been modified by human reviewer.")
    elif lifecycle == "escalated":
        st.warning("Decision has been escalated.")
    elif lifecycle == "approved":
        st.success("Decision approved.")
    elif lifecycle == "rejected":
        st.error("Decision rejected.")

    st.markdown("---")

    with st.expander("Modify decision"):
        action = st.text_input("Action", value=decision_data.get("action", ""), key=f"act_{decision_id}")
        reason = st.text_area("Reason", value=decision_data.get("reason", ""), key=f"reason_{decision_id}")
        urgency = st.selectbox(
            "Urgency",
            ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            index=["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(decision_data.get("urgency", "MEDIUM")),
            key=f"urgency_{decision_id}",
        )
        confidence = st.number_input(
            "Confidence",
            min_value=0.0,
            max_value=1.0,
            value=float(decision_data.get("confidence", 0.0)),
            step=0.05,
            key=f"conf_{decision_id}",
        )
        evidence = st.text_input(
            "Evidence summary",
            value=decision_data.get("evidence_summary", ""),
            key=f"evidence_{decision_id}",
        )
        actor = st.text_input("Actor", value="human", key=f"actor_{decision_id}")
        notes = st.text_input("Notes", value="", key=f"notes_{decision_id}")
        justification = st.text_input("Justification", value="", key=f"just_{decision_id}_mod")

        if st.button("Submit modification", key=f"mod_{decision_id}"):
            try:
                result = client.modify_decision_sync(
                    decision_id=decision_id,
                    action=action,
                    reason=reason,
                    urgency=urgency,
                    confidence=confidence,
                    evidence_summary=evidence,
                    actor=actor,
                    notes=notes,
                    justification=justification,
                )
                st.success(f"Modified: {result.get('decision_id')}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to modify: {e}")