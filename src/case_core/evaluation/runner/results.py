from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    case_id: str
    expected_decision: str
    actual_decision: str
    expected_urgency: str
    actual_urgency: str
    confidence: float
    correct_decision: bool
    correct_urgency: bool
    processing_time_ms: float
    provider: str
    model: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationRun:
    dataset_name: str
    dataset_version: str
    provider: str
    model: str
    results: list[EvaluationResult] = field(default_factory=list)
    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    avg_processing_time_ms: float = 0.0
    decision_accuracy: float = 0.0
    urgency_accuracy: float = 0.0
