import os
import sys

import pytest

sys.path.insert(0, "src")

from case_core.domain.registry import DomainRegistry
from case_core.domain.urban_policy import UrbanPolicy
from case_core.evaluation.datasets.loader import Dataset, DatasetItem, DatasetLoader
from case_core.evaluation.metrics.calculator import (
    compute_all_metrics,
    compute_avg_confidence,
    compute_avg_processing_time,
    compute_decision_accuracy,
    compute_error_rate,
    compute_urgency_accuracy,
)
from case_core.evaluation.reports.generator import ReportGenerator
from case_core.evaluation.runner.results import EvaluationResult, EvaluationRun
from case_core.evaluation.runner.runner import EvaluationRunner
from case_core.providers.mock import MockProvider
from case_core.reliability.pipeline import ReliabilityPipeline

TEST_DATASET_PATH = "test_dataset.json"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists(TEST_DATASET_PATH):
        os.remove(TEST_DATASET_PATH)


def _make_dataset() -> Dataset:
    return Dataset(
        name="test-dataset",
        version="1.0.0",
        description="Test dataset for evaluation",
        items=[
            DatasetItem(
                case_id="eval-001",
                report_text="Falla en farola",
                domain="urban_operations",
                expected_decision="approve",
                expected_urgency="MEDIUM",
                evidence=[{"id": "ev-001", "type": "text", "content": "test", "source": "test", "confidence": 0.9, "extracted_at": "2026-09-08T12:00:00Z"}],
            ),
            DatasetItem(
                case_id="eval-002",
                report_text="Emergency in downtown",
                domain="urban_operations",
                expected_decision="escalate",
                expected_urgency="HIGH",
                evidence=[{"id": "ev-002", "type": "text", "content": "emergency", "source": "test", "confidence": 0.95, "extracted_at": "2026-09-08T12:00:00Z"}],
            ),
        ],
    )


def _make_run() -> EvaluationRun:
    return EvaluationRun(
        dataset_name="test",
        dataset_version="1.0.0",
        provider="mock",
        model="mock-v1",
        results=[
            EvaluationResult(
                case_id="eval-001",
                expected_decision="approve",
                actual_decision="approve",
                expected_urgency="MEDIUM",
                actual_urgency="MEDIUM",
                confidence=0.85,
                correct_decision=True,
                correct_urgency=True,
                processing_time_ms=1.0,
                provider="mock",
                model="mock-v1",
            ),
            EvaluationResult(
                case_id="eval-002",
                expected_decision="escalate",
                actual_decision="reject",
                expected_urgency="HIGH",
                actual_urgency="LOW",
                confidence=0.70,
                correct_decision=False,
                correct_urgency=False,
                processing_time_ms=2.0,
                provider="mock",
                model="mock-v1",
            ),
        ],
        total_cases=2,
        successful_cases=2,
        failed_cases=0,
    )


class TestDatasetLoader:
    def test_load_from_dict(self):
        loader = DatasetLoader()
        data = {
            "name": "test",
            "version": "1.0.0",
            "items": [
                {
                    "case_id": "c1",
                    "report_text": "test",
                    "domain": "urban_operations",
                    "expected_decision": "approve",
                    "expected_urgency": "LOW",
                }
            ],
        }
        dataset = loader.load_from_dict(data)
        assert dataset.name == "test"
        assert len(dataset.items) == 1

    def test_save_and_load_file(self):
        loader = DatasetLoader()
        dataset = _make_dataset()
        loader.save_to_file(dataset, TEST_DATASET_PATH)
        loaded = loader.load_from_file(TEST_DATASET_PATH)
        assert loaded.name == "test-dataset"
        assert loaded.version == "1.0.0"
        assert len(loaded.items) == 2

    def test_load_nonexistent_raises(self):
        loader = DatasetLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_from_file("nonexistent.json")


class TestMetrics:
    def test_decision_accuracy(self):
        run = _make_run()
        assert compute_decision_accuracy(run) == 0.5

    def test_urgency_accuracy(self):
        run = _make_run()
        assert compute_urgency_accuracy(run) == 0.5

    def test_avg_confidence(self):
        run = _make_run()
        assert abs(compute_avg_confidence(run) - 0.775) < 0.001

    def test_avg_processing_time(self):
        run = _make_run()
        assert compute_avg_processing_time(run) == 1.5

    def test_error_rate(self):
        run = _make_run()
        assert compute_error_rate(run) == 0.0

    def test_error_rate_with_errors(self):
        run = _make_run()
        run.results[0].error = "test error"
        assert compute_error_rate(run) == 0.5

    def test_compute_all_metrics(self):
        run = _make_run()
        metrics = compute_all_metrics(run)
        assert "decision_accuracy" in metrics
        assert "urgency_accuracy" in metrics
        assert "avg_confidence" in metrics
        assert "error_rate" in metrics

    def test_empty_run_metrics(self):
        run = EvaluationRun(
            dataset_name="empty",
            dataset_version="0.0.0",
            provider="mock",
            model="mock-v1",
        )
        assert compute_decision_accuracy(run) == 0.0
        assert compute_error_rate(run) == 0.0


class TestReportGenerator:
    def test_generate_report(self):
        run = _make_run()
        gen = ReportGenerator()
        report = gen.generate(run)
        assert "summary" in report
        assert "metrics" in report
        assert "results" in report
        assert report["summary"]["total_cases"] == 2

    def test_save_report(self):
        run = _make_run()
        gen = ReportGenerator()
        gen.save_report(run, "test_report.json")
        assert os.path.exists("test_report.json")
        os.remove("test_report.json")


class TestEvaluationRunner:
    @pytest.mark.asyncio
    async def test_run_single_case(self):
        provider = MockProvider()
        runner = EvaluationRunner(provider)
        registry = DomainRegistry()
        registry.register(UrbanPolicy())
        pipeline = ReliabilityPipeline(UrbanPolicy())

        item = DatasetItem(
            case_id="eval-001",
            report_text="[TEST-MOCK-01] Standard case",
            domain="urban_operations",
            expected_decision="approve",
            expected_urgency="MEDIUM",
            evidence=[{"id": "ev-001", "type": "text", "content": "test", "source": "test", "confidence": 0.9, "extracted_at": "2026-09-08T12:00:00Z"}],
        )

        result = await runner.run_single(item, pipeline, UrbanPolicy())
        assert result.case_id == "eval-001"
        assert result.correct_decision is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_dataset(self):
        provider = MockProvider()
        runner = EvaluationRunner(provider)
        registry = DomainRegistry()
        registry.register(UrbanPolicy())
        pipeline = ReliabilityPipeline(UrbanPolicy())

        dataset = _make_dataset()
        dataset.items[0].report_text = "[TEST-MOCK-01] Standard case"
        dataset.items[1].report_text = "[TEST-MOCK-03] High urgency case"

        eval_run = await runner.run_dataset(dataset, pipeline, registry)
        assert eval_run.total_cases == 2
        assert eval_run.provider == "mock"
