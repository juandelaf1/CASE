from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_empty_state,
    render_lifecycle_badge,
    render_metric_cards,
    render_risk_badge,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Human Review</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Review and act on cases requiring human oversight</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    with st.spinner("Loading pending decisions..."):
        pending_data = client.list_pending_review_sync(limit=100)

    decisions = pending_data.get("decisions", [])
    count = pending_data.get("count", 0)

    render_metric_cards([
        {"label": "Pending", "value": str(count), "icon": "\u23f1\ufe0f", "color": "#fbbf24"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not decisions:
        render_empty_state("No decisions pending human review")
        return

    for d in decisions:
        decision_id = d.get("decision_id", "N/A")
        case_id = d.get("case_id", "N/A")
        action = d.get("action", "N/A")
        urgency = d.get("urgency", "N/A")
        lifecycle = d.get("lifecycle", "ai_proposed")
        confidence = d.get("confidence", 0)
        reason = d.get("reason", "")

        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                st.markdown(f"**{case_id}**")
                st.caption(f"`{decision_id[:20]}...`")
                st.caption(f"Action: {action.replace('_', ' ').title()}")
            with col2:
                render_risk_badge(urgency)
                st.caption(f"{confidence:.0%} confidence")
                render_lifecycle_badge(lifecycle)
            with col3:
                st.caption(reason[:120] + ("..." if len(reason) > 120 else ""))

            st.divider()

            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                if st.button("\u2705 Approve", key=f"approve_{decision_id}", use_container_width=True):
                    _act(client, decision_id, "approve")
            with col_b:
                if st.button("\u274c Reject", key=f"reject_{decision_id}", use_container_width=True):
                    _act(client, decision_id, "reject")
            with col_c:
                if st.button("\u26a0\ufe0f Escalate", key=f"escalate_{decision_id}", use_container_width=True):
                    _act(client, decision_id, "escalate")
            with col_d:
                if st.button("\u270f\ufe0f Modify", key=f"modify_{decision_id}", use_container_width=True):
                    st.session_state[f"modifying_{decision_id}"] = True

            if st.session_state.get(f"modifying_{decision_id}", False):
                _render_modify_form(client, decision_id, d)

            if st.session_state.get(f"result_{decision_id}"):
                result = st.session_state.pop(f"result_{decision_id}")
                if result.get("error"):
                    st.error(f"Action failed: {result.get('detail', 'Unknown error')}")
                else:
                    st.success(f"Action completed: {result.get('status', 'done')}")
                    st.rerun()


def _act(client: CASEClient, decision_id: str, action: str) -> None:
    with st.spinner(f"Executing {action}..."):
        if action == "approve":
            result = client.approve_decision_sync(decision_id, actor="ui-user")
        elif action == "reject":
            result = client.reject_decision_sync(decision_id, actor="ui-user")
        elif action == "escalate":
            result = client.escalate_decision_sync(decision_id, actor="ui-user")
        else:
            result = {"error": True, "detail": f"Unknown action: {action}"}
    st.session_state[f"result_{decision_id}"] = result


def _render_modify_form(client: CASEClient, decision_id: str, decision: dict) -> None:
    with st.form(f"modify_{decision_id}"):
        st.markdown("**Modify Decision**")
        action = st.selectbox("New Action", ["approve", "reject", "escalate"], index=0)
        reason = st.text_area("New Reason", value=decision.get("reason", ""))
        urgency = st.selectbox("New Urgency", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)
        confidence = st.slider("New Confidence", 0.0, 1.0, decision.get("confidence", 0.5), 0.05)
        evidence_summary = st.text_area("New Evidence Summary", value=decision.get("evidence_summary", ""))
        justification = st.text_area("Justification for Modification")
        notes = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Submit Modification", type="primary")
        if submitted:
            with st.spinner("Submitting modification..."):
                result = client.modify_decision_sync(
                    decision_id=decision_id,
                    action=action,
                    reason=reason,
                    urgency=urgency,
                    confidence=confidence,
                    evidence_summary=evidence_summary,
                    actor="ui-user",
                    notes=notes,
                    justification=justification,
                )
            st.session_state[f"result_{decision_id}"] = result
            st.session_state[f"modifying_{decision_id}"] = False
            st.rerun()
