from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_empty_state,
    render_field_row,
    render_metric_cards,
)

PROVIDER_DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "mock",
        "model_key": "CASE_MOCK_MODEL",
        "default_model": "mock-model",
        "health_type": "always_available",
    },
    {
        "name": "groq",
        "model_key": "CASE_GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
        "health_type": "api_key_check",
        "api_key_env": "CASE_GROQ_API_KEY",
    },
    {
        "name": "ollama",
        "model_key": "CASE_OLLAMA_MODEL",
        "default_model": "llama3",
        "health_type": "http_endpoint",
        "health_url": "http://localhost:11434/api/tags",
    },
]


def _check_provider_health(provider: dict[str, str]) -> tuple[bool, str, str]:
    """Check provider health. Returns (available, status_label, endpoint_display)."""
    health_type = provider["health_type"]

    if health_type == "always_available":
        return True, t("pl_available"), t("pl_mock_endpoint")

    if health_type == "api_key_check":
        api_key_env = provider.get("api_key_env", "")
        key_set = bool(os.environ.get(api_key_env))
        endpoint = f"env:{api_key_env}" if key_set else t("pl_groq_key_missing")
        return key_set, t("pl_available") if key_set else t("pl_unavailable"), endpoint

    if health_type == "http_endpoint":
        url = provider.get("health_url", "")
        try:
            resp = httpx.get(url, timeout=5.0)
            available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
            available = False
        status = t("pl_available") if available else t("pl_unavailable")
        return available, status, url

    return False, t("pl_unknown"), ""


def _render_provider_metrics(available_providers: list[tuple[str, list[dict[str, Any]]]]) -> None:
    groq_latencies = []
    ollama_latencies = []
    groq_costs = []
    ollama_costs = []

    for provider_name, runs in available_providers:
        if provider_name.lower() == "groq":
            for run in runs:
                latency = run.get("provider_info", {}).get("latency_ms", 0)
                if latency:
                    groq_latencies.append(latency)
                cost = run.get("cost")
                if cost:
                    try:
                        groq_costs.append(float(cost))
                    except (ValueError, TypeError):
                        pass
        elif provider_name.lower() == "ollama":
            for run in runs:
                latency = run.get("provider_info", {}).get("latency_ms", 0)
                if latency:
                    ollama_latencies.append(latency)
                cost = run.get("cost")
                if cost:
                    try:
                        ollama_costs.append(float(cost))
                    except (ValueError, TypeError):
                        pass

    if groq_latencies or ollama_latencies:
        st.markdown(f"**{t('pl_latency_comparison')}**")
        st.markdown(f'<p class="case-text-muted">{t("pl_latency_desc")}</p>', unsafe_allow_html=True)
        chart_data = {"Groq": groq_latencies if groq_latencies else [0], "Ollama": ollama_latencies if ollama_latencies else [0]}
        st.bar_chart(chart_data)
        if groq_latencies and ollama_latencies:
            avg_groq = sum(groq_latencies) / len(groq_latencies)
            avg_ollama = sum(ollama_latencies) / len(ollama_latencies)
            ratio = avg_ollama / avg_groq if avg_groq > 0 else 0
            st.caption(t("pl_latency_note", avg_groq=avg_groq, avg_ollama=avg_ollama, ratio=ratio))

    st.markdown("<br>", unsafe_allow_html=True)

    if groq_costs or ollama_costs:
        st.markdown(f"**{t('pl_cost_comparison')}**")
        st.markdown(f'<p class="case-text-muted">{t("pl_cost_desc")}</p>', unsafe_allow_html=True)
        chart_data = {"Groq": groq_costs if groq_costs else [0], "Ollama": ollama_costs if ollama_costs else [0]}
        st.bar_chart(chart_data)
        if groq_costs and ollama_costs:
            avg_groq_cost = sum(groq_costs) / len(groq_costs)
            avg_ollama_cost = sum(ollama_costs) / len(ollama_costs)
            ratio = avg_ollama_cost / avg_groq_cost if avg_groq_cost > 0 else 0
            st.caption(t("pl_cost_note", avg_groq_cost=avg_groq_cost, avg_ollama_cost=avg_ollama_cost, ratio=ratio))


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("pl_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("pl_subtitle")}</div>', unsafe_allow_html=True)

    client = get_client()

    try:
        client.health_sync()
    except Exception:
        render_backend_offline()
        return

    try:
        with st.spinner(t("pl_loading")):
            providers_data = client.list_providers_sync()
    except Exception:
        render_backend_offline()
        return

    providers = providers_data.get("providers", [])
    active = providers_data.get("active_provider", "unknown")

    if st.button(t("pl_check_health"), use_container_width=False):
        st.rerun()

    st.markdown(f"#### {t('pl_health_status')}")

    health_results: list[dict[str, str]] = []
    for pdef in PROVIDER_DEFINITIONS:
        available, status_label, endpoint = _check_provider_health(pdef)
        health_results.append({
            "name": pdef["name"],
            "model": os.environ.get(pdef["model_key"], pdef["default_model"]),
            "available": "yes" if available else "no",
            "status": status_label,
            "endpoint": endpoint,
        })

    render_metric_cards([
        {
            "label": r["name"],
            "value": r["status"],
            "icon": "\u2705" if r["available"] == "yes" else "\u274c",
            "color": "#1a7a4a" if r["available"] == "yes" else "#dc2626",
        }
        for r in health_results
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    for r in health_results:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1:
                st.markdown(f"**{r['name']}**")
                st.caption(f"{t('field_model')}: `{r['model']}`")
            with c2:
                color = "#1a7a4a" if r["available"] == "yes" else "#dc2626"
                st.markdown(
                    f'<span style="color:{color}; font-weight:600;">{r["status"]}</span>',
                    unsafe_allow_html=True,
                )
            with c3:
                st.caption(f"{t('pl_endpoint')}: `{r['endpoint']}`")

            if r["name"] == active:
                st.markdown(f"**{t('pl_active')}**")

    st.markdown("<br>", unsafe_allow_html=True)

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

    st.markdown(f"#### {t('pl_neutrality_title')}")
    st.caption(t("pl_neutrality_explain"))

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

    st.markdown(f"#### {t('pl_metrics_title')}")

    try:
        client = get_client()
        cases_result = client.list_cases_sync(limit=100, offset=0)
        decisions = cases_result.get("decisions", [])
        
        groq_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "groq"]
        ollama_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "ollama"]
        mock_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "mock"]
        
        available_providers = []
        if groq_runs:
            available_providers.append(("Groq", groq_runs))
        if ollama_runs:
            available_providers.append(("Ollama", ollama_runs))
        if mock_runs:
            available_providers.append(("Mock", mock_runs))
            
        if available_providers:
            _render_provider_metrics(available_providers)
        else:
            render_empty_state(t("pl_no_runs"))
    except Exception:
        st.info(t("pl_could_not_load"))

    with st.expander(t("pl_config")):
        st.markdown("""
**Supported Providers:**

| Provider | Env Vars | Status |
|----------|----------|--------|
| MockProvider | (none) | CONNECTED — deterministic test/demo |
| GroqProvider | `CASE_GROQ_API_KEY`, `CASE_GROQ_MODEL` | CONNECTED — real inference |
| OllamaProvider | `CASE_OLLAMA_BASE_URL` | TESTED_ISOLATED — local LLM |
| CloudProvider | `CASE_CLOUD_API_KEY`, `CASE_CLOUD_BASE_URL` | TESTED_ISOLATED — OpenAI-compatible |

**How to enable Groq:**

```bash
export CASE_PROVIDER=groq
export CASE_GROQ_API_KEY=gsk_...
export CASE_GROQ_MODEL=llama-3.3-70b-versatile
```

**Important:** CASE validation remains active regardless of provider.
The provider may be probabilistic — the system around it remains controlled.
""")
