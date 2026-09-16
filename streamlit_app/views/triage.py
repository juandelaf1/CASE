from __future__ import annotations

import json

import httpx
import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_case_decision,
    render_confidence,
    render_down_arrow,
    render_empty_state,
    render_field_row,
    render_metric_cards,
    render_model_proposal,
    render_section_close,
    render_section_header,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("triage_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("triage_subtitle")}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("triage_desc")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

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
    with st.form("triage_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            report_text = st.text_area(
                t("triage_report"),
                height=120,
                placeholder=t("triage_report_ph"),
            )
        with col2:
            domain = st.selectbox(t("triage_domain"), options=domains if domains else ["default"])
            urgency = st.selectbox(t("triage_urgency"), options=["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)

        metadata_raw = st.text_area(t("triage_metadata"), height=68, placeholder='{"key": "value"}')
        submitted = st.form_submit_button(t("triage_submit"), type="primary", use_container_width=True)

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

        try:
            with st.spinner(t("triage_processing")):
                result = client.triage_sync(
                    report_text=report_text,
                    domain=domain,
                    urgency=urgency,
                    metadata=metadata,
                )
        except httpx.ConnectError:
            render_backend_offline()
            return
        except Exception as exc:
            st.error(t("exec_error", error=str(exc)))
            return

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
                category = detail.get("category", t("common_n_a")) if isinstance(detail, dict) else t("common_n_a")
                st.caption(t("triage_category", category=category))
            else:
                error_msg = detail.get("error", t("common_error")) if isinstance(detail, dict) else str(detail)
                st.error(t("triage_error", error=error_msg))
            return

        data = result["data"]
        st.session_state["last_triage"] = data
        _render_triage_result(data)


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


def _render_triage_result(data: dict) -> None:
    case_id = data.get("case_id", t("common_n_a"))
    domain = data.get("domain", t("common_n_a"))
    ms = data.get("processing_time_ms", 0)

    render_metric_cards([
        {"label": t("triage_case_id"), "value": case_id, "icon": "\u2611", "color": "#1a7a7a"},
        {"label": t("triage_domain"), "value": domain, "icon": "\u25ce", "color": "#6a4fa0"},
        {"label": t("field_processing_time"), "value": f"{ms:.1f} ms", "icon": "\u23f1", "color": "#1a7a7a"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    original_ai = data.get("original_ai_proposal")
    if original_ai:
        render_model_proposal(original_ai)
        render_down_arrow()
    else:
        render_section_header(t("sec_model_proposal"), "", "case-section-proposal")
        st.caption(t("dc_no_proposal"))
        render_section_close()
        render_down_arrow()

    render_section_header(t("sec_validation"), "", "case-section-validation")
    confidence = data.get("confidence", 0)
    lifecycle = data.get("lifecycle", "ai_proposed")
    urgency = data.get("urgency", t("common_n_a"))

    render_field_row(t("field_confidence"), f"{confidence:.0%}")
    render_field_row(t("field_urgency"), urgency)
    render_field_row(t("field_lifecycle"), lifecycle.replace("_", " ").upper())
    render_section_close()
    render_down_arrow()

    render_case_decision(data)

    provider_info = data.get("provider_info")
    if provider_info:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(t("triage_provider_telemetry"), expanded=False):
            render_field_row(t("field_provider"), provider_info.get("provider", t("common_n_a")))
            render_field_row(t("field_model"), provider_info.get("model", t("common_n_a")))
            render_field_row(t("field_tokens"), f"{provider_info.get('total_tokens', 0)} (prompt: {provider_info.get('prompt_tokens', 0)}, completion: {provider_info.get('completion_tokens', 0)})")
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
