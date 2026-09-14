from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient


def get_hitl_client() -> CASEClient:
    if "hitl_client" not in st.session_state:
        st.session_state.hitl_client = CASEClient()
    return st.session_state.hitl_client


def hitl_list() -> list[dict[str, Any]]:
    client = get_hitl_client()

    st.subheader("Pending Human Review")

    try:
        response = client.list_pending_review_sync()
    except Exception as e:
        st.warning(f"Cannot connect to HITL API: {e}")
        return []

    decisions = response.get("decisions", [])
    count = response.get("count", 0)

    if count == 0:
        return decisions

    st.info(f"{count} decision{'s' if count != 1 else ''} awaiting review")

    for dec in decisions:
        _render_decision_card(dec, client)

    return decisions


def _render_decision_card(dec: dict[str, Any], client: CASEClient) -> None:
    decision_id = dec.get("decision_id", "unknown")
    action = dec.get("action", "unknown")
    urgency = dec.get("urgency", "unknown")
    lifecycle = dec.get("lifecycle", "unknown")
    case_id = dec.get("case_id", "N/A")
    domain = dec.get("domain", "N/A")
    reason = dec.get("reason", "N/A")
    confidence = dec.get("confidence", 0)

    action_colors = {"approve": "green", "reject": "red", "escalate": "orange"}
    color = action_colors.get(action, "gray")

    title = f":{color}[{action.upper()}] — {urgency} urgency"

    with st.expander(title):
        st.markdown(f"**Case:** `{case_id}` · **Domain:** {domain}")

        ai_proposal = dec.get("original_ai_proposal")
        if ai_proposal:
            st.markdown("**AI Recommendation:**")
            st.markdown(
                f"- Action: **{ai_proposal.get('action', 'N/A')}** "
                f"(confidence: {ai_proposal.get('confidence', 0):.0%})"
            )
            st.markdown(f"- Urgency: **{ai_proposal.get('urgency', 'N/A')}**")
            st.markdown(f"- Reason: {ai_proposal.get('reason', 'N/A')}")
            evidence_sum = ai_proposal.get("evidence_summary", "")
            if evidence_sum:
                st.markdown(f"- Evidence: {evidence_sum}")

        override = dec.get("human_override")
        if override:
            st.markdown("**Human Decision:**")
            st.markdown(f"- Actor: {override.get('actor', 'N/A')}")
            st.markdown(f"- Justification: {override.get('justification', 'N/A')}")

        lifecycle_display = lifecycle.replace("_", " ").title()
        st.caption(f"Status: {lifecycle_display}")

        if lifecycle in ("ai_proposed", "under_review"):
            _render_action_buttons(decision_id, client)


def _render_action_buttons(decision_id: str, client: CASEClient) -> None:
    action_key = f"hitl_action_{decision_id}"
    if action_key not in st.session_state:
        st.session_state[action_key] = None

    current_action = st.session_state[action_key]

    if current_action is None:
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Approve", key=f"btn_approve_{decision_id}", use_container_width=True):
                st.session_state[action_key] = "approve"
                st.rerun()
        with c2:
            if st.button("Reject", key=f"btn_reject_{decision_id}", use_container_width=True):
                st.session_state[action_key] = "reject"
                st.rerun()
        with c3:
            if st.button("Escalate", key=f"btn_escalate_{decision_id}", use_container_width=True):
                st.session_state[action_key] = "escalate"
                st.rerun()
    else:
        st.markdown("---")
        st.markdown(f"**Action:** {current_action.upper()}")

        justification = st.text_area(
            "Justification (required)",
            key=f"just_input_{decision_id}",
            placeholder="Explain the rationale for this decision...",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm", key=f"confirm_{decision_id}", use_container_width=True):
                if not justification.strip():
                    st.error("Justification is required.")
                    return
                try:
                    if current_action == "approve":
                        client.approve_decision_sync(
                            decision_id, actor="human", justification=justification.strip()
                        )
                    elif current_action == "reject":
                        client.reject_decision_sync(
                            decision_id, actor="human", justification=justification.strip()
                        )
                    elif current_action == "escalate":
                        client.escalate_decision_sync(
                            decision_id, actor="human", justification=justification.strip()
                        )
                    st.session_state[action_key] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Action failed: {e}")

        with col2:
            if st.button("Cancel", key=f"cancel_{decision_id}", use_container_width=True):
                st.session_state[action_key] = None
                st.rerun()
