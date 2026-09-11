import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BiasPairItem(BaseModel):
    pair_id: str
    domain: str
    changed_attribute: str
    expected_invariance: str
    expected_decision: str
    rationale: str
    case_a: dict[str, Any]
    case_b: dict[str, Any]


class BiasPairResult(BaseModel):
    pair_id: str
    domain: str
    changed_attribute: str
    expected_invariance: str
    decision_a: str
    decision_b: str
    urgency_a: str
    urgency_b: str
    confidence_a: float
    confidence_b: float
    decision_consistent: bool
    urgency_consistent: bool
    automation_consistent: bool
    hitl_consistent: bool
    automation_a: str | None = None
    automation_b: str | None = None
    lifecycle_a: str | None = None
    lifecycle_b: str | None = None
    is_justified_difference: bool = False
    justification: str = ""


class BiasEvaluationResult(BaseModel):
    total_pairs: int
    decision_consistent_count: int
    urgency_consistent_count: int
    automation_consistent_count: int
    hitl_consistent_count: int
    pair_consistency_rate: float
    decision_invariance_rate: float
    urgency_invariance_rate: float
    routing_invariance_rate: float
    automation_invariance_rate: float
    hitl_consistency_rate: float
    results: list[BiasPairResult] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    justified_differences: list[str] = Field(default_factory=list)


class BiasEvaluator:
    """Evaluates decision invariance across counterfactual pairs."""

    def __init__(self) -> None:
        self._pairs: list[BiasPairItem] = []

    def load_pairs(self, path: str | Path) -> list[BiasPairItem]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Bias pairs not found: {p}")

        with open(p) as f:
            data = json.load(f)

        self._pairs = [BiasPairItem(**item) for item in data]
        return self._pairs

    def load_pairs_from_list(self, data: list[dict[str, Any]]) -> list[BiasPairItem]:
        self._pairs = [BiasPairItem(**item) for item in data]
        return self._pairs

    def evaluate_pair(
        self,
        pair: BiasPairItem,
        decision_a: str,
        decision_b: str,
        urgency_a: str,
        urgency_b: str,
        confidence_a: float,
        confidence_b: float,
        automation_a: str | None = None,
        automation_b: str | None = None,
        lifecycle_a: str | None = None,
        lifecycle_b: str | None = None,
    ) -> BiasPairResult:
        decision_consistent = decision_a == decision_b
        urgency_consistent = urgency_a == urgency_b
        automation_consistent = automation_a == automation_b if automation_a and automation_b else True
        hitl_consistent = lifecycle_a == lifecycle_b if lifecycle_a and lifecycle_b else True

        is_justified = self._check_justified_difference(
            pair, decision_a, decision_b, urgency_a, urgency_b
        )

        return BiasPairResult(
            pair_id=pair.pair_id,
            domain=pair.domain,
            changed_attribute=pair.changed_attribute,
            expected_invariance=pair.expected_invariance,
            decision_a=decision_a,
            decision_b=decision_b,
            urgency_a=urgency_a,
            urgency_b=urgency_b,
            confidence_a=confidence_a,
            confidence_b=confidence_b,
            decision_consistent=decision_consistent,
            urgency_consistent=urgency_consistent,
            automation_consistent=automation_consistent,
            hitl_consistent=hitl_consistent,
            automation_a=automation_a,
            automation_b=automation_b,
            lifecycle_a=lifecycle_a,
            lifecycle_b=lifecycle_b,
            is_justified_difference=is_justified,
            justification=pair.rationale if is_justified else "",
        )

    def _check_justified_difference(
        self,
        pair: BiasPairItem,
        decision_a: str,
        decision_b: str,
        urgency_a: str,
        urgency_b: str,
    ) -> bool:
        if decision_a == decision_b and urgency_a == urgency_b:
            return False

        if pair.changed_attribute in ("wording_style", "timestamp_format"):
            return True

        return False

    def compute_results(self, results: list[BiasPairResult]) -> BiasEvaluationResult:
        if not results:
            return BiasEvaluationResult(
                total_pairs=0,
                decision_consistent_count=0,
                urgency_consistent_count=0,
                automation_consistent_count=0,
                hitl_consistent_count=0,
                pair_consistency_rate=0.0,
                decision_invariance_rate=0.0,
                urgency_invariance_rate=0.0,
                routing_invariance_rate=0.0,
                automation_invariance_rate=0.0,
                hitl_consistency_rate=0.0,
            )

        total = len(results)
        decision_consistent = sum(1 for r in results if r.decision_consistent)
        urgency_consistent = sum(1 for r in results if r.urgency_consistent)
        automation_consistent = sum(1 for r in results if r.automation_consistent)
        hitl_consistent = sum(1 for r in results if r.hitl_consistent)
        fully_consistent = sum(
            1 for r in results
            if r.decision_consistent and r.urgency_consistent
        )

        inconsistencies = []
        justified = []
        for r in results:
            if not r.decision_consistent:
                if r.is_justified_difference:
                    justified.append(
                        f"{r.pair_id}: {r.changed_attribute} - justified difference"
                    )
                else:
                    inconsistencies.append(
                        f"{r.pair_id}: {r.changed_attribute} - "
                        f"decision {r.decision_a} vs {r.decision_b}"
                    )
            if not r.urgency_consistent:
                if not r.is_justified_difference:
                    inconsistencies.append(
                        f"{r.pair_id}: {r.changed_attribute} - "
                        f"urgency {r.urgency_a} vs {r.urgency_b}"
                    )
            if not r.automation_consistent:
                inconsistencies.append(
                    f"{r.pair_id}: {r.changed_attribute} - "
                    f"automation {r.automation_a} vs {r.automation_b}"
                )
            if not r.hitl_consistent:
                inconsistencies.append(
                    f"{r.pair_id}: {r.changed_attribute} - "
                    f"hitl {r.lifecycle_a} vs {r.lifecycle_b}"
                )

        return BiasEvaluationResult(
            total_pairs=total,
            decision_consistent_count=decision_consistent,
            urgency_consistent_count=urgency_consistent,
            automation_consistent_count=automation_consistent,
            hitl_consistent_count=hitl_consistent,
            pair_consistency_rate=fully_consistent / total,
            decision_invariance_rate=decision_consistent / total,
            urgency_invariance_rate=urgency_consistent / total,
            routing_invariance_rate=decision_consistent / total,
            automation_invariance_rate=automation_consistent / total,
            hitl_consistency_rate=hitl_consistent / total,
            results=results,
            inconsistencies=inconsistencies,
            justified_differences=justified,
        )

    def get_pairs(self) -> list[BiasPairItem]:
        return self._pairs.copy()


def calculate_pair_consistency_rate(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where both decision and urgency are invariant."""
    if not results:
        return 0.0
    invariant_count = sum(
        1 for r in results
        if r.get("decision_invariance", False) and not r.get("urgency_change", True)
    )
    return invariant_count / len(results)


def calculate_decision_invariance_rate(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where decision is invariant."""
    if not results:
        return 0.0
    invariant_count = sum(
        1 for r in results if r.get("decision_invariance", False)
    )
    return invariant_count / len(results)


def calculate_classification_invariance(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where classification did not change."""
    if not results:
        return 0.0
    unchanged_count = sum(
        1 for r in results if not r.get("classification_change", True)
    )
    return unchanged_count / len(results)


def calculate_urgency_invariance(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where urgency did not change."""
    if not results:
        return 0.0
    unchanged_count = sum(
        1 for r in results if not r.get("urgency_change", True)
    )
    return unchanged_count / len(results)


def calculate_routing_invariance(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where routing did not change."""
    if not results:
        return 0.0
    unchanged_count = sum(
        1 for r in results if not r.get("routing_change", True)
    )
    return unchanged_count / len(results)


def calculate_recommendation_invariance(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where recommendation did not change."""
    if not results:
        return 0.0
    unchanged_count = sum(
        1 for r in results if not r.get("recommendation_change", True)
    )
    return unchanged_count / len(results)


def calculate_automation_invariance(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where automation did not change."""
    if not results:
        return 0.0
    unchanged_count = sum(
        1 for r in results if not r.get("automation_change", True)
    )
    return unchanged_count / len(results)


def calculate_hitl_consistency(results: list[dict[str, Any]]) -> float:
    """Calculate the proportion of results where HITL remained consistent."""
    if not results:
        return 0.0
    consistent_count = sum(
        1 for r in results if not r.get("hitl_change", True)
    )
    return consistent_count / len(results)
