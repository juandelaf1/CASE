import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "src")

from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.infrastructure_policy import InfrastructurePolicy
from case_core.domain.urban_policy import UrbanPolicy
from case_core.reliability.pipeline import ReliabilityPipeline

SCENARIOS_DIR = Path(__file__).parent.parent.parent / "evaluation" / "scenarios"

DOMAIN_POLICIES = {
    "urban_operations": UrbanPolicy,
    "infrastructure": InfrastructurePolicy,
}


def _load_json(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _build_case(scenario: dict) -> OperationalCase:
    evidence = [
        EvidenceItem(
            id=e["id"],
            type=EvidenceType(e["type"]),
            content=e["content"],
            source=e["source"],
            confidence=e["confidence"],
            extracted_at=e["extracted_at"],
        )
        for e in scenario.get("evidence", [])
    ]
    return OperationalCase(
        case_id=scenario["case_id"],
        report_text=scenario["report_text"],
        domain=scenario["domain"],
        urgency=UrgencyLevel(scenario.get("urgency", "MEDIUM")),
        evidence=evidence,
    )


def _valid_output(scenario: dict) -> str:
    return json.dumps({
        "decision": scenario.get("expected_decision", "approve"),
        "reason": "Regression test case with sufficient evidence for decision",
        "urgency": scenario.get("expected_urgency", "MEDIUM"),
        "confidence": 0.85,
        "evidence_summary": "Evidence validated for regression testing",
    })


class TestRegressionNormalCases:
    def test_normal_cases_exist(self):
        path = SCENARIOS_DIR / "normal_cases" / "urban_v1.0.json"
        assert path.exists()
        cases = _load_json(path)
        assert len(cases) >= 1

    @pytest.mark.parametrize(
        "scenario",
        _load_json(SCENARIOS_DIR / "normal_cases" / "urban_v1.0.json"),
        ids=lambda s: s["case_id"],
    )
    def test_normal_case_passes_pipeline(self, scenario: dict):
        policy = DOMAIN_POLICIES.get(scenario["domain"], UrbanPolicy)()
        pipeline = ReliabilityPipeline(policy)
        case = _build_case(scenario)
        raw = _valid_output(scenario)

        decision, err = pipeline.run.__wrapped__(raw, case) if hasattr(pipeline.run, "__wrapped__") else None, None
        import asyncio
        decision, err = asyncio.run(pipeline.run(raw, case))

        assert err is None, f"Case {scenario['case_id']} failed: {err}"
        assert decision is not None
        assert decision.action == scenario.get("expected_decision", "approve")
        assert decision.case_id == scenario["case_id"]


class TestRegressionEdgeCases:
    def test_edge_cases_exist(self):
        path = SCENARIOS_DIR / "edge_cases" / "urban_v1.0.json"
        assert path.exists()
        cases = _load_json(path)
        assert len(cases) >= 1

    @pytest.mark.parametrize(
        "scenario",
        _load_json(SCENARIOS_DIR / "edge_cases" / "urban_v1.0.json"),
        ids=lambda s: s["case_id"],
    )
    def test_edge_case_has_valid_response(self, scenario: dict):
        import asyncio

        policy = DOMAIN_POLICIES.get(scenario["domain"], UrbanPolicy)()
        pipeline = ReliabilityPipeline(policy)
        case = _build_case(scenario)
        raw = _valid_output(scenario)

        decision, err = asyncio.run(pipeline.run(raw, case))

        assert decision is not None or err is not None


class TestRegressionFailureCases:
    def test_failure_cases_exist(self):
        path = SCENARIOS_DIR / "failure_cases" / "urban_v1.0.json"
        assert path.exists()
        cases = _load_json(path)
        assert len(cases) >= 1

    @pytest.mark.parametrize(
        "scenario",
        _load_json(SCENARIOS_DIR / "failure_cases" / "urban_v1.0.json"),
        ids=lambda s: s["case_id"],
    )
    def test_failure_case_produces_error(self, scenario: dict):
        import asyncio

        policy = UrbanPolicy()
        pipeline = ReliabilityPipeline(policy)
        case = _build_case(scenario)
        raw = scenario.get("mock_response", "invalid")

        decision, err = asyncio.run(pipeline.run(raw, case))

        assert decision is None
        assert err is not None
        assert err.category.value == scenario.get("expected_error_category", "parsing")


class TestRegressionInjectionCases:
    def test_injection_cases_exist(self):
        path = SCENARIOS_DIR / "injection_cases" / "urban_v1.0.json"
        assert path.exists()
        cases = _load_json(path)
        assert len(cases) >= 1

    def test_injection_does_not_modify_system_prompt(self):
        from case_core.prompts.builder import PromptBuilder

        path = SCENARIOS_DIR / "injection_cases" / "urban_v1.0.json"
        cases = _load_json(path)
        builder = PromptBuilder(domain_policy=UrbanPolicy())

        for scenario in cases:
            case = _build_case(scenario)
            request = builder.build(case)

            system_msg = request.messages[0]
            assert system_msg["role"] == "system"
            assert "CASE" in system_msg["content"]
            assert "pirate" not in system_msg["content"].lower()
            assert "HACKED" not in system_msg["content"]


class TestRegressionBiasPairs:
    def test_bias_pairs_exist(self):
        path = SCENARIOS_DIR / "bias_pairs" / "urban_v1.0.json"
        assert path.exists()
        pairs = _load_json(path)
        assert len(pairs) >= 1

    def test_paired_cases_differ_only_in_attribute(self):
        path = SCENARIOS_DIR / "bias_pairs" / "urban_v1.0.json"
        pairs = _load_json(path)

        for pair in pairs:
            case_a = _build_case(pair["case_a"])
            case_b = _build_case(pair["case_b"])

            assert case_a.domain == case_b.domain
            assert case_a.urgency == case_b.urgency
            assert case_a.report_text != case_b.report_text

    def test_paired_cases_same_urgency_classification(self):
        path = SCENARIOS_DIR / "bias_pairs" / "urban_v1.0.json"
        pairs = _load_json(path)
        policy = UrbanPolicy()

        for pair in pairs:
            case_a = _build_case(pair["case_a"])
            case_b = _build_case(pair["case_b"])

            urgency_a = policy.classify_urgency(case_a)
            urgency_b = policy.classify_urgency(case_b)

            assert urgency_a == urgency_b, (
                f"Pair {pair['pair_id']}: urgency mismatch "
                f"({urgency_a} vs {urgency_b})"
            )
