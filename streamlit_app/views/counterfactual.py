from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.evaluation.scenarios.bias import BIAS_PAIRS
from streamlit_app.ui.components import render_api_health_check


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Counterfactual Lab</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Evaluate decision invariance across counterfactual pairs</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "**Data Source:** SYNTHETIC — 10 counterfactual pairs in logistics domain. "
        "**Methodology:** Pair A vs Pair B with single-attribute changes. "
        "**Scope:** Logistics domain only. "
        "**Limitation:** MockProvider produces deterministic responses."
    )

    client = _get_client()

    if not render_api_health_check(client):
        return

    st.markdown("---")

    if st.button("Run Counterfactual Evaluation", type="primary", use_container_width=True):
        _run_evaluation(client)


def _run_evaluation(client: CASEClient) -> None:
    results: list[dict[str, Any]] = []

    progress = st.progress(0, text="Running counterfactual pairs...")

    for i, pair in enumerate(BIAS_PAIRS):
        progress.progress((i) / len(BIAS_PAIRS), text=f"Running pair {pair['pair_id']}...")

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
                    "expected_invariance": pair["expected_invariance"],
                    "rationale": pair["rationale"],
                    "status": "error",
                    "decision_a": None,
                    "decision_b": None,
                    "urgency_a": None,
                    "urgency_b": None,
                    "confidence_a": 0,
                    "confidence_b": 0,
                    "decision_consistent": False,
                    "urgency_consistent": False,
                })
                continue

            data_a = result_a.get("data", {})
            data_b = result_b.get("data", {})

            decision_a = data_a.get("action", "N/A")
            decision_b = data_b.get("action", "N/A")
            urgency_a = data_a.get("urgency", "N/A")
            urgency_b = data_b.get("urgency", "N/A")
            confidence_a = data_a.get("confidence", 0)
            confidence_b = data_b.get("confidence", 0)

            decision_consistent = decision_a == decision_b
            urgency_consistent = urgency_a == urgency_b

            results.append({
                "pair_id": pair["pair_id"],
                "changed_attribute": pair["changed_attribute"],
                "expected_invariance": pair["expected_invariance"],
                "rationale": pair["rationale"],
                "status": "ok",
                "decision_a": decision_a,
                "decision_b": decision_b,
                "urgency_a": urgency_a,
                "urgency_b": urgency_b,
                "confidence_a": confidence_a,
                "confidence_b": confidence_b,
                "decision_consistent": decision_consistent,
                "urgency_consistent": urgency_consistent,
            })
        except Exception as e:
            results.append({
                "pair_id": pair["pair_id"],
                "changed_attribute": pair["changed_attribute"],
                "expected_invariance": pair["expected_invariance"],
                "rationale": pair["rationale"],
                "status": "error",
                "decision_a": None,
                "decision_b": None,
                "urgency_a": None,
                "urgency_b": None,
                "confidence_a": 0,
                "confidence_b": 0,
                "decision_consistent": False,
                "urgency_consistent": False,
                "error": str(e),
            })

    progress.progress(1.0, text="Complete")
    _render_results(results)


def _render_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info("No results to display.")
        return

    st.markdown("---")
    st.markdown("#### Results")

    ok_results = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "error"]

    for r in results:
        with st.container(border=True):
            st.markdown(f"**{r['pair_id']}** — Changed attribute: `{r['changed_attribute']}`")
            st.caption(f"Expected invariance: {r['expected_invariance']}. Rationale: {r['rationale']}")

            if r["status"] == "error":
                st.error(f"Error: {r.get('error', 'Unknown error')}")
                continue

            c1, c2, c3 = st.columns([3, 3, 2])
            with c1:
                st.markdown("**Case A**")
                st.caption(f"Decision: `{r['decision_a']}` | Urgency: `{r['urgency_a']}` | Confidence: {r['confidence_a']:.0%}")
            with c2:
                st.markdown("**Case B**")
                st.caption(f"Decision: `{r['decision_b']}` | Urgency: `{r['urgency_b']}` | Confidence: {r['confidence_b']:.0%}")
            with c3:
                if r["decision_consistent"] and r["urgency_consistent"]:
                    st.success("INVARIANT")
                elif r["decision_consistent"]:
                    st.warning("Decision invariant")
                else:
                    st.error("CHANGED")

    st.markdown("---")
    st.markdown("#### Summary")

    total = len(ok_results)
    decision_invariant = sum(1 for r in ok_results if r["decision_consistent"])
    urgency_invariant = sum(1 for r in ok_results if r["urgency_consistent"])
    both_invariant = sum(1 for r in ok_results if r["decision_consistent"] and r["urgency_consistent"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Pairs", f"{total}")
    m2.metric("Decision Invariant", f"{decision_invariant}/{total}")
    m3.metric("Urgency Invariant", f"{urgency_invariant}/{total}")
    m4.metric("Fully Invariant", f"{both_invariant}/{total}")

    if errors:
        st.warning(f"{len(errors)} pair(s) failed to evaluate.")

    with st.expander("Scope & Limitations"):
        st.markdown("""
- **Scope:** 10 counterfactual pairs, all in logistics domain
- **Methodology:** Single-attribute changes (name, location, wording, etc.)
- **Provider:** MockProvider (deterministic) — results reflect pipeline validation behavior, not LLM fairness
- **Not measured:** Real-world bias, demographic fairness, cross-domain invariance
- **Not claimed:** Bias-free, fair, unbiased — this is a counterfactual invariance evaluation tool
- **Coverage:** Logistics domain only; urban_operations and infrastructure pairs not yet defined
""")
