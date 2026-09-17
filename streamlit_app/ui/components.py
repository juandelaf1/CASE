from __future__ import annotations

from html import escape as _html_escape
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
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics, strict=True):
        with col:
            st.markdown(
                metric_card(m["label"], m["value"], m["icon"], m.get("color", "#1a7a7a")),
                unsafe_allow_html=True,
            )


def render_section_header(title: str, icon: str = "", section_class: str = "case-section-proposal") -> None:
    label = f"{icon} {title}".strip() if icon else title
    st.markdown(
        f'<div class="case-section {section_class}">'
        f'<div class="case-section-title">{label}</div>',
        unsafe_allow_html=True,
    )


def render_section_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_field_row(label: str, value: str) -> None:
    st.markdown(
        f'<div class="case-field-row">'
        f'<span class="case-field-label">{_html_escape(label)}</span>'
        f'<span class="case-field-value">{_html_escape(str(value))}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_confidence(score: float) -> None:
    try:
        pct = f"{float(score):.0%}"
    except (TypeError, ValueError):
        pct = "N/A"
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:8px;">'
        f'<span style="font-size:0.82rem; font-weight:600; color:var(--text-primary);">{pct}</span>'
        f'{confidence_bar_html(score if isinstance(score, (int, float)) else 0.0)}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_risk_badge(level: str) -> None:
    cls = risk_badge_class(level)
    st.markdown(f'<span class="case-badge {cls}">{_html_escape(str(level))}</span>', unsafe_allow_html=True)


def render_lifecycle_badge(lifecycle: str) -> None:
    cls = lifecycle_badge_class(lifecycle)
    label = str(lifecycle).replace("_", " ").upper()
    st.markdown(f'<span class="case-badge {cls}">{_html_escape(label)}</span>', unsafe_allow_html=True)


def render_action_badge(action: str) -> None:
    color = action_color(action)
    label = str(action).replace("_", " ").upper()
    st.markdown(
        f'<span class="case-badge" style="background:{color}12; color:{color};">{_html_escape(label)}</span>',
        unsafe_allow_html=True,
    )


def render_model_proposal(proposal: dict[str, Any]) -> None:
    from streamlit_app.i18n import t
    render_section_header(t("sec_model_proposal"), "", "case-section-proposal")
    render_field_row(t("field_action"), proposal.get("action", t("common_n_a")))
    render_field_row(t("field_urgency"), proposal.get("urgency", t("common_n_a")))
    render_field_row(t("field_reason"), proposal.get("reason", t("common_n_a")))
    render_field_row(t("field_evidence"), proposal.get("evidence_summary", t("common_n_a")))
    conf = proposal.get("confidence")
    if conf is not None:
        render_field_row(t("field_confidence"), "")
        render_confidence(conf)
    render_section_close()


def render_case_decision(decision: dict[str, Any]) -> None:
    from streamlit_app.i18n import t
    render_section_header(t("sec_case_decision"), "", "case-section-decision")

    action = decision.get("action", t("common_n_a"))
    render_action_badge(action)
    st.markdown("<br>", unsafe_allow_html=True)

    render_field_row(t("field_action"), action)
    render_field_row(t("field_reason"), decision.get("reason", t("common_n_a")))
    render_field_row(t("field_urgency"), decision.get("urgency", t("common_n_a")))
    render_field_row(t("field_evidence"), decision.get("evidence_summary", t("common_n_a")))

    conf = decision.get("confidence")
    if conf is not None:
        render_field_row(t("field_confidence"), "")
        render_confidence(conf)

    lifecycle = decision.get("lifecycle", t("common_n_a"))
    cls = lifecycle_badge_class(lifecycle)
    label = str(lifecycle).replace("_", " ").upper()
    render_field_row(t("field_lifecycle"), f'<span class="case-badge {cls}">{_html_escape(label)}</span>')

    ms = decision.get("processing_time_ms")
    if ms is not None:
        render_field_row(t("field_processing_time"), f"{ms:.1f} ms")

    render_section_close()


def render_lifecycle_badge_html(lifecycle: str) -> str:
    cls = lifecycle_badge_class(lifecycle)
    label = str(lifecycle).replace("_", " ").upper()
    return f'<span class="case-badge {cls}">{_html_escape(label)}</span>'


def render_audit_event(event: dict[str, Any]) -> None:
    etype = event.get("event_type", "UNKNOWN")
    color = event_type_color(etype)
    ts = event.get("timestamp", "")
    actor = event.get("actor", "system")
    details = event.get("details", {})

    detail_parts = []
    if "actor" in details:
        detail_parts.append(f"Actor: {_html_escape(str(details['actor']))}")
    if "justification" in details and details["justification"]:
        detail_parts.append(f"Justification: {_html_escape(str(details['justification']))}")
    if "original_action" in details:
        detail_parts.append(f"Was: {_html_escape(str(details['original_action']))}")
    if "new_action" in details:
        detail_parts.append(f"Now: {_html_escape(str(details['new_action']))}")
    detail_str = " \u00b7 ".join(detail_parts)

    st.markdown(
        f'<div class="case-timeline-event">'
        f'<div class="case-timeline-dot" style="background:{color};"></div>'
        f'<div class="case-timeline-body">'
        f'<div class="case-timeline-type">{_html_escape(etype)}</div>'
        f'<div class="case-timeline-meta">{_html_escape(ts)} \u00b7 {_html_escape(actor)}</div>'
        f'{f"<div class=\"case-timeline-details\">{detail_str}</div>" if detail_str else ""}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_down_arrow() -> None:
    st.markdown('<div class="case-flow-connector">\u2193</div>', unsafe_allow_html=True)


def render_empty_state(message: str) -> None:
    st.markdown(f'<div class="case-empty-state">{_html_escape(message)}</div>', unsafe_allow_html=True)


def render_api_health_check(client: Any) -> bool:
    from streamlit_app.i18n import t
    try:
        health = client.health_sync()
        if health.get("status") != "ok":
            st.warning(t("offline_title"))
            return False
        return True
    except Exception:
        st.error(t("offline_title"))
        return False


def render_backend_offline(url: str = "http://localhost:8000") -> None:
    from streamlit_app.i18n import t
    st.markdown(
        f'<div class="case-offline-box">'
        f'<div class="case-offline-title">{t("offline_title")}</div>'
        f'<div class="case-offline-desc">{t("offline_desc", url=url)}</div>'
        f'<div class="case-offline-code">{t("offline_start_api")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_error_state(message: str, detail: str = "") -> None:
    st.error(message)
    if detail:
        st.caption(detail)


def render_pipeline_visual(steps: list[tuple[str, str, str]]) -> None:
    """Render a horizontal pipeline visual.

    Args:
        steps: List of (label, step_number, color) tuples.
    """
    if not steps:
        return
    parts = ['<div class="case-pipeline">']
    for i, (label, step_num, color) in enumerate(steps):
        if i > 0:
            parts.append('<div class="case-pipeline-arrow">\u2192</div>')
        parts.append(
            f'<div class="case-pipeline-step">'
            f'<div class="case-pipeline-icon" style="background:{color}18; color:{color};">{_html_escape(step_num)}</div>'
            f'<div class="case-pipeline-label">{_html_escape(label)}</div>'
            f'</div>'
        )
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)
