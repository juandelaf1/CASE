import json
from pathlib import Path
from typing import Any

from case_core.evaluation.metrics.calculator import compute_all_metrics
from case_core.evaluation.runner.results import EvaluationRun


class ReportGenerator:
    def generate(self, run: EvaluationRun) -> dict[str, Any]:
        metrics = compute_all_metrics(run)

        decisions: dict[str, int] = {}
        for r in run.results:
            key = f"{r.expected_decision}_as_{r.actual_decision}"
            decisions[key] = decisions.get(key, 0) + 1

        return {
            "summary": {
                "dataset": run.dataset_name,
                "version": run.dataset_version,
                "provider": run.provider,
                "model": run.model,
                "total_cases": run.total_cases,
                "successful_cases": run.successful_cases,
                "failed_cases": run.failed_cases,
            },
            "metrics": metrics,
            "decision_distribution": decisions,
            "results": [
                {
                    "case_id": r.case_id,
                    "expected": r.expected_decision,
                    "actual": r.actual_decision,
                    "correct": r.correct_decision,
                    "confidence": r.confidence,
                    "error": r.error,
                }
                for r in run.results
            ],
        }

    def save_report(self, run: EvaluationRun, path: str | Path) -> dict[str, Any]:
        report = self.generate(run)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(report, f, indent=2)
        return report
