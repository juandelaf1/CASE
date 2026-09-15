from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import (
    render_api_health_check,
    render_case_decision,
    render_field_row,
    render_model_proposal,
    render_validation_section,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Provider Comparison</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Run the same case through the current provider and compare results</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "**Scope:** Runs one case through the currently configured provider. "
        "For multi-provider comparison, restart the API with different `CASE_PROVIDER` values. "
        "**Not compared:** Different inputs, different pipelines, or different evaluation criteria."
    )

    client = _get_client()

    if not render_api_health_check(client):
        return

    st.markdown("---")

    with st.form("comparison_form"):
        st.markdown("#### Case Input")
        report_text = st.text_area(
            "Report Text",
            value="Minor pothole on Main St. Photo evidence attached.",
            height=100,
        )
        c1, c2 = st.columns(2)
        with c1:
            domain = st.selectbox("Domain", ["urban_operations", "logistics", "infrastructure"])
        with c2:
            urgency = st.selectbox("Urgency", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

        evidence_json = st.text_area(
            "Evidence (JSON array, optional)",
            value='[{"id": "ev-001", "type": "text", "content": "Photo confirms issue", "source": "test", "confidence": 0.9, "extracted_at": "2026-09-15T00:00:00Z"}]',
            height=80,
        )

        submitted = st.form_submit_button("Run Case", type="primary", use_container_width=True)

    if submitted:
        import json

        try:
            evidence = json.loads(evidence_json) if evidence_json.strip() else []
        except json.JSONDecodeError:
            st.error("Invalid JSON in evidence field.")
            return

        with st.spinner("Running through CASE pipeline..."):
            result = client.triage_sync(
                report_text=report_text,
                domain=domain,
                urgency=urgency,
                evidence=evidence,
            )

        if result.get("error"):
            st.error(f"Error: {result.get('detail', 'Unknown error')}")
            return

        data = result.get("data", {})

        st.markdown("---")
        st.markdown("#### Result")

        render_model_proposal(data)

        render_validation_section()

        render_case_decision(data)

        st.markdown("---")
        st.markdown("#### Provider Telemetry")

        provider_info = data.get("provider_info")
        if provider_info:
            with st.container(border=True):
                render_field_row("Provider", provider_info.get("provider", "N/A"))
                render_field_row("Model", provider_info.get("model", "N/A"))

                latency = provider_info.get("latency_ms", 0)
                render_field_row("Latency", f"{latency:.1f} ms" if latency else "N/A")

                prompt_tokens = provider_info.get("prompt_tokens", 0)
                completion_tokens = provider_info.get("completion_tokens", 0)
                total_tokens = provider_info.get("total_tokens", 0)
                if total_tokens:
                    render_field_row("Tokens", f"{prompt_tokens} prompt / {completion_tokens} completion / {total_tokens} total")
                else:
                    render_field_row("Tokens", "NOT AVAILABLE")

                render_field_row("Finish Reason", provider_info.get("finish_reason", "N/A"))

                error = provider_info.get("error")
                if error:
                    st.error(f"Provider error: {error}")
        else:
            st.info("No provider telemetry available.")

    with st.expander("Multi-Provider Comparison"):
        st.markdown("""
To compare across providers, restart the API with different configurations:

```bash
# Provider A: MockProvider (deterministic)
CASE_PROVIDER=mock python -m case_api.main

# Provider B: GroqProvider (real inference)
CASE_PROVIDER=groq CASE_GROQ_API_KEY=gsk_... python -m case_api.main
```

Then submit the same case to each and compare results in the Case Explorer.

**Important:** Each run uses the same CASE pipeline — only the provider changes.
""")
