from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_app.components.state import get_client

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
        "failure_reason": "Urban domain requires evidence; this case has none. A real provider would reject or escalate.",
    },
]


def render() -> None:
    st.header("Provider Evaluation")
    st.markdown("*Test the triage pipeline with representative cases*")

    client = get_client()

    try:
        health = client.health_sync()
        if health.get("status") != "ok":
            st.warning("CASE API is not healthy.")
            return
    except Exception:
        st.error("Cannot connect to CASE API.")
        return

    st.markdown("---")
    st.markdown("### Pipeline Evaluation")
    st.markdown(
        "Runs 3 cases through the full triage pipeline. "
        "With MockProvider, responses are deterministic and do not reflect real LLM analysis."
    )

    if st.button("Run Evaluation", key="run_quick_eval"):
        results = _run_evaluation(client)
        _render_results(results)


def _run_evaluation(client) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    with st.spinner("Running evaluation..."):
        for i, test_case in enumerate(EVAL_CASES):
            try:
                payload = {
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
                    results.append({
                        "index": i,
                        "description": test_case["description"],
                        "expected_decision": test_case["expected_decision"],
                        "expected_urgency": test_case["expected_urgency"],
                        "expected_failure": test_case.get("expected_failure", False),
                        "failure_reason": test_case.get("failure_reason", ""),
                        "status": "error",
                        "actual_decision": None,
                        "actual_urgency": None,
                        "error": error_msg,
                        "confidence": 0,
                        "processing_time_ms": 0,
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
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "description": test_case["description"],
                    "expected_decision": test_case["expected_decision"],
                    "expected_urgency": test_case["expected_urgency"],
                    "expected_failure": test_case.get("expected_failure", False),
                    "failure_reason": test_case.get("failure_reason", ""),
                    "status": "error",
                    "actual_decision": None,
                    "actual_urgency": None,
                    "error": str(e),
                    "confidence": 0,
                    "processing_time_ms": 0,
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
        "error": ("error", "Error"),
    }

    st.markdown("### Results")

    for r in results:
        status_type, status_text = status_labels.get(r["status"], ("info", r["status"]))

        with st.container():
            st.markdown(f"**{r['description']}**")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.caption("Decision")
                if r["actual_decision"]:
                    st.markdown(f"`{r['actual_decision']}` (expected `{r['expected_decision']}`)")
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

            st.divider()

    total = len(results)
    matches = sum(1 for r in results if r["status"] in ("match", "expected_behavior"))
    errors = sum(1 for r in results if r["status"] == "error")

    m1, m2, m3 = st.columns(3)
    m1.metric("Pipeline Success", f"{total - errors}/{total}")
    m2.metric("Exact Matches", f"{matches}/{total}")
    m3.metric("Errors", f"{errors}/{total}")

    with st.expander("About MockProvider"):
        st.markdown(
            "MockProvider returns deterministic responses for testing the pipeline. "
            "It does not perform real LLM analysis. "
            "For accurate evaluation, use OllamaProvider or a cloud provider."
        )
