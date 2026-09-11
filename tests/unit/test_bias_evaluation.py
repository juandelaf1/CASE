from case_core.evaluation.metrics.bias import (
    BiasEvaluator,
    BiasPairItem,
    calculate_pair_consistency_rate,
    calculate_decision_invariance_rate,
    calculate_classification_invariance,
    calculate_urgency_invariance,
    calculate_routing_invariance,
    calculate_recommendation_invariance,
    calculate_automation_invariance,
    calculate_hitl_consistency,
)

import pytest

class TestBS030_BiasEvaluation:
    @pytest.fixture
    def sample_results(self):
        return [
            {
                "invariance": "INVARIANT",
                "decision_invariance": True,
                "classification_change": False,
                "urgency_change": False,
                "routing_change": False,
                "recommendation_change": False,
                "automation_change": False,
                "hitl_change": False,
            },
            {
                "invariance": "JUSTIFIED_DIFFERENCE",
                "decision_invariance": False,
                "classification_change": True,
                "urgency_change": True,
                "routing_change": False,
                "recommendation_change": False,
                "automation_change": False,
                "hitl_change": False,
            },
            {
                "invariance": "POTENTIAL_CONCERN",
                "decision_invariance": False,
                "classification_change": False,
                "urgency_change": False,
                "routing_change": True,
                "recommendation_change": True,
                "automation_change": False,
                "hitl_change": False,
            },
        ]

    def test_pair_consistency_rate(self, sample_results):
        rate = calculate_pair_consistency_rate(sample_results)
        assert rate == 1/3

    def test_decision_invariance_rate(self, sample_results):
        rate = calculate_decision_invariance_rate(sample_results)
        assert rate == 1/3

    def test_classification_invariance(self, sample_results):
        rate = calculate_classification_invariance(sample_results)
        assert rate == 2/3

    def test_urgency_invariance(self, sample_results):
        rate = calculate_urgency_invariance(sample_results)
        assert rate == 2/3

    def test_routing_invariance(self, sample_results):
        rate = calculate_routing_invariance(sample_results)
        assert rate == 2/3

    def test_recommendation_invariance(self, sample_results):
        rate = calculate_recommendation_invariance(sample_results)
        assert rate == 2/3

    def test_automation_invariance(self, sample_results):
        rate = calculate_automation_invariance(sample_results)
        assert rate == 1

    def test_hitl_consistency(self, sample_results):
        rate = calculate_hitl_consistency(sample_results)
        assert rate == 1


class TestBiasEvaluatorRoutingVsDecision:
    """Tests that routing_invariance_rate and decision_invariance_rate are independent."""

    def _make_pair(self, pair_id: str = "PAIR-001") -> BiasPairItem:
        return BiasPairItem(
            pair_id=pair_id,
            domain="logistics",
            changed_attribute="route_name",
            expected_invariance="decision_and_urgency",
            expected_decision="approve",
            rationale="Route name should not affect decision",
            case_a={"case_id": f"{pair_id}-A", "report_text": "Test", "domain": "logistics", "urgency": "MEDIUM", "evidence": []},
            case_b={"case_id": f"{pair_id}-B", "report_text": "Test", "domain": "logistics", "urgency": "MEDIUM", "evidence": []},
        )

    def test_routing_changes_but_decision_same(self):
        """Routing changes but decision stays the same: decision=1.0, routing=0.0."""
        evaluator = BiasEvaluator()
        pair = self._make_pair()
        result = evaluator.evaluate_pair(
            pair,
            decision_a="approve", decision_b="approve",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
            routing_consistent=False,
        )
        assert result.decision_consistent is True
        assert result.routing_consistent is False

        results = evaluator.compute_results([result])
        assert results.decision_invariance_rate == 1.0
        assert results.routing_invariance_rate == 0.0

    def test_decision_changes_but_routing_same(self):
        """Decision changes but routing stays the same: decision=0.0, routing=1.0."""
        evaluator = BiasEvaluator()
        pair = self._make_pair()
        result = evaluator.evaluate_pair(
            pair,
            decision_a="approve", decision_b="reject",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
            routing_consistent=True,
        )
        assert result.decision_consistent is False
        assert result.routing_consistent is True

        results = evaluator.compute_results([result])
        assert results.decision_invariance_rate == 0.0
        assert results.routing_invariance_rate == 1.0

    def test_both_change(self):
        """Both routing and decision change: both=0.0."""
        evaluator = BiasEvaluator()
        pair = self._make_pair()
        result = evaluator.evaluate_pair(
            pair,
            decision_a="approve", decision_b="reject",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
            routing_consistent=False,
        )
        assert result.decision_consistent is False
        assert result.routing_consistent is False

        results = evaluator.compute_results([result])
        assert results.decision_invariance_rate == 0.0
        assert results.routing_invariance_rate == 0.0

    def test_neither_changes(self):
        """Neither changes: both=1.0."""
        evaluator = BiasEvaluator()
        pair = self._make_pair()
        result = evaluator.evaluate_pair(
            pair,
            decision_a="approve", decision_b="approve",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
            routing_consistent=True,
        )
        assert result.decision_consistent is True
        assert result.routing_consistent is True

        results = evaluator.compute_results([result])
        assert results.decision_invariance_rate == 1.0
        assert results.routing_invariance_rate == 1.0

    def test_default_routing_consistent_is_true(self):
        """When routing_consistent is not passed, defaults to True."""
        evaluator = BiasEvaluator()
        pair = self._make_pair()
        result = evaluator.evaluate_pair(
            pair,
            decision_a="approve", decision_b="approve",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
        )
        assert result.routing_consistent is True

    def test_mixed_pairs_distinct_rates(self):
        """Multiple pairs where routing and decision diverge."""
        evaluator = BiasEvaluator()
        pair1 = self._make_pair("PAIR-001")
        pair2 = self._make_pair("PAIR-002")

        r1 = evaluator.evaluate_pair(
            pair1,
            decision_a="approve", decision_b="approve",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
            routing_consistent=False,
        )
        r2 = evaluator.evaluate_pair(
            pair2,
            decision_a="approve", decision_b="reject",
            urgency_a="MEDIUM", urgency_b="MEDIUM",
            confidence_a=0.8, confidence_b=0.8,
            routing_consistent=True,
        )

        results = evaluator.compute_results([r1, r2])
        assert results.decision_invariance_rate == 0.5
        assert results.routing_invariance_rate == 0.5
