from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.components.state import get_client
from streamlit_app.i18n import t


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("cf_title")}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="case-page-subtitle">{t("eval_synthetic_label")}</div>', unsafe_allow_html=True)

    st.info(t("cf_explanation"))

    st.caption(t("cf_domain_scope"))

    client = get_client()

    st.markdown("---")

    if st.button(t("cf_run"), type="primary", use_container_width=True):
        try:
            from case_core.evaluation.scenarios.bias import BIAS_PAIRS
        except ImportError:
            st.error(t("cf_module_error"))
            return
        _run_evaluation(client, BIAS_PAIRS)


def _run_evaluation(client: CASEClient, bias_pairs: list[dict[str, Any]]) -> None:
    results: list[dict[str, Any]] = []

    progress = st.progress(0, text=t("cf_running"))

    for i, pair in enumerate(bias_pairs):
        progress.progress((i) / len(bias_pairs), text=t("cf_pair", id=str(pair.get("pair_id", ""))))

        case_a = pair["case_a"]
        case_b = pair["case_b"]

        try:
            result_a = client.triage_sync(
                report_text=case_a["report_text"],
                domain=case_a["domain"],
                urgency=case_a["urgency"],
                evidence=case_a.get("evidence", []),
            )
            result_b = client.triage_sync(
                report_text=case_b["report_text"],
                domain=case_b["domain"],
                urgency=case_b["urgency"],
                evidence=case_b.get("evidence", []),
            )

            if result_a.get("error") or result_b.get("error"):
                results.append({
                    "pair_id": pair["pair_id"],
                    "changed_attribute": pair["changed_attribute"],
                    "status": "error",
                    "decision_a": None,
                    "decision_b": None,
                    "error": result_a.get("error") or result_b.get("error"),
                })
                continue

            data_a = result_a.get("data", {})
            data_b = result_b.get("data", {})

            decision_a = data_a.get("action", t("common_n_a"))
            decision_b = data_b.get("action", t("common_n_a"))

            decision_consistent = decision_a == decision_b

            results.append({
                "pair_id": pair["pair_id"],
                "changed_attribute": pair["changed_attribute"],
                "status": "ok",
                "decision_a": decision_a,
                "decision_b": decision_b,
                "decision_consistent": decision_consistent,
            })
        except Exception as e:
            results.append({
                "pair_id": pair["pair_id"],
                "changed_attribute": pair["changed_attribute"],
                "status": "error",
                "decision_a": None,
                "decision_b": None,
                "error": str(e),
            })

    progress.progress(1.0, text=t("cf_complete"))
    _render_results(results)


def _render_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info(t("cf_no_results"))
        return

    st.markdown("---")
    st.markdown(f"#### {t('cf_results')}")

    ok_results = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "error"]

    for r in results:
        with st.container(border=True):
            st.markdown(f"**{r['pair_id']}** — {t('cf_changed_attr', attr=r['changed_attribute'])} `{t('eval_simulated_badge')}`")

            if r["status"] == "error":
                st.error(f"Error: {r.get('error', t('common_error'))}")
                continue

            c1, c2, c3 = st.columns([3, 3, 2])
            with c1:
                st.markdown(f"**Case A**")
                st.markdown(f"`{r['decision_a']}`")
            with c2:
                st.markdown(f"**Case B**")
                st.markdown(f"`{r['decision_b']}`")
            with c3:
                if r["decision_consistent"]:
                    st.success(t("cf_invariant"))
                else:
                    st.error(t("cf_changed"))

    st.markdown("---")
    st.markdown(f"#### {t('cf_summary')}")

    total = len(ok_results)
    invariant = sum(1 for r in ok_results if r["decision_consistent"])
    changed = total - invariant
    invariance_rate = (invariant / total * 100) if total else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("cf_total_pairs"), f"{total}")
    m2.metric(t("cf_invariant_count"), f"{invariant}")
    m3.metric(t("cf_changed_count"), f"{changed}")
    m4.metric(t("cf_invariance_rate"), f"{invariance_rate:.0f}%")

    if errors:
        st.warning(t("cf_errors", count=str(len(errors))))

    st.info(t("eval_simulated_banner"))

    with st.expander(t("cf_scope")):
        st.markdown(t("cf_scope_text"))
