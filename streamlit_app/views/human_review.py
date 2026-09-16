from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_action_badge,
    render_backend_offline,
    render_empty_state,
    render_field_row,
    render_lifecycle_badge,
    render_metric_cards,
    render_risk_badge,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("review_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("review_subtitle")}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("review_desc")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    try:
        with st.spinner(t("review_loading")):
            pending_data = client.list_pending_review_sync(limit=100)
    except Exception:
        render_backend_offline()
        return

    decisions = pending_data.get("decisions", [])
    count = pending_data.get("count", 0)

    render_metric_cards([
        {"label": t("review_pending"), "value": str(count), "icon": "\u23f3", "color": "#a06800"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    if not decisions:
        render_empty_state(t("review_empty"))
        return

    for d in decisions:
        _render_decision_card(client, d)


def _render_decision_card(client: CASEClient, decision: dict) -> None:
    decision_id = decision.get("decision_id", t("common_n_a"))
    case_id = decision.get("case_id", t("common_n_a"))
    action = decision.get("action", t("common_n_a"))
    urgency = decision.get("urgency", t("common_n_a"))
    lifecycle = decision.get("lifecycle", "ai_proposed")
    confidence = decision.get("confidence", 0)
    reason = decision.get("reason", "")

    with st.container(border=True):
        st.markdown(f"**{t('triage_case_id')}: {case_id}**")

        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            render_action_badge(action)
            st.caption(f"{t('field_confidence')}: {confidence:.0%}")
        with c2:
            render_risk_badge(urgency)
            render_lifecycle_badge(lifecycle)
        with c3:
            if reason:
                st.caption(reason[:150] + ("..." if len(reason) > 150 else ""))

        st.divider()

        st.markdown(f"**{t('review_actions')}:**")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            if st.button(t("review_approve"), key=f"approve_{decision_id}", use_container_width=True):
                _act(client, decision_id, "approve")
        with col_b:
            if st.button(t("review_reject"), key=f"reject_{decision_id}", use_container_width=True):
                _act(client, decision_id, "reject")
        with col_c:
            if st.button(t("review_escalate"), key=f"escalate_{decision_id}", use_container_width=True):
                _act(client, decision_id, "escalate")
        with col_d:
            if st.button(t("review_modify"), key=f"modify_{decision_id}", use_container_width=True):
                st.session_state[f"modifying_{decision_id}"] = True

        if st.session_state.get(f"modifying_{decision_id}", False):
            _render_modify_form(client, decision_id, decision)

        if st.session_state.get(f"result_{decision_id}"):
            result = st.session_state.pop(f"result_{decision_id}", None)
            if result is None:
                return
            if result.get("error"):
                error_msg = result.get("detail", t("common_error"))
                st.error(t("review_failed", error=str(error_msg)))
            else:
                st.success(t("review_completed", status=result.get("status", "done")))
                st.rerun()


def _act(client: CASEClient, decision_id: str, action: str) -> None:
    try:
        with st.spinner(t("review_executing", action=action)):
            if action == "approve":
                result = client.approve_decision_sync(decision_id, actor="ui-user")
            elif action == "reject":
                result = client.reject_decision_sync(decision_id, actor="ui-user")
            elif action == "escalate":
                result = client.escalate_decision_sync(decision_id, actor="ui-user")
            else:
                result = {"error": True, "detail": f"Unknown action: {action}"}
    except Exception as exc:
        result = {"error": True, "detail": str(exc)}
    st.session_state[f"result_{decision_id}"] = result


def _render_modify_form(client: CASEClient, decision_id: str, decision: dict) -> None:
    st.markdown("---")
    st.markdown(f"**{t('review_modify_title')}**")

    with st.form(f"modify_{decision_id}"):
        action = st.selectbox(t("review_new_action"), ["approve", "reject", "escalate"], index=0)
        urgency = st.selectbox(t("review_new_urgency"), ["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)
        confidence = st.slider(t("review_new_confidence"), 0.0, 1.0, decision.get("confidence", 0.5), 0.05)
        reason = st.text_area(t("review_new_reason"), value=decision.get("reason", ""))
        evidence_summary = st.text_area(t("review_new_evidence"), value=decision.get("evidence_summary", ""))
        justification = st.text_area(t("review_justification"))
        notes = st.text_area(t("review_notes"))

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button(t("review_submit"), type="primary", use_container_width=True)
        with c2:
            cancelled = st.form_submit_button(t("review_cancel"), use_container_width=True)

        if cancelled:
            st.session_state[f"modifying_{decision_id}"] = False
            st.rerun()

        if submitted:
            if not justification.strip():
                st.error(t("review_justification_required"))
                return
            try:
                with st.spinner(t("review_submitting")):
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
            except Exception as exc:
                result = {"error": True, "detail": str(exc)}
            st.session_state[f"result_{decision_id}"] = result
            st.session_state[f"modifying_{decision_id}"] = False
            st.rerun()
