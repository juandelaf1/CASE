from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_action_badge,
    render_backend_offline,
    render_empty_state,
    render_field_row,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("comp_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("comp_subtitle")}</div>', unsafe_allow_html=True)

    client = _get_client()

    st.info(t("comp_how"))
    st.markdown("---")

    try:
        cases_result = client.list_cases_sync(limit=50, offset=0)
        decisions = cases_result.get("decisions", [])
    except Exception:
        render_backend_offline()
        return

    if not decisions:
        render_empty_state(t("comp_no_cases"))
        return

    groq_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "groq"]
    ollama_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "ollama"]

    if not groq_runs and not ollama_runs:
        render_empty_state(t("comp_no_runs"))
        return

    _render_provider_status(groq_runs, ollama_runs)

    st.markdown("---")

    _render_comparison(groq_runs, ollama_runs, decisions)


def _render_provider_status(groq_runs: list[dict], ollama_runs: list[dict]) -> None:
    st.markdown(f"#### {t('comp_available')}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(t("comp_groq_runs"), len(groq_runs))
    with c2:
        st.metric(t("comp_ollama_runs"), len(ollama_runs))
    with c3:
        st.metric(t("comp_total"), len(groq_runs) + len(ollama_runs))


def _render_comparison(
    groq_runs: list[dict],
    ollama_runs: list[dict],
    all_runs: list[dict],
) -> None:
    st.markdown(f"#### {t('comp_side_by_side')}")

    case_ids = sorted(set(
        d.get("case_id", t("common_n_a"))
        for d in all_runs
        if d.get("case_id")
    ))

    if not case_ids:
        render_empty_state(t("comp_no_cases"))
        return

    selected_case = st.selectbox(
        t("comp_select_case"),
        options=case_ids,
        format_func=lambda x: f"Case {x}",
    )

    if not selected_case:
        return

    groq_for_case = next(
        (d for d in groq_runs if d.get("case_id") == selected_case), None
    )
    ollama_for_case = next(
        (d for d in ollama_runs if d.get("case_id") == selected_case), None
    )

    if not groq_for_case and not ollama_for_case:
        st.warning(t("comp_no_runs_case", id=selected_case))
        return

    col_groq, col_ollama = st.columns(2)

    with col_groq:
        _render_provider_column("Groq", groq_for_case)

    with col_ollama:
        _render_provider_column("Ollama", ollama_for_case)

    if groq_for_case and ollama_for_case:
        st.markdown("<br>", unsafe_allow_html=True)
        _render_differences(groq_for_case, ollama_for_case)


def _render_provider_column(name: str, data: dict[str, Any] | None) -> None:
    if not data:
        st.markdown(
            f'<div class="case-comparison-col">'
            f'<div class="case-comparison-header">{name}</div>'
            f'<div style="text-align:center; padding:2rem; color:var(--text-muted);">'
            f'{t("comp_no_data", name=name)}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    pi = data.get("provider_info", {})
    automation = data.get("automation_assessment", {})
    action = data.get("action", t("common_n_a"))
    lifecycle = data.get("lifecycle", t("common_n_a"))
    confidence = data.get("confidence", 0)
    urgency = data.get("urgency", t("common_n_a"))
    risk_level = automation.get("risk_level", t("common_n_a"))
    latency = pi.get("latency_ms", 0)
    total_tokens = pi.get("total_tokens", 0)
    prompt_tokens = pi.get("prompt_tokens", 0)
    completion_tokens = pi.get("completion_tokens", 0)
    model = pi.get("model", t("common_n_a"))
    processing_time = data.get("processing_time_ms", 0)

    html = (
        f'<div class="case-comparison-col">'
        f'<div class="case-comparison-header">{name} \u2014 {model}</div>'
    )

    rows = [
        (t("field_action"), action.upper()),
        (t("field_lifecycle"), lifecycle.replace("_", " ").upper()),
        (t("field_confidence"), f"{confidence:.0%}"),
        (t("field_urgency"), urgency),
        (t("field_risk_level"), risk_level),
        (t("field_automation"), automation.get("automation_decision", t("common_n_a"))),
        (t("field_latency"), f"{latency:.0f} ms"),
        (t("field_processing_time"), f"{processing_time:.0f} ms"),
        (t("field_tokens"), f"{total_tokens} (P:{prompt_tokens} / C:{completion_tokens})"),
    ]

    for label, value in rows:
        html += (
            f'<div class="case-comparison-row">'
            f'<span class="case-comparison-label">{label}</span>'
            f'<span class="case-comparison-value">{value}</span>'
            f'</div>'
        )

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    with st.expander(t("comp_reason", name=name), expanded=False):
        st.markdown(data.get("reason", t("common_n_a")))


def _render_differences(groq: dict, ollama: dict) -> None:
    st.markdown(f"#### {t('comp_diff_title')}")

    groq_action = groq.get("action", t("common_n_a"))
    ollama_action = ollama.get("action", t("common_n_a"))
    groq_confidence = groq.get("confidence", 0)
    ollama_confidence = ollama.get("confidence", 0)
    groq_pi = groq.get("provider_info", {})
    ollama_pi = ollama.get("provider_info", {})
    groq_latency = groq_pi.get("latency_ms", 0)
    ollama_latency = ollama_pi.get("latency_ms", 0)

    diffs = []

    if groq_action != ollama_action:
        diffs.append({
            "metric": t("field_action"),
            "groq": groq_action.upper(),
            "ollama": ollama_action.upper(),
            "note": t("comp_diff_decision"),
        })

    if abs(groq_confidence - ollama_confidence) > 0.1:
        diffs.append({
            "metric": t("field_confidence"),
            "groq": f"{groq_confidence:.0%}",
            "ollama": f"{ollama_confidence:.0%}",
            "note": t("comp_diff_confidence"),
        })

    if groq_latency > 0 and ollama_latency > 0:
        ratio = ollama_latency / groq_latency
        diffs.append({
            "metric": t("field_latency"),
            "groq": f"{groq_latency:.0f} ms",
            "ollama": f"{ollama_latency:.0f} ms",
            "note": t("comp_diff_latency", ratio=f"{ratio:.0f}"),
        })

    if not diffs:
        st.success(t("comp_same"))
        return

    for d in diffs:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 2])
            with c1:
                st.markdown(f"**{d['metric']}**")
            with c2:
                st.markdown(f"**Groq:** {d['groq']}")
            with c3:
                st.markdown(f"**Ollama:** {d['ollama']}")
            st.caption(d["note"])

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("comp_educational")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
