from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.components.state import get_client
from streamlit_app.i18n import t

EVAL_CASES = [
    {
        "description": "Minor pothole with photo evidence",
        "report_text": "Minor pothole on Main St. Photo evidence attached.",
        "domain": "urban_operations",
        "urgency": "LOW",
        "evidence": [
            {"id": "ev-001", "type": "text", "content": "Photo confirms small pothole", "source": "test", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}
        ],
        "expected_decision": "approve",
    },
    {
        "description": "Structural crack on bridge",
        "report_text": "Structural crack on bridge over highway.",
        "domain": "urban_operations",
        "urgency": "CRITICAL",
        "evidence": [
            {"id": "ev-001", "type": "text", "content": "Inspection report flags load-bearing concern", "source": "test", "confidence": 0.95, "extracted_at": "2026-09-14T12:00:00Z"}
        ],
        "expected_decision": "escalate",
    },
    {
        "description": "Illegal dumping with no evidence",
        "report_text": "Illegal dumping reported in alley.",
        "domain": "urban_operations",
        "urgency": "LOW",
        "evidence": [],
        "expected_decision": "reject",
        "expected_failure": True,
        "failure_reason": "Urban domain requires evidence; this case has none. Terminal failure is expected behavior.",
    },
]


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("eval_title")}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="case-page-subtitle">{t("eval_synthetic_label")}</div>', unsafe_allow_html=True)

    st.warning(t("eval_disclaimer"))

    client = get_client()

    st.markdown("---")

    if st.button(t("eval_run"), key="run_quick_eval", type="primary", use_container_width=True):
        results = _run_evaluation(client)
        _render_results(results)


def _run_evaluation(client: CASEClient) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    with st.spinner(t("eval_running")):
        for i, test_case in enumerate(EVAL_CASES):
            try:
                payload: dict[str, Any] = {
                    "report_text": test_case["report_text"],
                    "domain": test_case["domain"],
                    "urgency": test_case["urgency"],
                }
                if test_case["evidence"]:
                    payload["evidence"] = test_case["evidence"]

                result = client.triage_sync(**payload)

                if result.get("error"):
                    detail = result.get("detail", {})
                    error_msg = detail.get("error", t("common_error")) if isinstance(detail, dict) else str(detail)
                    is_expected = test_case.get("expected_failure", False)
                    results.append({
                        "index": i,
                        "description": test_case["description"],
                        "expected_decision": test_case["expected_decision"],
                        "expected_failure": is_expected,
                        "failure_reason": test_case.get("failure_reason", ""),
                        "status": "expected_behavior" if is_expected else "unexpected_error",
                        "actual_decision": None,
                        "error": error_msg,
                    })
                    continue

                data = result.get("data", {})
                actual_decision = data.get("action", t("common_n_a"))
                expected_decision = test_case["expected_decision"]

                if test_case.get("expected_failure"):
                    status = "expected_behavior"
                elif actual_decision == expected_decision:
                    status = "match"
                else:
                    status = "mismatch"

                results.append({
                    "index": i,
                    "description": test_case["description"],
                    "expected_decision": expected_decision,
                    "expected_failure": test_case.get("expected_failure", False),
                    "failure_reason": test_case.get("failure_reason", ""),
                    "status": status,
                    "actual_decision": actual_decision,
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "description": test_case["description"],
                    "expected_decision": test_case["expected_decision"],
                    "expected_failure": test_case.get("expected_failure", False),
                    "failure_reason": test_case.get("failure_reason", ""),
                    "status": "unexpected_error",
                    "actual_decision": None,
                    "error": str(e),
                })

    return results


def _render_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info(t("eval_no_results"))
        return

    st.markdown("---")
    st.markdown(f"#### {t('eval_results')}")

    for r in results:
        with st.container(border=True):
            st.markdown(f"**{r['description']}** `{t('eval_simulated_badge')}`")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(t("field_action"))
                if r["actual_decision"]:
                    match = r["actual_decision"] == r["expected_decision"]
                    st.markdown(f"`{r['actual_decision']}`")
                    if match:
                        st.success(t("eval_match"))
                    else:
                        st.error(t("eval_mismatch"))
                elif r["error"]:
                    st.error(r["error"][:100])
            with col2:
                st.caption(t("eval_expected_action"))
                st.markdown(f"`{r['expected_decision']}`")
            with col3:
                st.caption(t("eval_status"))
                if r["status"] == "match":
                    st.success(t("eval_match"))
                elif r["status"] == "mismatch":
                    st.error(t("eval_mismatch"))
                elif r["status"] == "expected_behavior":
                    st.info(t("eval_expected_behavior"))
                else:
                    st.error(t("eval_unexpected_error"))

            if r["failure_reason"]:
                st.caption(r["failure_reason"])

    st.markdown("---")
    st.markdown(f"#### {t('eval_summary')}")

    total = len(results)
    matches = len([r for r in results if r["status"] == "match"])
    mismatches = len([r for r in results if r["status"] == "mismatch"])
    errors = len([r for r in results if r["status"] == "unexpected_error"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("eval_total"), f"{total}")
    m2.metric(t("eval_matches"), f"{matches}")
    m3.metric(t("eval_mismatches"), f"{mismatches}")
    m4.metric(t("eval_errors"), f"{errors}")

    st.info(t("eval_simulated_banner"))

    with st.expander(t("eval_limitations")):
        st.markdown(t("eval_limitations_text"))
