from case_core.evaluation.metrics.bias import (
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
