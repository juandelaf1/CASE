from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_api_health_check,
    render_backend_offline,
    render_empty_state,
    render_field_row,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("pl_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("pl_subtitle")}</div>', unsafe_allow_html=True)

    client = _get_client()

    if not render_api_health_check(client):
        return

    try:
        with st.spinner(t("pl_loading")):
            providers_data = client.list_providers_sync()
    except Exception:
        render_backend_offline()
        return

    providers = providers_data.get("providers", [])
    active = providers_data.get("active_provider", "unknown")

    st.markdown(f"#### {t('pl_configured')}")
    for p in providers:
        name = p.get("name", "unknown")
        model = p.get("model", "unknown")
        is_mock = p.get("is_mock", False)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"**{name}**")
                st.caption(f"{t('field_model')}: `{model}`")
            with c2:
                if is_mock:
                    st.warning(t("pl_mock"))
                elif name in ("groq", "ollama", "cloud"):
                    st.success(t("pl_real"))
                else:
                    st.info(t("pl_unknown"))
            with c3:
                if name == active:
                    st.markdown(f"**{t('pl_active')}**")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### {t('pl_neutrality')}")
    st.caption(t("pl_neutrality_desc"))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### {t('pl_telemetry')}")
    st.caption(t("pl_telemetry_desc"))

    try:
        cases_result = client.list_cases_sync(limit=1, offset=0)
        decisions = cases_result.get("decisions", [])
        if not decisions:
            render_empty_state(t("pl_no_runs"))
        else:
            last = decisions[0]
            provider_info = last.get("provider_info")
            if provider_info:
                with st.container(border=True):
                    render_field_row(t("field_provider"), provider_info.get("provider", t("common_n_a")))
                    render_field_row(t("field_model"), provider_info.get("model", t("common_n_a")))

                    latency = provider_info.get("latency_ms", 0)
                    render_field_row(t("field_latency"), f"{latency:.1f} ms" if latency else "N/A")

                    prompt_tokens = provider_info.get("prompt_tokens", 0)
                    completion_tokens = provider_info.get("completion_tokens", 0)
                    total_tokens = provider_info.get("total_tokens", 0)
                    if total_tokens:
                        render_field_row(t("field_tokens"), f"{prompt_tokens} prompt / {completion_tokens} completion / {total_tokens} total")
                    else:
                        render_field_row(t("field_tokens"), t("pl_not_available"))

                    render_field_row(t("field_finish_reason"), provider_info.get("finish_reason", t("common_n_a")))

                    error = provider_info.get("error")
                    if error:
                        st.error(t("pl_provider_error", error=error))
            else:
                st.info(t("pl_no_telemetry"))
    except Exception:
        st.info(t("pl_could_not_load"))

    with st.expander(t("pl_config")):
        st.markdown("""
**Supported Providers:**

| Provider | Env Vars | Status |
|----------|----------|--------|
| MockProvider | (none) | CONNECTED \u2014 deterministic test/demo |
| GroqProvider | `CASE_GROQ_API_KEY`, `CASE_GROQ_MODEL` | CONNECTED \u2014 real inference |
| OllamaProvider | `CASE_OLLAMA_BASE_URL` | TESTED_ISOLATED \u2014 local LLM |
| CloudProvider | `CASE_CLOUD_API_KEY`, `CASE_CLOUD_BASE_URL` | TESTED_ISOLATED \u2014 OpenAI-compatible |

**How to enable Groq:**

```bash
export CASE_PROVIDER=groq
export CASE_GROQ_API_KEY=gsk_...
export CASE_GROQ_MODEL=llama-3.3-70b-versatile
```

**Important:** CASE validation remains active regardless of provider.
The provider may be probabilistic \u2014 the system around it remains controlled.
""")
