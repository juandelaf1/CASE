"""Model evaluation framework — Phase 3.8."""

from __future__ import annotations

from typing import Any

from case_core.ml.dataset_contracts import DatasetSplit, TrainingDataset
from case_core.ml.training_abstraction import EvaluationRunner, ModelAdapter


class DeterministicEvaluationRunner(EvaluationRunner):
    """Deterministic evaluation for model comparison."""

    def evaluate_accuracy(self, adapter: ModelAdapter, dataset: TrainingDataset) -> float:
        test_examples = dataset.get_split(DatasetSplit.TEST)
        if not test_examples:
            return 0.0
        correct = 0
        total = len(test_examples)
        for example in test_examples:
            prediction = adapter.predict(example.input_text)
            if self._semantic_match(prediction, example.target_output):
                correct += 1
        return correct / total if total > 0 else 0.0

    def evaluate_safety(
        self, adapter: ModelAdapter, test_cases: list[dict[str, Any]]
    ) -> dict[str, Any]:
        results = []
        for case in test_cases:
            input_text = case.get("input", "")
            expected禁忌 = case.get("forbidden_output", "")
            prediction = adapter.predict(input_text)
            is_safe = expected禁忌 not in prediction if expected禁忌 else True
            results.append({
                "input": input_text,
                "prediction": prediction,
                "expected_forbidden": expected禁忌,
                "is_safe": is_safe,
            })
        safe_count = sum(1 for r in results if r["is_safe"])
        return {
            "total": len(results),
            "safe": safe_count,
            "unsafe": len(results) - safe_count,
            "safety_rate": safe_count / len(results) if results else 1.0,
            "details": results,
        }

    def evaluate_domain_validity(self, adapter: ModelAdapter, dataset: TrainingDataset) -> float:
        test_examples = dataset.get_split(DatasetSplit.TEST)
        if not test_examples:
            return 0.0
        valid = 0
        total = len(test_examples)
        for example in test_examples:
            prediction = adapter.predict(example.input_text)
            if self._is_domain_valid(prediction, dataset.domain.value):
                valid += 1
        return valid / total if total > 0 else 0.0

    def compare_with_baseline(
        self, adapted_adapter: ModelAdapter, baseline_adapter: ModelAdapter, dataset: TrainingDataset
    ) -> dict[str, Any]:
        adapted_accuracy = self.evaluate_accuracy(adapted_adapter, dataset)
        baseline_accuracy = self.evaluate_accuracy(baseline_adapter, dataset)
        adapted_domain = self.evaluate_domain_validity(adapted_adapter, dataset)
        baseline_domain = self.evaluate_domain_validity(baseline_adapter, dataset)
        return {
            "adapted_accuracy": adapted_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "accuracy_delta": adapted_accuracy - baseline_accuracy,
            "adapted_domain_validity": adapted_domain,
            "baseline_domain_validity": baseline_domain,
            "domain_validity_delta": adapted_domain - baseline_domain,
            "improvement": adapted_accuracy > baseline_accuracy,
            "regression": adapted_accuracy < baseline_accuracy,
        }

    def _semantic_match(self, prediction: str, target: str) -> bool:
        pred_lower = prediction.strip().lower()
        target_lower = target.strip().lower()
        if pred_lower == target_lower:
            return True
        if target_lower in pred_lower or pred_lower in target_lower:
            return True
        pred_words = set(pred_lower.split())
        target_words = set(target_lower.split())
        if not target_words:
            return False
        overlap = len(pred_words & target_words) / len(target_words)
        return overlap >= 0.5

    def _is_domain_valid(self, output: str, domain: str) -> bool:
        domain_keywords = {
            "logistics": ["shipment", "carrier", "route", "delivery", "transport", "freight"],
            "urban": ["incident", "city", "urban", "municipal", "public"],
            "infrastructure": ["infrastructure", "bridge", "road", "utility", "maintenance"],
        }
        keywords = domain_keywords.get(domain, [])
        output_lower = output.lower()
        return any(kw in output_lower for kw in keywords) or len(keywords) == 0

    def generate_regression_report(
        self, adapted_adapter: ModelAdapter, baseline_adapter: ModelAdapter, dataset: TrainingDataset
    ) -> dict[str, Any]:
        comparison = self.compare_with_baseline(adapted_adapter, baseline_adapter, dataset)
        test_examples = dataset.get_split(DatasetSplit.TEST)
        detailed_results = []
        for example in test_examples:
            adapted_pred = adapted_adapter.predict(example.input_text)
            baseline_pred = baseline_adapter.predict(example.input_text)
            adapted_match = self._semantic_match(adapted_pred, example.target_output)
            baseline_match = self._semantic_match(baseline_pred, example.target_output)
            detailed_results.append({
                "input": example.input_text,
                "target": example.target_output,
                "adapted_prediction": adapted_pred,
                "baseline_prediction": baseline_pred,
                "adapted_correct": adapted_match,
                "baseline_correct": baseline_match,
                "regression": not adapted_match and baseline_match,
                "improvement": adapted_match and not baseline_match,
            })
        regressions = [r for r in detailed_results if r["regression"]]
        improvements = [r for r in detailed_results if r["improvement"]]
        return {
            "summary": comparison,
            "total_test_cases": len(test_examples),
            "regressions": len(regressions),
            "improvements": len(improvements),
            "regression_details": regressions,
            "improvement_details": improvements,
        }
