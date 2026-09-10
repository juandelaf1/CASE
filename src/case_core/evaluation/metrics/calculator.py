from case_core.evaluation.runner.results import EvaluationRun


def compute_decision_accuracy(run: EvaluationRun) -> float:
    if not run.results:
        return 0.0
    return sum(1 for r in run.results if r.correct_decision) / len(run.results)


def compute_urgency_accuracy(run: EvaluationRun) -> float:
    if not run.results:
        return 0.0
    return sum(1 for r in run.results if r.correct_urgency) / len(run.results)


def compute_avg_confidence(run: EvaluationRun) -> float:
    if not run.results:
        return 0.0
    return sum(r.confidence for r in run.results) / len(run.results)


def compute_avg_processing_time(run: EvaluationRun) -> float:
    if not run.results:
        return 0.0
    return sum(r.processing_time_ms for r in run.results) / len(run.results)


def compute_error_rate(run: EvaluationRun) -> float:
    if not run.results:
        return 0.0
    return sum(1 for r in run.results if r.error is not None) / len(run.results)


def compute_precision_recall(
    run: EvaluationRun,
    target_decision: str,
) -> tuple[float, float]:
    tp = sum(1 for r in run.results if r.actual_decision == target_decision and r.correct_decision)
    fp = sum(1 for r in run.results if r.actual_decision == target_decision and not r.correct_decision)
    fn = sum(1 for r in run.results if r.actual_decision != target_decision and r.expected_decision == target_decision)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return precision, recall


def compute_all_metrics(run: EvaluationRun) -> dict:
    return {
        "decision_accuracy": compute_decision_accuracy(run),
        "urgency_accuracy": compute_urgency_accuracy(run),
        "avg_confidence": compute_avg_confidence(run),
        "avg_processing_time_ms": compute_avg_processing_time(run),
        "error_rate": compute_error_rate(run),
        "total_cases": run.total_cases,
        "successful_cases": run.successful_cases,
        "failed_cases": run.failed_cases,
    }
