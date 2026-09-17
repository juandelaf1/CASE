from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_empty_state,
)


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown(
        f'<div class="case-page-title">{t("comp_title")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-page-subtitle">{t("comp_subtitle")}</div>',
        unsafe_allow_html=True,
    )

    client = _get_client()

    try:
        cases_result = client.list_cases_sync(limit=100, offset=0)
        decisions = cases_result.get("decisions", [])
    except Exception:
        render_backend_offline()
        return

    if not decisions:
        _render_empty()
        return

    groq_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "groq"]
    ollama_runs = [d for d in decisions if d.get("provider_info", {}).get("provider") == "ollama"]

    if not groq_runs and not ollama_runs:
        _render_empty()
        return

    _render_provider_status(groq_runs, ollama_runs)

    st.markdown("---")

    if not groq_runs or not ollama_runs:
        _render_single_provider(groq_runs, ollama_runs)
        return

    _render_side_by_side(groq_runs, ollama_runs, decisions)


def _render_empty() -> None:
    st.markdown('<div class="case-section-educational">', unsafe_allow_html=True)
    st.markdown(f"### {t('comp_empty_title')}")
    st.markdown(t("comp_empty_desc"))
    st.markdown(
        f'<p style="color:var(--text-muted); font-size:0.88rem;">{t("comp_empty_how")}</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_provider_status(
    groq_runs: list[dict[str, Any]],
    ollama_runs: list[dict[str, Any]],
) -> None:
    total = len(groq_runs) + len(ollama_runs)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(t("comp_groq_runs"), len(groq_runs))
    with c2:
        st.metric(t("comp_ollama_runs"), len(ollama_runs))
    with c3:
        st.metric(t("comp_total"), total)


def _render_single_provider(
    groq_runs: list[dict[str, Any]],
    ollama_runs: list[dict[str, Any]],
) -> None:
    if groq_runs:
        provider_name = "Groq"
        runs = groq_runs
    else:
        provider_name = "Ollama"
        runs = ollama_runs

    st.info(t("comp_single_provider", name=provider_name))

    case_ids = sorted({d.get("case_id", "") for d in runs if d.get("case_id")})
    if not case_ids:
        render_empty_state(t("comp_no_cases"))
        return

    selected_case = st.selectbox(
        t("comp_select_case"),
        options=case_ids,
        format_func=lambda x: f"Case {x}",
        key="single_provider_select",
    )
    if not selected_case:
        return

    run_data = next(
        (d for d in runs if d.get("case_id") == selected_case), None
    )
    if not run_data:
        render_empty_state(t("comp_no_runs_case", id=selected_case))
        return

    _render_provider_card(provider_name, run_data)


def _render_side_by_side(
    groq_runs: list[dict[str, Any]],
    ollama_runs: list[dict[str, Any]],
    all_runs: list[dict[str, Any]],
) -> None:
    case_ids = sorted({d.get("case_id", "") for d in all_runs if d.get("case_id")})

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

    st.markdown(f"#### {t('comp_side_by_side')}")

    col_groq, col_ollama = st.columns(2)

    with col_groq:
        _render_provider_card("Groq", groq_for_case)

    with col_ollama:
        _render_provider_card("Ollama", ollama_for_case)

    if groq_for_case and ollama_for_case:
        st.markdown("")
        _render_differences(groq_for_case, ollama_for_case)


def _render_provider_card(name: str, data: dict[str, Any] | None) -> None:
    if not data:
        html = (
            f'<div class="case-comparison-col">'
            f'<div class="case-comparison-header">{_esc(name)}</div>'
            f'<div style="text-align:center; padding:2rem; color:var(--text-muted);">'
            f'{_esc(t("comp_no_data", name=name))}'
            f'</div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    pi = data.get("provider_info", {})
    automation = data.get("automation_assessment", {})
    action = data.get("action", t("common_n_a"))
    lifecycle = data.get("lifecycle", t("common_n_a"))
    confidence = data.get("confidence", 0)
    urgency = data.get("urgency", t("common_n_a"))
    model = pi.get("model", t("common_n_a"))
    latency = pi.get("latency_ms", 0)
    total_tokens = pi.get("total_tokens", 0)
    prompt_tokens = pi.get("prompt_tokens", 0)
    completion_tokens = pi.get("completion_tokens", 0)
    processing_time = data.get("processing_time_ms", 0)

    row_data = [
        (t("field_action"), action.upper()),
        (t("field_urgency"), urgency),
        (t("field_confidence"), f"{confidence:.0%}"),
        (t("field_latency"), f"{latency:,.0f} ms"),
        (t("field_tokens"), f"{total_tokens:,} (P:{prompt_tokens} / C:{completion_tokens})"),
        (t("field_lifecycle"), lifecycle.replace("_", " ").upper()),
        (t("field_processing_time"), f"{processing_time:,.0f} ms"),
        (t("field_risk_level"), automation.get("risk_level", t("common_n_a"))),
    ]

    html = (
        f'<div class="case-comparison-col">'
        f'<div class="case-comparison-header">{_esc(name)} \u2014 {_esc(model)}</div>'
    )
    for label, value in row_data:
        html += (
            f'<div class="case-comparison-row">'
            f'<span class="case-comparison-label">{_esc(label)}</span>'
            f'<span class="case-comparison-value">{_esc(value)}</span>'
            f'</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    with st.expander(t("comp_reason", name=name), expanded=False):
        st.markdown(data.get("reason", t("common_n_a")))


def _render_differences(groq: dict[str, Any], ollama: dict[str, Any]) -> None:
    st.markdown(f"#### {t('comp_diff_title')}")

    groq_action = groq.get("action", t("common_n_a"))
    ollama_action = ollama.get("action", t("common_n_a"))
    groq_confidence = groq.get("confidence", 0)
    ollama_confidence = ollama.get("confidence", 0)
    groq_latency = groq.get("provider_info", {}).get("latency_ms", 0)
    ollama_latency = ollama.get("provider_info", {}).get("latency_ms", 0)

    diffs: list[dict[str, str]] = []

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
            "groq": f"{groq_latency:,.0f} ms",
            "ollama": f"{ollama_latency:,.0f} ms",
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


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
