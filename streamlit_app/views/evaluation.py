from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.client import CASEClient
from streamlit_app.ui.components import render_api_health_check

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
        "expected_urgency": "LOW",
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
        "expected_urgency": "CRITICAL",
    },
    {
        "description": "Illegal dumping with no evidence",
        "report_text": "Illegal dumping reported in alley.",
        "domain": "urban_operations",
        "urgency": "LOW",
        "evidence": [],
        "expected_decision": "reject",
        "expected_urgency": "LOW",
        "expected_failure": True,
        "failure_reason": "Urban domain requires evidence; this case has none. Terminal failure is expected behavior.",
    },
]


def _get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    return CASEClient(base_url=api_url)


def render() -> None:
    st.markdown('<div class="case-page-title">Evaluation Lab</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-page-subtitle">Test the triage pipeline with representative cases</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "**Data Source:** SYNTHETIC — deterministic test cases. "
        "**Provider:** MockProvider (deterministic responses, not real LLM analysis). "
        "**Scope:** urban_operations domain only."
    )

    client = _get_client()

    if not render_api_health_check(client):
        return

    st.markdown("---")
    st.markdown("#### Pipeline Evaluation")
    st.caption(
        "Runs 3 synthetic cases through the full triage pipeline. "
        "Results demonstrate pipeline behavior, not LLM quality."
    )

    if st.button("Run Evaluation", key="run_quick_eval", type="primary"):
        results = _run_evaluation(client)
        _render_results(results)

    with st.expander("Metric Definitions"):
        st.markdown("""
| Metric | Formula | Exclusions |
|--------|---------|------------|
| Decision Match | actual_decision == expected_decision | Expected failures |
| Urgency Match | actual_urgency == expected_urgency | Expected failures |
| Pipeline Success | cases_without_error / total_cases | None |
| Error Rate | cases_with_error / total_cases | None |

**Expected failures** are cases where terminal failure is the correct behavior (e.g., missing required evidence). These are excluded from accuracy calculations.
""")


def _run_evaluation(client: CASEClient) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    with st.spinner("Running evaluation..."):
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
                    error_msg = detail.get("error", "Unknown error") if isinstance(detail, dict) else str(detail)
                    is_expected = test_case.get("expected_failure", False)
                    results.append({
                        "index": i,
                        "description": test_case["description"],
                        "expected_decision": test_case["expected_decision"],
                        "expected_urgency": test_case["expected_urgency"],
                        "expected_failure": is_expected,
                        "failure_reason": test_case.get("failure_reason", ""),
                        "status": "expected_behavior" if is_expected else "unexpected_error",
                        "actual_decision": None,
                        "actual_urgency": None,
                        "error": error_msg,
                        "confidence": 0,
                        "processing_time_ms": 0,
                        "provider_info": None,
                    })
                    continue

                data = result.get("data", {})
                actual_decision = data.get("action", "N/A")
                actual_urgency = data.get("urgency", "N/A")
                expected_decision = test_case["expected_decision"]
                expected_urgency = test_case["expected_urgency"]

                decision_match = actual_decision == expected_decision
                urgency_match = actual_urgency == expected_urgency

                if test_case.get("expected_failure"):
                    status = "expected_behavior"
                elif decision_match and urgency_match:
                    status = "match"
                elif decision_match:
                    status = "partial_match"
                else:
                    status = "mismatch"

                results.append({
                    "index": i,
                    "description": test_case["description"],
                    "expected_decision": expected_decision,
                    "expected_urgency": expected_urgency,
                    "expected_failure": test_case.get("expected_failure", False),
                    "failure_reason": test_case.get("failure_reason", ""),
                    "status": status,
                    "actual_decision": actual_decision,
                    "actual_urgency": actual_urgency,
                    "error": None,
                    "confidence": data.get("confidence", 0),
                    "processing_time_ms": data.get("processing_time_ms", 0),
                    "provider_info": data.get("provider_info"),
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "description": test_case["description"],
                    "expected_decision": test_case["expected_decision"],
                    "expected_urgency": test_case["expected_urgency"],
                    "expected_failure": test_case.get("expected_failure", False),
                    "failure_reason": test_case.get("failure_reason", ""),
                    "status": "unexpected_error",
                    "actual_decision": None,
                    "actual_urgency": None,
                    "error": str(e),
                    "confidence": 0,
                    "processing_time_ms": 0,
                    "provider_info": None,
                })

    return results


def _render_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info("No results to display.")
        return

    status_labels = {
        "match": ("pass", "Full match"),
        "partial_match": ("warn", "Decision matches"),
        "mismatch": ("error", "Mismatch"),
        "expected_behavior": ("info", "Expected"),
        "unexpected_error": ("error", "Unexpected error"),
    }

    st.markdown("#### Results")

    valid_results = [r for r in results if not r["expected_failure"] and r["status"] != "unexpected_error"]
    expected_failures = [r for r in results if r["expected_failure"]]
    unexpected_errors = [r for r in results if r["status"] == "unexpected_error"]

    for r in results:
        status_type, status_text = status_labels.get(r["status"], ("info", r["status"]))

        with st.container(border=True):
            st.markdown(f"**{r['description']}**")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.caption("Decision")
                if r["actual_decision"]:
                    match = r["actual_decision"] == r["expected_decision"]
                    st.markdown(f"`{r['actual_decision']}` (expected `{r['expected_decision']}`)")
                    if match:
                        st.success("Match")
                    else:
                        st.error("Mismatch")
                elif r["error"]:
                    st.error(r["error"][:100])
            with col2:
                st.caption("Urgency")
                if r["actual_urgency"]:
                    st.markdown(f"`{r['actual_urgency']}` (expected `{r['expected_urgency']}`)")
            with col3:
                st.caption("Status")
                if status_type == "pass":
                    st.success(status_text)
                elif status_type == "warn":
                    st.warning(status_text)
                elif status_type == "error":
                    st.error(status_text)
                else:
                    st.info(status_text)
            with col4:
                st.caption("Confidence")
                if r["confidence"]:
                    st.markdown(f"{r['confidence']:.0%}")

            if r["failure_reason"]:
                st.caption(r["failure_reason"])

            pi = r.get("provider_info")
            if pi:
                st.caption(f"Provider: {pi.get('provider', 'N/A')} | Model: {pi.get('model', 'N/A')} | Tokens: {pi.get('total_tokens', 0)}")

    st.markdown("---")
    st.markdown("#### Summary Metrics")

    total = len(results)
    successful = len([r for r in results if r["status"] not in ("unexpected_error",)])
    errors = len(unexpected_errors)
    matches = len([r for r in valid_results if r["status"] == "match"])
    valid_count = len(valid_results)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pipeline Success", f"{successful}/{total}")
    m2.metric("Decision Accuracy", f"{matches}/{valid_count}" if valid_count else "N/A")
    m3.metric("Errors", f"{errors}/{total}")
    m4.metric("Expected Failures", f"{len(expected_failures)}")

    if expected_failures:
        st.markdown("**Expected Failures:**")
        for r in expected_failures:
            st.caption(f"- {r['description']}: {r['failure_reason']}")

    if unexpected_errors:
        st.markdown("**Unexpected Errors:**")
        for r in unexpected_errors:
            st.error(f"- {r['description']}: {r['error']}")

    with st.expander("Limitations"):
        st.markdown("""
- MockProvider returns deterministic responses; does not reflect real LLM analysis
- Only 3 synthetic cases in urban_operations domain
- No cross-domain evaluation
- No real-world data
- Cost estimates are illustrative only (based on default pricing, not actual usage)
- For accurate evaluation, use OllamaProvider or a cloud provider with real cases
""")
