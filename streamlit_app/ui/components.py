from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.ui.theme import (
    action_color,
    confidence_bar_html,
    event_type_color,
    lifecycle_badge_class,
    metric_card,
    risk_badge_class,
)


def render_metric_cards(metrics: list[dict[str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics, strict=False):
        with col:
            st.markdown(metric_card(m["label"], m["value"], m["icon"], m.get("color", "#4f8cf7")), unsafe_allow_html=True)


def render_section_header(title: str, icon: str = "", section_class: str = "case-section-proposal") -> None:
    label = f"{icon} {title}".strip() if icon else title
    st.markdown(
        f'<div class="case-section {section_class}">'
        f'<div class="case-section-title">{label}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="case-section {section_class}" style="padding-top:0;">', unsafe_allow_html=True)


def render_section_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_field_row(label: str, value: str) -> None:
    st.markdown(
        f'<div class="case-field-row">'
        f'<span class="case-field-label">{label}</span>'
        f'<span class="case-field-value">{value}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_confidence(score: float) -> None:
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:8px;">'
        f'<span style="font-size:0.85rem; font-weight:600; color:var(--text-primary);">{score:.0%}</span>'
        f"{confidence_bar_html(score)}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_risk_badge(level: str) -> None:
    cls = risk_badge_class(level)
    st.markdown(f'<span class="case-badge {cls}">{level}</span>', unsafe_allow_html=True)


def render_lifecycle_badge(lifecycle: str) -> None:
    cls = lifecycle_badge_class(lifecycle)
    label = lifecycle.replace("_", " ").upper()
    st.markdown(f'<span class="case-badge {cls}">{label}</span>', unsafe_allow_html=True)


def render_action_badge(action: str) -> None:
    color = action_color(action)
    label = action.replace("_", " ").upper()
    st.markdown(
        f'<span class="case-badge" style="background:{color}22; color:{color};">{label}</span>',
        unsafe_allow_html=True,
    )


def render_model_proposal(proposal: dict[str, Any]) -> None:
    render_section_header("MODEL PROPOSAL", "LLM", "case-section-proposal")
    render_field_row("Action", proposal.get("action", "N/A"))
    render_field_row("Urgency", proposal.get("urgency", "N/A"))
    render_field_row("Reason", proposal.get("reason", "N/A"))
    render_field_row("Evidence Summary", proposal.get("evidence_summary", "N/A"))
    conf = proposal.get("confidence")
    if conf is not None:
        st.markdown(
            '<div class="case-field-row">'
            '<span class="case-field-label">Confidence</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        render_confidence(conf)
    render_section_close()


def render_validation_section() -> None:
    render_section_header("VALIDATION", "check", "case-section-validation")
    st.caption("CASE validates schema, risk routing, and policy compliance before producing a decision.")
    render_section_close()


def render_case_decision(decision: dict[str, Any]) -> None:
    render_section_header("CASE DECISION", "shield", "case-section-decision")

    action = decision.get("action", "N/A")
    render_action_badge(action)
    st.markdown("<br>", unsafe_allow_html=True)

    render_field_row("Action", action)
    render_field_row("Reason", decision.get("reason", "N/A"))
    render_field_row("Urgency", decision.get("urgency", "N/A"))
    render_field_row("Evidence Summary", decision.get("evidence_summary", "N/A"))

    conf = decision.get("confidence")
    if conf is not None:
        st.markdown(
            '<div class="case-field-row">'
            '<span class="case-field-label">Confidence</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        render_confidence(conf)

    lifecycle = decision.get("lifecycle", "N/A")
    render_field_row("Lifecycle", "")
    st.markdown(
        f'<div style="margin-left:auto;">{render_lifecycle_badge_html(lifecycle)}</div>',
        unsafe_allow_html=True,
    )

    ms = decision.get("processing_time_ms")
    if ms is not None:
        render_field_row("Processing Time", f"{ms:.1f} ms")

    render_section_close()


def render_lifecycle_badge_html(lifecycle: str) -> str:
    cls = lifecycle_badge_class(lifecycle)
    label = lifecycle.replace("_", " ").upper()
    return f'<span class="case-badge {cls}">{label}</span>'


def render_audit_event(event: dict[str, Any]) -> None:
    etype = event.get("event_type", "UNKNOWN")
    color = event_type_color(etype)
    ts = event.get("timestamp", "")
    actor = event.get("actor", "system")
    details = event.get("details", {})

    detail_parts = []
    if "actor" in details:
        detail_parts.append(f"Actor: {details['actor']}")
    if "justification" in details and details["justification"]:
        detail_parts.append(f"Justification: {details['justification']}")
    if "original_action" in details:
        detail_parts.append(f"Was: {details['original_action']}")
    if "new_action" in details:
        detail_parts.append(f"Now: {details['new_action']}")
    detail_str = " · ".join(detail_parts)

    st.markdown(
        f'<div class="case-timeline-event">'
        f'<div class="case-timeline-dot" style="background:{color};"></div>'
        f'<div class="case-timeline-body">'
        f'<div class="case-timeline-type">{etype}</div>'
        f'<div class="case-timeline-meta">{ts} · {actor}</div>'
        f'{f"<div class=case-timeline-details>{detail_str}</div>" if detail_str else ""}'
        f"</div></div>",
        unsafe_allow_html=True,
    )


def render_down_arrow() -> None:
    st.markdown('<div class="case-arrow-down">\u2193</div>', unsafe_allow_html=True)


def render_empty_state(message: str) -> None:
    st.markdown(f'<div class="case-empty-state">{message}</div>', unsafe_allow_html=True)
