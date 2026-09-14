from typing import Any

import streamlit as st

from streamlit_app.components.state import get_client

TEST_CASES = [
    {
        "case_id": "eval-001",
        "report_text": "Minor pothole on Main St. Photo evidence attached.",
        "domain": "urban_operations",
        "urgency": "LOW",
        "evidence": [
            {"id": "ev-001", "type": "text", "content": "Photo confirms small pothole", "source": "test", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}
        ],
    },
    {
        "case_id": "eval-002",
        "report_text": "Structural crack on bridge over highway.",
        "domain": "urban_operations",
        "urgency": "CRITICAL",
        "evidence": [
            {"id": "ev-001", "type": "text", "content": "Inspection report flags load-bearing concern", "source": "test", "confidence": 0.95, "extracted_at": "2026-09-14T12:00:00Z"}
        ],
    },
    {
        "case_id": "eval-003",
        "report_text": "Illegal dumping reported in alley.",
        "domain": "urban_operations",
        "urgency": "LOW",
        "evidence": [],
    },
]


def _render_comparison_table(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info("No comparison results to display.")
        return

    st.markdown("### Provider Comparison Results")

    headers = ["Provider", "Model", "Cases", "Decision Acc.", "Urgency Acc.", "Avg Latency (ms)"]
    cols = st.columns(len(headers))
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")

    for r in results:
        cols = st.columns(len(headers))
        cols[0].write(r.get("provider", "N/A"))
        cols[1].write(r.get("model", "N/A"))
        cols[2].write(str(r.get("total_cases", 0)))
        cols[3].write(f"{r.get('decision_accuracy', 0):.1%}")
        cols[4].write(f"{r.get('urgency_accuracy', 0):.1%}")
        cols[5].write(f"{r.get('avg_latency_ms', 0):.0f}")


def render() -> None:
    st.header("Provider Evaluation")
    st.markdown("*Compare provider performance on the same dataset*")

    client = get_client()

    try:
        health = client.health_sync()
        if health.get("status") != "ok":
            st.warning("CASE API is not healthy. Provider comparison may not work.")
            return
    except Exception:
        st.error("Cannot connect to CASE API. Start the API server first.")
        return

    st.markdown("---")
    st.markdown("### Quick Evaluation")
    st.markdown(
        "Run a quick evaluation through the API with the MockProvider. "
        "This tests the end-to-end pipeline with 3 representative cases."
    )

    if st.button("Run Quick Evaluation", key="run_quick_eval"):
        results = []
        correct_decisions = 0
        correct_urgencies = 0
        total_cases = len(TEST_CASES)

        expected = {
            "eval-001": ("approve", "LOW"),
            "eval-002": ("escalate", "CRITICAL"),
            "eval-003": ("reject", "LOW"),
        }

        with st.spinner("Running evaluation..."):
            for test_case in TEST_CASES:
                try:
                    result = client.triage_sync(**test_case)
                    if result.get("error"):
                        st.warning(f"Case {test_case['case_id']}: Error - {result.get('detail', 'Unknown')}")
                        continue

                    data = result.get("data", {})
                    exp_decision, exp_urgency = expected.get(test_case["case_id"], ("unknown", "UNKNOWN"))

                    if data.get("action") == exp_decision:
                        correct_decisions += 1
                    if data.get("urgency") == exp_urgency:
                        correct_urgencies += 1

                    results.append({
                        "case_id": test_case["case_id"],
                        "decision": data.get("action", "N/A"),
                        "urgency": data.get("urgency", "N/A"),
                        "confidence": data.get("confidence", 0),
                        "processing_time_ms": data.get("processing_time_ms", 0),
                        "expected_decision": exp_decision,
                        "expected_urgency": exp_urgency,
                    })
                except Exception as e:
                    st.warning(f"Case {test_case['case_id']}: {e}")

        if results:
            st.markdown("### Evaluation Results")

            headers = ["Case", "Decision", "Expected", "Match", "Urgency", "Expected", "Match", "Confidence", "Time (ms)"]
            cols = st.columns(len(headers))
            for col, header in zip(cols, headers):
                col.markdown(f"**{header}**")

            for r in results:
                cols = st.columns(len(headers))
                cols[0].write(r["case_id"])
                cols[1].write(r["decision"])
                cols[2].write(r["expected_decision"])
                cols[3].write("Yes" if r["decision"] == r["expected_decision"] else "No")
                cols[4].write(r["urgency"])
                cols[5].write(r["expected_urgency"])
                cols[6].write("Yes" if r["urgency"] == r["expected_urgency"] else "No")
                cols[7].write(f"{r['confidence']:.2f}")
                cols[8].write(f"{r['processing_time_ms']:.0f}")

            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            col1.metric("Decision Accuracy", f"{correct_decisions}/{total_cases}", f"{correct_decisions/total_cases:.0%}")
            col2.metric("Urgency Accuracy", f"{correct_urgencies}/{total_cases}", f"{correct_urgencies/total_cases:.0%}")
            col3.metric("Total Cases", str(total_cases))

    st.markdown("---")
    st.markdown("### Provider Comparison")
    st.markdown(
        "To compare providers (e.g., MockProvider vs OllamaProvider), "
        "run the evaluation with different provider configurations and compare results side by side."
    )

    with st.expander("How to compare providers"):
        st.markdown(
            "1. Start the API with MockProvider (default)\n"
            "2. Run Quick Evaluation above\n"
            "3. Restart the API with OllamaProvider\n"
            "4. Run Quick Evaluation again\n"
            "5. Compare the results"
        )

    with st.expander("Architecture note"):
        st.markdown(
            "The Streamlit dashboard communicates with CASE exclusively through the HTTP API. "
            "Provider evaluation runs through the same triage pipeline as operational requests, "
            "ensuring evaluation results reflect real system behavior."
        )
