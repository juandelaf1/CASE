from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_empty_state,
    render_field_row,
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


def _get_system_status(client: CASEClient) -> dict[str, str]:
    status = {"api": "❌", "db": "❌", "provider": "—"}
    try:
        health = client.health_sync()
        if health.get("status") == "ok":
            status["api"] = "✅"
            status["db"] = "✅"
    except Exception:
        pass
    try:
        data = client.list_providers_sync()
        active = data.get("active_provider", "unknown")
        status["provider"] = active.upper()
    except Exception:
        pass
    return status


def render() -> None:
    client = get_client()
    provider = _get_active_provider(client)
    st.session_state["active_provider"] = provider

    _render_hero()
    _render_system_status(client)
    st.markdown("---")
    _render_case_selection(client, provider)
    _render_pending_link(client)


def _render_hero() -> None:
    st.markdown(
        '<div class="case-hero">'
        f'<div class="case-hero-title">CASE</div>'
        f'<div class="case-hero-subtitle">{t("dc_hero_subtitle")}</div>'
        f'<div class="case-hero-desc">{t("dc_hero_desc")}</div>'
        f'<div class="case-hero-tagline">{t("app_principle")}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_system_status(client: CASEClient) -> None:
    status = _get_system_status(client)
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:center; gap:2rem; '
        f'padding:0.6rem 1.2rem; font-size:0.82rem; color:var(--text-muted);">'
        f'<span>{t("dc_api_status")}: {status["api"]}</span>'
        f'<span>{t("dc_db_status")}: {status["db"]}</span>'
        f'<span>{t("dc_provider_status")}: <strong>{status["provider"]}</strong></span>'
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
                f'<div class="case-selector-id">CASE-{info["id"]}</div>'
                f'<div class="case-selector-meta">'
                f'{t(info["short_key"])}<br>'
                f'{info["transport"]} · {info["domain"]}'
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
        with st.expander(f"{t(info['label_key'])} — {t('cases_view_details')}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                render_field_row(t("triage_case_id"), f"CASE-{info['id']}")
                render_field_row(t("triage_domain"), info["domain"])
                render_field_row(t("field_product"), info["product"])
            with c2:
                render_field_row(t("field_transporte"), info.get("transport", "Camión"))
                render_field_row(t("field_origen"), info["origin"])
                render_field_row(t("field_urgency"), info.get("urgency", "MEDIUM"))
                if "destination" in info:
                    render_field_row(t("field_reason"), info["destination"])

        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        with col_btn1:
            if st.button(
                f"▶  {t('dc_analyze')}",
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
        f"➕  {t('dc_custom_case')}",
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
            f'<div style="font-size:1.3rem;">⚖</div>'
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
    risk_level = t("common_n_a")
    automation = data.get("automation_assessment", {})
    if automation:
        risk_level = automation.get("risk_level", t("common_n_a"))

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

    # ── KEY METRICS ROW ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t("dc_result_decision"), action.upper())
    with col2:
        st.metric(t("dc_result_urgency"), urgency)
    with col3:
        st.metric(t("dc_result_confidence"), f"{confidence:.0%}")
    with col4:
        st.metric(t("dc_result_risk"), risk_level)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SUMMARY ──
    summary = data.get("summary", "")
    if summary:
        st.markdown(f"**{t('dc_summary')}**")
        st.markdown(f'<div style="font-size:1.05rem; color:var(--text-primary); padding:0.5rem 0;">{summary}</div>', unsafe_allow_html=True)

    # ── WHY? ──
    reason = data.get("reason", "")
    if reason:
        st.markdown(f"**{t('dc_why')}**")
        st.markdown(f'<div style="font-size:0.95rem; color:var(--text-secondary); padding:0.3rem 0;">{reason}</div>', unsafe_allow_html=True)

    # ── RATIONALE ──
    rationale = data.get("decision_rationale", "")
    if rationale:
        st.markdown(f"**{t('dc_rationale')}**")
        st.markdown(f'<div style="font-size:0.92rem; color:var(--text-secondary); padding:0.3rem 0; line-height:1.6;">{rationale}</div>', unsafe_allow_html=True)

    # ── FACTORS ──
    factors = data.get("decision_factors", [])
    if factors:
        st.markdown(f"**{t('dc_factors')}**")
        for factor in factors:
            st.markdown(f'<div style="font-size:0.92rem; color:var(--text-secondary); padding:0.15rem 0;">• {factor}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── HOW CASE REACHED THIS ──
    _render_react_trace(data)

    # ── VALIDATION ──
    _render_validation(data)

    # ── MODEL INFO ──
    _render_model_info(data, data.get("processing_time_ms", 0))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ACTION BUTTONS ──
    col_compare, col_audit, col_cases = st.columns([2, 1, 1])
    with col_compare:
        if st.button(f"🔬  {t('dc_compare_case')}", key="compare_this_case", use_container_width=True, type="primary"):
            st.session_state["compare_from_dc"] = {
                "report_text": f"Case {data.get('case_id', '')}: {reason}",
                "domain": data.get("domain", "logistics"),
                "urgency": urgency,
            }
            st.session_state["current_page"] = "comparison"
            st.rerun()
    with col_audit:
        if st.button(t("dc_view_audit"), key="result_view_audit", use_container_width=True):
            st.session_state["current_page"] = "audit_trail"
            st.rerun()
    with col_cases:
        if st.button(t("nav_cases"), key="result_view_cases", use_container_width=True):
            st.session_state["current_page"] = "cases"
            st.rerun()

    # ── TECHNICAL JSON ──
    with st.expander(t("dc_technical"), expanded=False):
        st.json(data)


def _render_react_trace(data: dict[str, Any]) -> None:
    st.markdown(f"**{t('dc_how_case_decided')}**")

    react_trace = data.get("react_trace")
    if not react_trace:
        st.caption(t("dc_no_react"))
        return

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("dc_react_explain")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    steps = react_trace.get("steps", [])
    if steps:
        for step in steps:
            step_name = step.get("step", "")
            observation = step.get("observation", "")
            label_key = f"react_{step_name}"
            label = t(label_key) if t(label_key) != label_key else step_name
            st.markdown(
                f'<div style="display:flex; align-items:flex-start; gap:0.75rem; padding:0.5rem 0; '
                f'border-bottom:1px solid var(--border);">'
                f'<div style="width:8px; height:8px; border-radius:50%; background:var(--brand-teal); '
                f'margin-top:6px; flex-shrink:0;"></div>'
                f'<div>'
                f'<div style="font-size:0.92rem; font-weight:600; color:var(--text-primary);">{label}</div>'
                f'<div style="font-size:0.85rem; color:var(--text-muted);">{observation}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    react_summary = react_trace.get("summary", "")
    if react_summary:
        st.markdown(
            f'<div style="font-size:0.88rem; color:var(--text-muted); font-style:italic; padding:0.5rem 0;">'
            f'{react_summary}</div>',
            unsafe_allow_html=True,
        )


def _render_validation(data: dict[str, Any]) -> None:
    st.markdown(f"**{t('dc_validation_title')}**")
    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("dc_validation_explain")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    automation = data.get("automation_assessment", {})
    if automation:
        validation_status = automation.get("validation_status", "")
        evidence_quality = automation.get("evidence_quality", "")
        items = []
        if validation_status:
            items.append(f"✓ {t('dc_validation_pass')}" if validation_status == "valid" else f"⚠ {validation_status}")
        if evidence_quality:
            items.append(f"✓ Evidencia: {evidence_quality}")
        requires_hitl = automation.get("requires_hitl", False)
        if requires_hitl:
            items.append("⚠ Requiere supervisión humana")
        for item in items:
            st.markdown(f'<div style="font-size:0.92rem; color:var(--text-secondary); padding:0.15rem 0;">{item}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="font-size:0.92rem; color:var(--text-secondary); padding:0.3rem 0;">'
            f'{t("dc_validation_detail")}</div>',
            unsafe_allow_html=True,
        )


def _render_model_info(data: dict[str, Any], processing_time: float) -> None:
    provider_info = data.get("provider_info")
    if not provider_info:
        return

    with st.expander(t("dc_model_title"), expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            render_field_row(t("dc_model_provider"), provider_info.get("provider", t("common_n_a")))
            render_field_row(t("dc_model_model"), provider_info.get("model", t("common_n_a")))
            render_field_row(t("dc_model_tokens_in"), str(provider_info.get("prompt_tokens", 0)))
            render_field_row(t("dc_model_tokens_out"), str(provider_info.get("completion_tokens", 0)))
        with c2:
            render_field_row(t("dc_model_tokens_total"), str(provider_info.get("total_tokens", 0)))
            render_field_row(t("dc_model_latency"), f"{provider_info.get('latency_ms', 0):.1f} ms")
            render_field_row(t("field_processing_time"), f"{processing_time:.1f} ms")
            render_field_row(t("dc_model_finish"), provider_info.get("finish_reason", t("common_n_a")))

        cost = data.get("cost")
        if cost:
            render_field_row(t("dc_model_cost"), str(cost))
