from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_api_health_check,
    render_empty_state,
    render_field_row,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Provider Lab</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Provider configuration and real telemetry from triage runs</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    if not render_api_health_check(client):
        return

    with st.spinner("Loading provider info..."):
        providers_data = client.list_providers_sync()

    providers = providers_data.get("providers", [])
    active = providers_data.get("active_provider", "unknown")

    st.markdown("#### Configured Provider")
    for p in providers:
        name = p.get("name", "unknown")
        model = p.get("model", "unknown")
        is_mock = p.get("is_mock", False)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"**{name}**")
                st.caption(f"Model: `{model}`")
            with c2:
                if is_mock:
                    st.warning("Deterministic test/demo provider — not a real LLM")
                else:
                    st.success("Active LLM provider")
            with c3:
                if name == active:
                    st.markdown("**ACTIVE**")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Provider Neutrality")
    st.caption(
        "CASE is provider-agnostic. The same pipeline, validation, risk assessment, "
        "and HITL logic execute regardless of which provider is configured. "
        "Provider telemetry is recorded from actual LLM responses — never fabricated."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Recent Telemetry")
    st.caption("Provider info from the last triage run (if available).")

    try:
        cases_result = client.list_cases_sync(limit=1, offset=0)
        decisions = cases_result.get("decisions", [])
        if not decisions:
            render_empty_state("No triage runs yet. Submit a case in the Triage page to see telemetry.")
        else:
            last = decisions[0]
            provider_info = last.get("provider_info")
            if provider_info:
                with st.container(border=True):
                    render_field_row("Provider", provider_info.get("provider", "N/A"))
                    render_field_row("Model", provider_info.get("model", "N/A"))
                    render_field_row("Prompt Tokens", str(provider_info.get("prompt_tokens", "N/A")))
                    render_field_row("Completion Tokens", str(provider_info.get("completion_tokens", "N/A")))
                    render_field_row("Total Tokens", str(provider_info.get("total_tokens", "N/A")))
                    render_field_row("Latency", f"{provider_info.get('latency_ms', 0):.1f} ms")
                    render_field_row("Finish Reason", provider_info.get("finish_reason", "N/A"))
            else:
                st.info("No provider telemetry recorded for the last case.")
    except Exception:
        st.info("Could not load recent telemetry.")

    with st.expander("About Provider Telemetry"):
        st.markdown(
            "Provider telemetry (model, tokens, latency) is captured from the actual "
            "LLM response during triage and stored in the decision metadata. "
            "With MockProvider, values are deterministic placeholders — not real LLM metrics. "
            "For real telemetry, configure OllamaProvider or a cloud provider."
        )
