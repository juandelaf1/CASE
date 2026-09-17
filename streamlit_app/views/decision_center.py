from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_action_badge,
    render_backend_offline,
    render_confidence,
    render_empty_state,
    render_field_row,
    render_pipeline_visual,
    render_section_close,
    render_section_header,
)

DEMO_CASES: dict[str, dict[str, Any]] = {
    "82721": {
        "id": "82721",
        "label_key": "case_a_label",
        "short_key": "case_a_short",
        "description": "Standard pharmaceutical shipment with verified logistics metrics.",
        "domain": "logistics",
        "product": "ARV Adult",
        "origin": "SCMS RDC",
        "transport": "Truck",
        "urgency": "LOW",
        "evidence": [
            {
                "id": "ev-82721-001",
                "type": "text",
                "content": "Standard ARV adult shipment from SCMS RDC via truck transport. No delays reported. Shipment on schedule.",
                "source": "logistics_report",
                "confidence": 0.92,
                "extracted_at": "2026-09-15T10:30:00Z",
            },
            {
                "id": "ev-82721-002",
                "type": "metric",
                "content": "delivery_days: 12, temperature_variance: 0.3, damage_rate: 0.01",
                "source": "logistics_telemetry",
                "confidence": 0.95,
                "extracted_at": "2026-09-15T10:30:00Z",
            },
        ],
    },
    "4": {
        "id": "4",
        "label_key": "case_b_label",
        "short_key": "case_b_short",
        "description": "Air shipment with higher value. Model may interpret differently.",
        "domain": "logistics",
        "product": "Pharmaceutical",
        "origin": "International",
        "transport": "Air",
        "urgency": "MEDIUM",
        "evidence": [
            {
                "id": "ev-4-001",
                "type": "text",
                "content": "High-value pharmaceutical air shipment. Customs clearance required at destination. Estimated transit time 5 days.",
                "source": "logistics_report",
                "confidence": 0.88,
                "extracted_at": "2026-09-15T10:30:00Z",
            },
            {
                "id": "ev-4-002",
                "type": "metric",
                "content": "declared_value: 45000, insurance_coverage: 50000, transit_days: 5",
                "source": "logistics_telemetry",
                "confidence": 0.90,
                "extracted_at": "2026-09-15T10:30:00Z",
            },
        ],
    },
    "108": {
        "id": "108",
        "label_key": "case_c_label",
        "short_key": "case_c_short",
        "description": "Pediatric medication shipment, international route.",
        "domain": "logistics",
        "product": "ARV Pediatric",
        "origin": "BMS Meymac, France",
        "transport": "Air",
        "destination": "Cote d'Ivoire",
        "urgency": "HIGH",
        "evidence": [
            {
                "id": "ev-108-001",
                "type": "text",
                "content": "Pediatric ARV shipment from BMS Meymac France to Cote d'Ivoire via air. Temperature-controlled logistics required.",
                "source": "logistics_report",
                "confidence": 0.90,
                "extracted_at": "2026-09-15T10:30:00Z",
            },
            {
                "id": "ev-108-002",
                "type": "metric",
                "content": "temperature_range: 2-8C, humidity: 45%, weight_kg: 120",
                "source": "logistics_telemetry",
                "confidence": 0.93,
                "extracted_at": "2026-09-15T10:30:00Z",
            },
        ],
    },
}


def _get_active_provider(client: CASEClient) -> dict[str, Any]:
    try:
        data = client.list_providers_sync()
        providers = data.get("providers", [])
        active_name = data.get("active_provider", "unknown")
        for p in providers:
            if p.get("name") == active_name:
                return p
        if providers:
            return providers[0]
    except Exception:
        pass
    return {"name": "unknown", "model": "unknown", "is_mock": True}


def _get_pending_count(client: CASEClient) -> int:
    try:
        data = client.list_pending_review_sync(limit=100)
        return len(data.get("decisions", []))
    except Exception:
        return 0


def render() -> None:
    client = get_client()
    provider = _get_active_provider(client)
    st.session_state["active_provider"] = provider

    _render_hero()
    _render_pipeline_visual()
    st.markdown("---")
    _render_provider_status(provider)
    st.markdown("---")
    _render_case_selection(client, provider)
    _render_pending_link(client)


def _render_hero() -> None:
    st.markdown(
        '<div class="case-hero">'
        f'<div class="case-hero-title">{t("dc_hero_title")}</div>'
        f'<div class="case-hero-subtitle">{t("dc_hero_subtitle")}</div>'
        f'<div class="case-hero-desc">{t("dc_hero_desc")}</div>'
        f'<div class="case-hero-tagline">{t("app_principle")}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_pipeline_visual() -> None:
    steps = [
        (t("pipe_input"), "1", "#1a7a7a"),
        (t("pipe_ai"), "2", "#1a7a7a"),
        (t("pipe_reliability"), "3", "#1a7a7a"),
        (t("pipe_risk"), "4", "#1a7a7a"),
        (t("pipe_decision"), "5", "#1a7a7a"),
        (t("pipe_human"), "6", "#a06800"),
        (t("pipe_audit"), "7", "#555a68"),
    ]
    render_pipeline_visual(steps)


def _render_provider_status(provider: dict[str, Any]) -> None:
    provider_name = provider.get("name", "unknown")
    provider_model = provider.get("model", "unknown")
    is_mock = provider.get("is_mock", True)

    if provider_name == "unknown":
        status_label = t("common_n_a")
        status_color = "#8b90a0"
    elif is_mock:
        status_label = t("dc_provider_demo")
        status_color = "#a06800"
    else:
        status_label = t("dc_provider_live", model=provider_model)
        status_color = "#1a7a4a"

    st.markdown(
        f'<div style="display:flex; align-items:center; gap:1rem; padding:0.8rem 1.2rem; '
        f'background:var(--bg-surface); border:1px solid var(--border); border-radius:10px;">'
        f'<div style="width:10px; height:10px; border-radius:50%; background:{status_color}; flex-shrink:0;"></div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.82rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-muted); font-weight:600;">'
        f'{t("field_provider")}</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:var(--text-primary);">'
        f'{provider_name.upper()}</div>'
        f'</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.82rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-muted); font-weight:600;">'
        f'{t("field_model")}</div>'
        f'<div style="font-size:1.0rem; color:var(--text-secondary);">'
        f'{provider_model}</div>'
        f'</div>'
        f'<div style="flex-shrink:0; padding:0.25rem 0.75rem; border-radius:9999px; '
        f'font-size:0.82rem; font-weight:700; letter-spacing:0.04em; '
        f'background:{status_color}12; color:{status_color};">'
        f'{status_label.upper()}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_case_selection(client: CASEClient, provider: dict[str, Any]) -> None:
    st.markdown(f"#### {t('dc_select_case')}")

    st.markdown(
        f'<div style="font-size:0.82rem; text-transform:uppercase; letter-spacing:0.06em; '
        f'color:var(--text-muted); font-weight:700; margin-bottom:0.8rem;">'
        f'{t("dc_select_case_demo")}</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    selected_case = st.session_state.get("selected_demo_case")

    for i, (case_id, info) in enumerate(DEMO_CASES.items()):
        with cols[i]:
            is_selected = selected_case == case_id
            card_class = "case-selector-card selected" if is_selected else "case-selector-card"
            urgency = info.get("urgency", "MEDIUM")
            urgency_badge_cls = {
                "LOW": "case-badge-low",
                "MEDIUM": "case-badge-medium",
                "HIGH": "case-badge-high",
                "CRITICAL": "case-badge-critical",
            }.get(urgency, "case-badge-medium")

            st.markdown(
                f'<div class="{card_class}">'
                f'<div class="case-selector-label">{t(info["label_key"])}</div>'
                f'<div class="case-selector-id">ID: CASE-{info["id"]}</div>'
                f'<div class="case-selector-meta">'
                f'{t(info["short_key"])}<br>'
                f'{info["transport"]} \u00b7 {info["domain"]}'
                f'</div>'
                f'<div style="margin-top:0.5rem;">'
                f'<span class="case-badge {urgency_badge_cls}">{urgency}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                t("dc_analyze") + f" CASE-{info['id']}",
                key=f"select_{case_id}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state["selected_demo_case"] = case_id
                st.session_state.pop("last_result", None)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if selected_case and selected_case in DEMO_CASES:
        info = DEMO_CASES[selected_case]
        with st.expander(f"{t(info['label_key'])} \u2014 {t('cases_view_details')}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                render_field_row(t("triage_case_id"), f"CASE-{info['id']}")
                render_field_row(t("triage_domain"), info["domain"])
                render_field_row(t("field_model"), info["product"])
            with c2:
                render_field_row(t("field_provider"), info["origin"])
                render_field_row(t("field_urgency"), info.get("urgency", "MEDIUM"))
                if "destination" in info:
                    render_field_row(t("field_reason"), info["destination"])

        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        with col_btn1:
            if st.button(
                f"\u25b6  {t('dc_analyze')}",
                key="run_case",
                type="primary",
                use_container_width=True,
            ):
                _execute_case(client, selected_case)

        with col_btn2:
            if st.button(t("dc_new_case"), key="new_case"):
                st.session_state.pop("selected_demo_case", None)
                st.session_state.pop("last_result", None)
                st.rerun()

        with col_btn3:
            if st.session_state.get("last_result"):
                if st.button(t("dc_view_audit"), key="view_audit"):
                    st.session_state["current_page"] = "audit_trail"
                    st.rerun()

        if st.session_state.get("last_result"):
            _render_result(st.session_state["last_result"])

    elif not selected_case:
        render_empty_state(t("dc_select_prompt"))

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div style="border-top:1px solid var(--border); padding-top:1rem; margin-top:0.5rem;">'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        f"\u2795  {t('dc_custom_case')}",
        key="custom_case_link",
        use_container_width=True,
    ):
        st.session_state["current_page"] = "triage"
        st.rerun()


def _render_pending_link(client: CASEClient) -> None:
    count = _get_pending_count(client)
    if count > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:0.75rem; padding:0.8rem 1.2rem; '
            f'background:var(--color-amber-bg); border:1px solid var(--color-amber-border); border-radius:10px;">'
            f'<div style="font-size:1.3rem;">\u2696</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.95rem; font-weight:700; color:var(--color-amber);">'
            f'{count} {t("review_pending")}</div>'
            f'<div style="font-size:0.88rem; color:var(--text-secondary);">'
            f'{t("review_desc")}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(t("room_open_review"), key="goto_review", type="primary"):
            st.session_state["current_page"] = "human_review"
            st.rerun()


def _execute_case(client: CASEClient, case_id: str) -> None:
    info = DEMO_CASES[case_id]

    progress_bar = st.progress(0, text=t("exec_preparing"))
    progress_bar.progress(10, text=t("exec_loading"))
    progress_bar.progress(30, text=t("exec_provider"))
    progress_bar.progress(50, text=t("exec_validating"))
    progress_bar.progress(70, text=t("exec_risk"))
    progress_bar.progress(85, text=t("exec_building"))

    try:
        result = client.triage_sync(
            report_text=f"Case {case_id}: {info['description']}",
            domain=info["domain"],
            urgency=info.get("urgency", "MEDIUM"),
            evidence=info.get("evidence"),
        )
    except httpx.ConnectError:
        progress_bar.empty()
        render_backend_offline()
        return
    except Exception as exc:
        progress_bar.empty()
        st.error(t("exec_error", error=str(exc)))
        return

    progress_bar.progress(100, text=t("exec_complete"))
    progress_bar.empty()

    if result.get("error"):
        error_type = result.get("error_type", "")
        detail = result.get("detail", {})
        if error_type == "backend_offline":
            render_backend_offline()
        elif error_type == "backend_error":
            st.error(t("err_backend_error", status=result.get("status", "?")))
            st.caption(t("err_backend_error_desc"))
        elif error_type == "validation":
            error_msg = detail.get("error", t("common_error")) if isinstance(detail, dict) else str(detail)
            st.error(t("err_validation", error=error_msg))
        else:
            error_msg = detail.get("error", t("common_error")) if isinstance(detail, dict) else str(detail)
            st.error(t("exec_error", error=error_msg))
        return

    data = result.get("data", {})
    st.session_state["last_result"] = data
    st.rerun()


def _render_result(data: dict[str, Any]) -> None:
    st.markdown("---")
    st.markdown(f"#### {t('dc_analysis_result')}")

    action = data.get("action", "unknown")
    lifecycle = data.get("lifecycle", "ai_proposed")
    confidence = data.get("confidence", 0)
    urgency = data.get("urgency", t("common_n_a"))
    reason = data.get("reason", "")
    processing_time = data.get("processing_time_ms", 0)

    action_class_map = {
        "approve": "case-decision-hero-approve",
        "reject": "case-decision-hero-reject",
        "escalate": "case-decision-hero-escalate",
    }
    hero_class = action_class_map.get(action, "case-decision-hero-review")

    st.markdown(
        f'<div class="case-decision-hero {hero_class}">'
        f'<div class="case-decision-hero-action">{action.upper()}</div>'
        f'<div class="case-decision-hero-lifecycle">{lifecycle.replace("_", " ").upper()}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if reason:
        st.markdown(f"**{t('dc_why')}** {reason}")

    st.markdown("<br>", unsafe_allow_html=True)

    col_risk, col_urgency, col_confidence, col_time = st.columns(4)
    with col_risk:
        automation = data.get("automation_assessment", {})
        risk_level = automation.get("risk_level", t("common_n_a"))
        st.metric(t("field_risk_level"), risk_level)
    with col_urgency:
        st.metric(t("field_urgency"), urgency)
    with col_confidence:
        st.metric(t("field_confidence"), f"{confidence:.0%}")
    with col_time:
        st.metric(t("field_processing_time"), f"{processing_time:.0f} ms")

    st.markdown("<br>", unsafe_allow_html=True)

    _render_ai_proposal(data)
    render_down_arrow()
    _render_case_governance(data)
    render_down_arrow()
    _render_final_decision(data)

    _render_educational_note()
    _render_provider_telemetry(data, processing_time)

    human_override = data.get("human_override")
    if human_override:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(t("dc_human_override"), expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                render_field_row(t("field_actor"), human_override.get("actor", t("common_n_a")))
                render_field_row(t("field_justification"), human_override.get("justification", t("common_n_a")))
            with c2:
                render_field_row(t("field_original_action"), human_override.get("original_action", t("common_n_a")))
                render_field_row(t("field_original_urgency"), human_override.get("original_urgency", t("common_n_a")))

    col_audit, col_cases = st.columns(2)
    with col_audit:
        if st.button(t("dc_view_audit"), key="result_view_audit", use_container_width=True):
            st.session_state["current_page"] = "audit_trail"
            st.rerun()
    with col_cases:
        if st.button(t("nav_cases"), key="result_view_cases", use_container_width=True):
            st.session_state["current_page"] = "cases"
            st.rerun()

    with st.expander(t("dc_technical"), expanded=False):
        st.json(data)


def _render_ai_proposal(data: dict[str, Any]) -> None:
    original_ai = data.get("original_ai_proposal")
    render_section_header(t("sec_ai_proposal"), "", "case-section-proposal")

    if original_ai:
        render_field_row(t("field_action"), original_ai.get("action", t("common_n_a")))
        render_field_row(t("field_urgency"), original_ai.get("urgency", t("common_n_a")))
        render_field_row(t("field_reason"), original_ai.get("reason", t("common_n_a"))[:200])
        conf = original_ai.get("confidence")
        if conf is not None:
            render_field_row(t("field_confidence"), "")
            render_confidence(conf)
    else:
        st.caption(t("dc_no_proposal"))

    render_section_close()


def _render_case_governance(data: dict[str, Any]) -> None:
    render_section_header(t("sec_case_governance"), "", "case-section-governance")

    render_field_row(t("field_reliability"), t("dc_validation_desc"))
    automation = data.get("automation_assessment", {})
    if automation:
        render_field_row(t("field_risk_level"), automation.get("risk_level", t("common_n_a")))
        render_field_row(t("field_automation"), automation.get("automation_decision", t("common_n_a")))
        factors = automation.get("factors", [])
        if factors:
            render_field_row(t("field_factors"), ", ".join(factors))

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("dc_reliability_desc")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_section_close()


def _render_final_decision(data: dict[str, Any]) -> None:
    render_section_header(t("sec_final_decision"), "", "case-section-decision")

    action = data.get("action", t("common_n_a"))
    lifecycle = data.get("lifecycle", t("common_n_a"))

    render_action_badge(action)
    st.markdown("<br>", unsafe_allow_html=True)

    render_field_row(t("field_action"), action)
    render_field_row(t("field_lifecycle"), lifecycle.replace("_", " ").upper())
    render_field_row(t("field_urgency"), data.get("urgency", t("common_n_a")))

    conf = data.get("confidence")
    if conf is not None:
        render_field_row(t("field_confidence"), "")
        render_confidence(conf)

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("dc_final_desc")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_section_close()


def _render_educational_note() -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("dc_proposal_vs_governance")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_provider_telemetry(data: dict[str, Any], processing_time: float) -> None:
    provider_info = data.get("provider_info")
    if not provider_info:
        return
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(t("dc_model_perf"), expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            render_field_row(t("field_provider"), provider_info.get("provider", t("common_n_a")))
            render_field_row(t("field_model"), provider_info.get("model", t("common_n_a")))
            render_field_row(
                t("field_tokens"),
                f"{provider_info.get('total_tokens', 0)} "
                f"(prompt: {provider_info.get('prompt_tokens', 0)}, "
                f"completion: {provider_info.get('completion_tokens', 0)})",
            )
        with c2:
            render_field_row(t("field_latency"), f"{provider_info.get('latency_ms', 0):.1f} ms")
            render_field_row(t("field_finish_reason"), provider_info.get("finish_reason", t("common_n_a")))
            render_field_row(t("field_processing_time"), f"{processing_time:.1f} ms")
        st.markdown(
            f'<div class="case-section-educational">'
            f'<p>{t("dc_latency_desc")}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_down_arrow() -> None:
    st.markdown('<div class="case-flow-connector">\u2193</div>', unsafe_allow_html=True)
