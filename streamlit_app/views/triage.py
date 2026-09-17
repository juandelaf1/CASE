from __future__ import annotations

import json
from typing import Any

import httpx
import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_case_decision,
    render_confidence,
    render_down_arrow,
    render_field_row,
    render_metric_cards,
    render_pipeline_visual,
    render_section_close,
    render_section_header,
)

_LIFECYCLE_LABELS: dict[str, str] = {
    "ai_proposed": "PROPUESTA IA",
    "under_review": "EN REVISION",
    "approved": "APROBADO",
    "rejected": "RECHAZADO",
    "modified": "MODIFICADO",
    "escalated": "ESCALADO",
}

_PROVIDER_MODELS: dict[str, str] = {
    "Groq": "llama-3.3-70b-versatile",
    "Ollama": "llama3.2",
    "Mock": "mock-deterministic",
}


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("triage_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("triage_subtitle")}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="case-section-educational">'
        f"<p>{t('triage_desc')}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    client = get_client()

    try:
        domains = client.list_domains_sync()
    except Exception:
        render_backend_offline()
        return

    tab_submit, tab_lookup = st.tabs([t("triage_new"), t("triage_lookup")])

    with tab_submit:
        _render_submit(client, domains)

    with tab_lookup:
        _render_lookup(client)


def _render_submit(client: CASEClient, domains: list[str]) -> None:
    st.markdown(f"#### {t('triage_new')}")

    provider_name = st.radio(
        "Proveedor",
        options=["Groq", "Ollama", "Mock"],
        horizontal=True,
        key="triage_provider_radio",
    )
    model_name = _PROVIDER_MODELS.get(provider_name, t("common_n_a"))
    st.markdown(
        f'<div class="case-provider-badge">'
        f'\u25cf Modelo: <strong>{model_name}</strong>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("triage_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            report_text = st.text_area(
                t("triage_report"),
                height=120,
                placeholder=t("triage_report_ph"),
            )
        with col2:
            domain = st.selectbox(
                t("triage_domain"),
                options=domains if domains else ["default"],
            )
            urgency = st.selectbox(
                t("triage_urgency"),
                options=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                index=1,
            )

        metadata_raw = st.text_area(
            t("triage_metadata"), height=68, placeholder='{"key": "value"}'
        )
        submitted = st.form_submit_button(
            t("dc_analyze"), type="primary", use_container_width=True
        )

    if submitted:
        if not report_text.strip():
            st.error(t("triage_report_required"))
            return

        metadata = None
        if metadata_raw.strip():
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                st.error(t("triage_invalid_json"))
                return

        _execute_triage(client, report_text, domain, urgency, metadata)


def _execute_triage(client: CASEClient, report_text: str, domain: str, urgency: str, metadata: dict[str, Any] | None) -> None:
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

    progress = st.progress(0, text=t("exec_preparing"))
    progress.progress(10, text=t("exec_loading"))
    progress.progress(30, text=t("exec_provider"))
    progress.progress(50, text=t("exec_validating"))
    progress.progress(70, text=t("exec_risk"))
    progress.progress(85, text=t("exec_building"))

    try:
        result = client.triage_sync(
            report_text=report_text,
            domain=domain,
            urgency=urgency,
            metadata=metadata,
        )
    except httpx.ConnectError:
        progress.empty()
        render_backend_offline()
        return
    except Exception as exc:
        progress.empty()
        st.error(t("exec_error", error=str(exc)))
        return

    progress.progress(100, text=t("exec_complete"))
    progress.empty()

    if result.get("error"):
        _handle_error(result)
        return

    data = result["data"]
    st.session_state["last_triage"] = data
    _render_triage_result(data)


def _handle_error(result: dict[str, Any]) -> None:
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
        category = detail.get("category", t("common_n_a")) if isinstance(detail, dict) else t("common_n_a")
        st.caption(t("triage_category", category=category))
    else:
        error_msg = detail.get("error", t("common_error")) if isinstance(detail, dict) else str(detail)
        st.error(t("triage_error", error=error_msg))


def _render_lookup(client: CASEClient) -> None:
    case_id = st.text_input(t("triage_case_id"), placeholder=t("triage_case_ph"))
    if st.button(t("triage_lookup_btn"), type="primary") and case_id:
        try:
            with st.spinner(t("triage_fetching")):
                result = client.get_case_sync(case_id)
        except Exception:
            render_backend_offline()
            return

        if result.get("error"):
            st.warning(t("triage_not_found", id=case_id))
            return

        decision = result.get("decision", {})
        st.session_state["last_triage"] = decision
        _render_triage_result(decision)


def _render_triage_result(data: dict[str, Any]) -> None:
    case_id = data.get("case_id", t("common_n_a"))
    domain = data.get("domain", t("common_n_a"))
    ms = data.get("processing_time_ms", 0)

    render_metric_cards([
        {"label": t("triage_case_id"), "value": case_id, "icon": "\u2611", "color": "#1a7a7a"},
        {"label": t("triage_domain"), "value": domain, "icon": "\u25ce", "color": "#6a4fa0"},
        {"label": t("field_processing_time"), "value": f"{ms:.1f} ms", "icon": "\u23f1", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    _render_llm_proposal(data)
    render_down_arrow()
    _render_case_governance(data)
    render_down_arrow()
    _render_final_decision_section(data)

    provider_info = data.get("provider_info")
    if provider_info:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(t("triage_provider_telemetry"), expanded=False):
            render_field_row(t("field_provider"), provider_info.get("provider", t("common_n_a")))
            render_field_row(t("field_model"), provider_info.get("model", t("common_n_a")))
            render_field_row(
                t("field_tokens"),
                f"{provider_info.get('total_tokens', 0)} "
                f"(prompt: {provider_info.get('prompt_tokens', 0)}, "
                f"completion: {provider_info.get('completion_tokens', 0)})",
            )
            render_field_row(t("field_latency"), f"{provider_info.get('latency_ms', 0):.1f} ms")
            render_field_row(t("field_finish_reason"), provider_info.get("finish_reason", t("common_n_a")))

    human_override = data.get("human_override")
    if human_override:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(t("dc_human_override"), expanded=True):
            render_field_row(t("field_actor"), human_override.get("actor", t("common_n_a")))
            render_field_row(t("field_justification"), human_override.get("justification", t("common_n_a")))
            render_field_row(t("field_original_action"), human_override.get("original_action", t("common_n_a")))
            render_field_row(t("field_original_urgency"), human_override.get("original_urgency", t("common_n_a")))

    with st.expander(t("triage_raw"), expanded=False):
        st.json(data)


def _render_llm_proposal(data: dict[str, Any]) -> None:
    original_ai = data.get("original_ai_proposal")

    if original_ai:
        render_section_header(t("sec_model_proposal"), "", "case-section-proposal")
        render_field_row(t("field_action"), original_ai.get("action", t("common_n_a")))
        render_field_row(t("field_urgency"), original_ai.get("urgency", t("common_n_a")))
        reason = original_ai.get("reason", t("common_n_a"))
        if len(reason) > 250:
            reason = reason[:250] + "..."
        render_field_row(t("field_reason"), reason)
        evidence = original_ai.get("evidence_summary", t("common_n_a"))
        if evidence and len(evidence) > 250:
            evidence = evidence[:250] + "..."
        render_field_row(t("field_evidence"), evidence)
        conf = original_ai.get("confidence")
        if conf is not None:
            render_field_row(t("field_confidence"), "")
            render_confidence(conf)
        render_section_close()
    else:
        render_section_header(t("sec_model_proposal"), "", "case-section-proposal")
        st.caption(t("dc_no_proposal"))
        render_section_close()

    st.markdown(
        f'<div class="case-section-educational">'
        f"<p>{t('app_principle')}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_case_governance(data: dict[str, Any]) -> None:
    render_section_header(t("sec_case_governance"), "", "case-section-governance")

    lifecycle = data.get("lifecycle", "ai_proposed")
    lifecycle_label = _LIFECYCLE_LABELS.get(lifecycle, lifecycle.replace("_", " ").upper())
    render_field_row(t("field_lifecycle"), lifecycle_label)

    automation = data.get("automation_assessment", {})
    risk_level = automation.get("risk_level", t("common_n_a"))
    render_field_row(t("field_risk_level"), risk_level)

    render_field_row(t("field_reliability"), t("dc_validation_desc"))

    reliability_score = data.get("reliability_score")
    if reliability_score is not None:
        render_field_row(t("field_confidence"), "")
        render_confidence(reliability_score)

    render_field_row(t("field_processing_time"), f"{data.get('processing_time_ms', 0):.1f} ms")

    factors = automation.get("factors", [])
    if factors:
        render_field_row(t("field_factors"), ", ".join(factors))

    render_section_close()


def _render_final_decision_section(data: dict[str, Any]) -> None:
    render_case_decision(data)

    action = data.get("action", t("common_n_a"))
    lifecycle = data.get("lifecycle", "ai_proposed")
    is_approved = action in ("approve", "auto_approve") and lifecycle == "approved"

    if is_approved:
        st.markdown(
            f'<div class="case-section-educational">'
            f"<p>{t('dc_final_desc')}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="case-section-educational">'
            f"<p>{t('dc_reliability_desc')}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
