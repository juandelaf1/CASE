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

    for dec in decisions:
        decision_id = dec.get("decision_id", "unknown")
        action = dec.get("action", "unknown")
        urgency = dec.get("urgency", "unknown")
        lifecycle = dec.get("lifecycle", "unknown")

        with st.expander(f"{decision_id} — {action.upper()} ({urgency}) [{lifecycle}]"):
            st.markdown(f"**Case:** {dec.get('case_id', 'N/A')}")
            st.markdown(f"**Domain:** {dec.get('domain', 'N/A')}")
            st.markdown(f"**Reason:** {dec.get('reason', 'N/A')}")
            st.markdown(f"**Confidence:** {dec.get('confidence', 0):.2f}")
            st.markdown(f"**Lifecycle:** `{lifecycle}`")

            if dec.get("original_ai_proposal"):
                orig = dec["original_ai_proposal"]
                st.markdown(f"**AI Proposal:** {orig.get('action')} / {orig.get('urgency')} / {orig.get('confidence')}")

            if dec.get("human_override"):
                override = dec["human_override"]
                st.markdown(f"**Human Override:** {override.get('actor')} — {override.get('justification')}")

            _render_hitl_actions(decision_id, lifecycle)

    return decisions


def _render_hitl_actions(decision_id: str, lifecycle: str) -> None:
    client = get_hitl_client()

    if lifecycle in ("ai_proposed", "under_review"):
        st.markdown("---")

        action_key = f"hitl_action_{decision_id}"
        if action_key not in st.session_state:
            st.session_state[action_key] = None

        current_action = st.session_state[action_key]

        if current_action is None:
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Approve", key=f"btn_approve_{decision_id}"):
                    st.session_state[action_key] = "approve"
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"btn_reject_{decision_id}"):
                    st.session_state[action_key] = "reject"
                    st.rerun()
            with col3:
                if st.button("Escalate", key=f"btn_escalate_{decision_id}"):
                    st.session_state[action_key] = "escalate"
                    st.rerun()
        else:
            st.markdown(f"**Action:** {current_action.upper()}")
            justification = st.text_input(
                "Justification",
                key=f"just_input_{decision_id}",
                placeholder="Explain the rationale for this action...",
            )
            actor = st.text_input("Actor", value="human", key=f"actor_{decision_id}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm", key=f"confirm_{decision_id}"):
                    try:
                        if current_action == "approve":
                            result = client.approve_decision_sync(
                                decision_id, actor=actor, justification=justification
                            )
                        elif current_action == "reject":
                            result = client.reject_decision_sync(
                                decision_id, actor=actor, justification=justification
                            )
                        elif current_action == "escalate":
                            result = client.escalate_decision_sync(
                                decision_id, actor=actor, justification=justification
                            )
                        else:
                            st.error(f"Unknown action: {current_action}")
                            return

                        st.success(f"Action completed: {result.get('decision_id')}")
                        st.session_state[action_key] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

            with col2:
                if st.button("Cancel", key=f"cancel_{decision_id}"):
                    st.session_state[action_key] = None
                    st.rerun()

        with st.expander("Modify decision"):
            _render_modify_form(decision_id, client)

    elif lifecycle == "modified":
        st.success("Decision modified by human reviewer.")
    elif lifecycle == "escalated":
        st.warning("Decision has been escalated.")
    elif lifecycle == "approved":
        st.success("Decision approved.")
    elif lifecycle == "rejected":
        st.error("Decision rejected.")


def _render_modify_form(decision_id: str, client: CASEClient) -> None:
    try:
        decision_data = client.get_decision_sync(decision_id)
    except Exception:
        return

    if decision_data.get("error"):
        return

    action = st.text_input("Action", value=decision_data.get("action", ""), key=f"mod_action_{decision_id}")
    reason = st.text_area("Reason", value=decision_data.get("reason", ""), key=f"mod_reason_{decision_id}")
    urgency = st.selectbox(
        "Urgency",
        ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        index=["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(decision_data.get("urgency", "MEDIUM")),
        key=f"mod_urgency_{decision_id}",
    )
    confidence = st.number_input(
        "Confidence",
        min_value=0.0,
        max_value=1.0,
        value=float(decision_data.get("confidence", 0.0)),
        step=0.05,
        key=f"mod_conf_{decision_id}",
    )
    evidence = st.text_input(
        "Evidence summary",
        value=decision_data.get("evidence_summary", ""),
        key=f"mod_evidence_{decision_id}",
    )
    actor = st.text_input("Actor", value="human", key=f"mod_actor_{decision_id}")
    justification = st.text_input("Justification", value="", key=f"mod_just_{decision_id}")

    if st.button("Submit modification", key=f"mod_submit_{decision_id}"):
        try:
            result = client.modify_decision_sync(
                decision_id=decision_id,
                action=action,
                reason=reason,
                urgency=urgency,
                confidence=confidence,
                evidence_summary=evidence,
                actor=actor,
                justification=justification,
            )
            st.success(f"Modified: {result.get('decision_id')}")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to modify: {e}")
