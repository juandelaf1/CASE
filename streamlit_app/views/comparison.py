from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import (
    render_backend_offline,
    render_empty_state,
)


def render() -> None:
    st.markdown(
        f'<div class="case-page-title">{t("comp_title")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-page-subtitle">{t("comp_subtitle")}</div>',
        unsafe_allow_html=True,
    )

    tab_live, tab_historical = st.tabs([
        t("comp_tab_live"),
        t("comp_tab_historical"),
    ])

    with tab_live:
        _render_live_tab()

    with tab_historical:
        _render_historical_tab()


# ── Tab 1: Live Comparison ──────────────────────────────────────────


def _render_live_tab() -> None:
    client = get_client()

    try:
        domains = client.list_domains_sync()
    except Exception:
        render_backend_offline()
        return

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("comp_live_desc")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Load from Decision Center if available
    compare_ctx = st.session_state.pop("compare_from_dc", None)
    default_report = compare_ctx.get("report_text", "") if compare_ctx else ""
    default_domain = compare_ctx.get("domain", domains[0] if domains else "default") if compare_ctx else (domains[0] if domains else "default")
    default_urgency = compare_ctx.get("urgency", "MEDIUM") if compare_ctx else "MEDIUM"
    default_evidence = compare_ctx.get("evidence", []) if compare_ctx else []
    default_metadata = compare_ctx.get("metadata", {}) if compare_ctx else {}
    auto_run = compare_ctx is not None

    # Store for comparison API call
    st.session_state._comparison_evidence = default_evidence
    st.session_state._comparison_metadata = default_metadata

    with st.form("live_comparison_form"):
        col_input, col_providers = st.columns([3, 2])

        with col_input:
            domain_idx = 0
            if default_domain in domains:
                domain_idx = domains.index(default_domain)
            domain = st.selectbox(
                t("triage_domain"),
                options=domains if domains else ["default"],
                index=domain_idx,
                key="live_cmp_domain",
            )
            report_text = st.text_area(
                t("triage_report"),
                height=120,
                placeholder=t("triage_report_ph"),
                key="live_cmp_report",
                value=default_report,
            )
            urgency_options = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            urgency_idx = urgency_options.index(default_urgency) if default_urgency in urgency_options else 1
            urgency = st.selectbox(
                t("triage_urgency"),
                options=urgency_options,
                index=urgency_idx,
                key="live_cmp_urgency",
            )
            # Evidence from Decision Center context
            evidence = st.text_area(
                t("field_evidence"),
                height=60,
                placeholder="Ej: Standard ARV adult shipment...",
                key="live_cmp_evidence",
                value="\n".join(default_evidence) if default_evidence else "",
            )
            # Metadata from Decision Center context
            metadata = st.text_area(
                t("triage_metadata"),
                height=60,
                placeholder='{"key": "value"}',
                key="live_cmp_metadata",
                value=str(default_metadata) if default_metadata else "",
            )

        with col_providers:
            st.markdown(f"**{t('comp_select_providers')}**")
            use_groq = st.checkbox("Groq", value=True, key="live_cmp_groq")
            use_ollama = st.checkbox("Ollama", value=True, key="live_cmp_ollama")
            use_mock = st.checkbox("Mock", value=False, key="live_cmp_mock")

        submitted = st.form_submit_button(
            t("comp_run_comparison"),
            type="primary",
            use_container_width=True,
        )

    if auto_run and not submitted:
        submitted = True
        report_text = default_report

    if not submitted:
        return

    if not report_text.strip():
        st.error(t("triage_report_required"))
        return

    selected_providers: list[str] = []
    if use_groq:
        selected_providers.append("groq")
    if use_ollama:
        selected_providers.append("ollama")
    if use_mock:
        selected_providers.append("mock")

    if len(selected_providers) < 1:
        st.warning(t("comp_select_at_least_one"))
        return

    _run_live_comparison(report_text, domain, urgency, selected_providers, evidence, metadata)


def _run_live_comparison(
    report_text: str,
    domain: str,
    urgency: str,
    providers: list[str],
    evidence: str,
    metadata: str,
) -> None:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    base = api_url.rstrip("/")

    progress = st.progress(0, text=t("comp_executing"))
    results: dict[str, dict[str, Any]] = {}

    total = len(providers)
    for idx, provider in enumerate(providers):
        progress.progress(
            int((idx / total) * 100),
            text=t("comp_running_provider", name=provider.upper()),
        )
        try:
            with httpx.Client(timeout=60.0) as http:
                resp = http.post(
                    f"{base}/api/v1/triage",
                    json={
                        "report_text": report_text,
                        "domain": domain,
                        "urgency": urgency,
                        "provider": provider,
                        "evidence": evidence,
                        "metadata": metadata,
                    },
                )
            if resp.status_code in (400, 422):
                detail = resp.json().get("detail", {})
                results[provider] = {"error": True, "detail": detail}
            elif resp.status_code >= 500:
                results[provider] = {
                    "error": True,
                    "detail": f"HTTP {resp.status_code}",
                }
            else:
                resp.raise_for_status()
                results[provider] = {"error": False, "data": resp.json()}
        except httpx.ConnectError:
            results[provider] = {
                "error": True,
                "detail": t("comp_provider_offline"),
            }
        except httpx.TimeoutException:
            results[provider] = {
                "error": True,
                "detail": t("comp_provider_timeout"),
            }
        except httpx.HTTPError as exc:
            results[provider] = {"error": True, "detail": str(exc)}

    progress.progress(100, text=t("comp_complete"))
    progress.empty()

    _render_live_results(results)


def _render_live_results(results: dict[str, dict[str, Any]]) -> None:
    provider_names = list(results.keys())
    cols = st.columns(len(provider_names)) if provider_names else []

    result_data_list: list[tuple[str, dict[str, Any]]] = []

    for col, provider_name in zip(cols, provider_names, strict=True):
        res = results[provider_name]
        with col:
            _render_result_card(
                provider_name=provider_name,
                data=res.get("data") if not res.get("error") else None,
                error=res.get("detail") if res.get("error") else None,
                source_badge="live",
            )
            if not res.get("error") and res.get("data") is not None:
                result_data_list.append((provider_name, res["data"]))

    if len(result_data_list) >= 2:
        st.markdown("---")
        _render_live_differences(result_data_list)

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("comp_educational")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_live_differences(
    pairs: list[tuple[str, dict[str, Any]]],
) -> None:
    st.markdown(f"#### {t('comp_diff_title')}")

    diffs: list[dict[str, str]] = []

    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            name_a, data_a = pairs[i]
            name_b, data_b = pairs[j]
            if not data_a or not data_b:
                continue

            action_a = data_a.get("action", t("common_n_a"))
            action_b = data_b.get("action", t("common_n_a"))
            conf_a = data_a.get("confidence", 0)
            conf_b = data_b.get("confidence", 0)
            lat_a = data_a.get("provider_info", {}).get("latency_ms", 0)
            lat_b = data_b.get("provider_info", {}).get("latency_ms", 0)
            urgency_a = data_a.get("urgency", t("common_n_a"))
            urgency_b = data_b.get("urgency", t("common_n_a"))

            if action_a != action_b:
                diffs.append({
                    "metric": t("field_action"),
                    "val_a": f"{name_a.upper()}: {action_a.upper()}",
                    "val_b": f"{name_b.upper()}: {action_b.upper()}",
                    "note": t("comp_diff_decision"),
                })

            if urgency_a != urgency_b:
                diffs.append({
                    "metric": t("field_urgency"),
                    "val_a": f"{name_a.upper()}: {urgency_a}",
                    "val_b": f"{name_b.upper()}: {urgency_b}",
                    "note": t("comp_diff_urgency"),
                })

            if abs(conf_a - conf_b) > 0.1:
                diffs.append({
                    "metric": t("field_confidence"),
                    "val_a": f"{name_a.upper()}: {conf_a:.0%}",
                    "val_b": f"{name_b.upper()}: {conf_b:.0%}",
                    "note": t("comp_diff_confidence"),
                })

            if lat_a > 0 and lat_b > 0:
                ratio = max(lat_a, lat_b) / max(min(lat_a, lat_b), 1)
                faster = name_a if lat_a < lat_b else name_b
                diffs.append({
                    "metric": t("field_latency"),
                    "val_a": f"{name_a.upper()}: {lat_a:,.0f} ms",
                    "val_b": f"{name_b.upper()}: {lat_b:,.0f} ms",
                    "note": t("comp_diff_latency_provider",
                               faster=faster.upper(), ratio=f"{ratio:.1f}"),
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
                st.markdown(f"**{d['val_a']}**")
            with c3:
                st.markdown(f"**{d['val_b']}**")
            st.caption(d["note"])


# ── Tab 2: Historical Comparison ────────────────────────────────────


def _render_historical_tab() -> None:
    client = get_client()

    try:
        cases_result = client.list_cases_sync(limit=100, offset=0)
        decisions = cases_result.get("decisions", [])
    except Exception:
        render_backend_offline()
        return

    if not decisions:
        _render_historical_empty()
        return

    groq_runs = [
        d for d in decisions
        if d.get("provider_info", {}).get("provider") == "groq"
    ]
    ollama_runs = [
        d for d in decisions
        if d.get("provider_info", {}).get("provider") == "ollama"
    ]
    mock_runs = [
        d for d in decisions
        if d.get("provider_info", {}).get("provider") == "mock"
    ]

    available_providers = []
    if groq_runs:
        available_providers.append(("Groq", groq_runs))
    if ollama_runs:
        available_providers.append(("Ollama", ollama_runs))
    if mock_runs:
        available_providers.append(("Mock", mock_runs))

    if not available_providers:
        _render_historical_empty()
        return

    _render_historical_stats(groq_runs, ollama_runs, mock_runs)

    st.markdown("---")

    if len(available_providers) < 2:
        _render_single_provider_historical(available_providers)
        return

    _render_historical_side_by_side(available_providers, decisions)


def _render_historical_empty() -> None:
    st.markdown('<div class="case-section-educational">', unsafe_allow_html=True)
    st.markdown(f"### {t('comp_empty_title')}")
    st.markdown(t("comp_empty_desc"))
    st.markdown(
        f'<p style="color:var(--text-muted); font-size:0.88rem;">{t("comp_empty_how")}</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_historical_stats(
    groq_runs: list[dict[str, Any]],
    ollama_runs: list[dict[str, Any]],
    mock_runs: list[dict[str, Any]],
) -> None:
    total = len(groq_runs) + len(ollama_runs) + len(mock_runs)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(t("comp_groq_runs"), len(groq_runs))
    with c2:
        st.metric(t("comp_ollama_runs"), len(ollama_runs))
    with c3:
        st.metric(t("comp_mock_runs"), len(mock_runs))
    with c4:
        st.metric(t("comp_total"), total)


def _render_single_provider_historical(
    available: list[tuple[str, list[dict[str, Any]]]],
) -> None:
    provider_name, runs = available[0]

    st.info(t("comp_single_provider", name=provider_name))

    case_ids = sorted({d.get("case_id", "") for d in runs if d.get("case_id")})
    if not case_ids:
        render_empty_state(t("comp_no_cases"))
        return

    selected_case = st.selectbox(
        t("comp_select_case"),
        options=case_ids,
        format_func=lambda x: f"Case {x}",
        key="hist_single_select",
    )
    if not selected_case:
        return

    run_data = next(
        (d for d in runs if d.get("case_id") == selected_case), None
    )
    if not run_data:
        render_empty_state(t("comp_no_runs_case", id=selected_case))
        return

    _render_result_card(
        provider_name=provider_name,
        data=run_data,
        source_badge="historical",
    )


def _render_historical_side_by_side(
    available: list[tuple[str, list[dict[str, Any]]]],
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
        key="hist_side_select",
    )
    if not selected_case:
        return

    provider_runs: list[tuple[str, dict[str, Any] | None]] = []
    for provider_name, runs in available:
        match = next(
            (d for d in runs if d.get("case_id") == selected_case), None
        )
        provider_runs.append((provider_name, match))

    has_any = any(data is not None for _, data in provider_runs)
    if not has_any:
        st.warning(t("comp_no_runs_case", id=selected_case))
        return

    st.markdown(f"#### {t('comp_side_by_side')}")

    cols = st.columns(len(provider_runs))
    for col, (pname, pdata) in zip(cols, provider_runs, strict=True):
        with col:
            _render_result_card(
                provider_name=pname,
                data=pdata,
                source_badge="historical",
            )

    valid_pairs = [(n, d) for n, d in provider_runs if d is not None]
    if len(valid_pairs) >= 2:
        st.markdown("---")
        _render_historical_differences(valid_pairs)


def _render_historical_differences(
    pairs: list[tuple[str, dict[str, Any]]],
) -> None:
    st.markdown(f"#### {t('comp_diff_title')}")

    diffs: list[dict[str, str]] = []

    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            name_a, data_a = pairs[i]
            name_b, data_b = pairs[j]

            action_a = data_a.get("action", t("common_n_a"))
            action_b = data_b.get("action", t("common_n_a"))
            conf_a = data_a.get("confidence", 0)
            conf_b = data_b.get("confidence", 0)
            lat_a = data_a.get("provider_info", {}).get("latency_ms", 0)
            lat_b = data_b.get("provider_info", {}).get("latency_ms", 0)

            if action_a != action_b:
                diffs.append({
                    "metric": t("field_action"),
                    "val_a": f"{name_a.upper()}: {action_a.upper()}",
                    "val_b": f"{name_b.upper()}: {action_b.upper()}",
                    "note": t("comp_diff_decision"),
                })

            if abs(conf_a - conf_b) > 0.1:
                diffs.append({
                    "metric": t("field_confidence"),
                    "val_a": f"{name_a.upper()}: {conf_a:.0%}",
                    "val_b": f"{name_b.upper()}: {conf_b:.0%}",
                    "note": t("comp_diff_confidence"),
                })

            if lat_a > 0 and lat_b > 0:
                faster = name_a if lat_a < lat_b else name_b
                ratio = max(lat_a, lat_b) / max(min(lat_a, lat_b), 1)
                diffs.append({
                    "metric": t("field_latency"),
                    "val_a": f"{name_a.upper()}: {lat_a:,.0f} ms",
                    "val_b": f"{name_b.upper()}: {lat_b:,.0f} ms",
                    "note": t("comp_diff_latency_provider",
                               faster=faster.upper(), ratio=f"{ratio:.1f}"),
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
                st.markdown(f"**{d['val_a']}**")
            with c3:
                st.markdown(f"**{d['val_b']}**")
            st.caption(d["note"])

    st.markdown(
        f'<div class="case-section-educational">'
        f'<p>{t("comp_educational")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Shared result card ──────────────────────────────────────────────


def _render_result_card(
    provider_name: str,
    data: dict[str, Any] | None,
    error: str | None = None,
    source_badge: str = "live",
) -> None:
    if source_badge == "live":
        badge_html = (
            '<span class="case-badge" style="background:#0d6efd18; color:#0d6efd; '
            'font-size:0.72rem; font-weight:600; padding:2px 8px; border-radius:4px;">'
            'EN VIVO</span>'
        )
    else:
        badge_html = (
            '<span class="case-badge" style="background:#6c757d18; color:#6c757d; '
            'font-size:0.72rem; font-weight:600; padding:2px 8px; border-radius:4px;">'
            'HISTÓRICO</span>'
        )

    if error is not None:
        html = (
            f'<div class="case-comparison-col">'
            f'<div class="case-comparison-header">'
            f'{_esc(provider_name)} {badge_html}'
            f'</div>'
            f'<div style="text-align:center; padding:1.5rem; color:#dc3545;">'
            f'<div style="font-size:1.4rem; margin-bottom:0.5rem;">&#x26A0;</div>'
            f'<div style="font-weight:600;">{t("comp_error")}</div>'
            f'<div style="font-size:0.85rem; margin-top:0.3rem; color:var(--text-muted);">'
            f'{_esc(str(error))}</div>'
            f'</div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    if not data:
        html = (
            f'<div class="case-comparison-col">'
            f'<div class="case-comparison-header">'
            f'{_esc(provider_name)} {badge_html}'
            f'</div>'
            f'<div style="text-align:center; padding:2rem; color:var(--text-muted);">'
            f'{_esc(t("comp_no_data", name=provider_name))}'
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
        (t("field_provider"), pi.get("provider", provider_name)),
        (t("field_model"), model),
        (t("field_action"), action.upper()),
        (t("field_urgency"), urgency),
        (t("field_confidence"), f"{confidence:.0%}"),
        (t("field_tokens"), f"{total_tokens:,} (P:{prompt_tokens} / C:{completion_tokens})"),
        (t("field_latency"), f"{latency:,.0f} ms"),
        (t("field_processing_time"), f"{processing_time:,.0f} ms"),
        (t("field_lifecycle"), lifecycle.replace("_", " ").upper()),
        (t("field_risk_level"), automation.get("risk_level", t("common_n_a"))),
    ]

    html = (
        f'<div class="case-comparison-col">'
        f'<div class="case-comparison-header">'
        f'{_esc(provider_name)} {badge_html}'
        f'</div>'
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

    with st.expander(t("comp_reason", name=provider_name), expanded=False):
        st.markdown(data.get("reason", t("common_n_a")))


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
