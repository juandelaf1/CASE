"""Tests for ML Adaptation — Phase 3."""

import tempfile
from pathlib import Path

import pytest

from case_core.ml.adapters import MockAdapter, NullAdapter, NullInferenceEngine
from case_core.ml.dataset_contracts import (
    DatasetDomain,
    DatasetSplit,
    Provenance,
    TrainingDataset,
    TrainingExample,
)
from case_core.ml.dataset_pipeline import DeterministicDatasetPipeline
from case_core.ml.evaluation import DeterministicEvaluationRunner
from case_core.ml.evaluation_dataset import EvaluationDatasetGenerator
from case_core.ml.lora_config import AdaptationMethod, LoRAConfig, TrainingConfig
from case_core.ml.training_abstraction import (
    ModelAdapter,
)


class TestDatasetContracts:
    def test_training_example_creation(self):
        example = TrainingExample(
            input_text="test input",
            target_output="test output",
            domain=DatasetDomain.LOGISTICS,
        )
        assert example.input_text == "test input"
        assert example.target_output == "test output"
        assert example.domain == DatasetDomain.LOGISTICS

    def test_training_dataset_size(self):
        dataset = TrainingDataset(
            dataset_id="test",
            name="Test",
            domain=DatasetDomain.GENERAL,
        )
        assert dataset.size == 0
        dataset.add_example(
            TrainingExample(input_text="a", target_output="b")
        )
        assert dataset.size == 1

    def test_dataset_split(self):
        dataset = TrainingDataset(
            dataset_id="test",
            name="Test",
            domain=DatasetDomain.GENERAL,
        )
        dataset.add_example(
            TrainingExample(input_text="a", target_output="b", split=DatasetSplit.TRAIN)
        )
        dataset.add_example(
            TrainingExample(input_text="c", target_output="d", split=DatasetSplit.TEST)
        )
        train = dataset.get_split(DatasetSplit.TRAIN)
        test = dataset.get_split(DatasetSplit.TEST)
        assert len(train) == 1
        assert len(test) == 1

    def test_quality_filter(self):
        dataset = TrainingDataset(
            dataset_id="test",
            name="Test",
            domain=DatasetDomain.GENERAL,
        )
        dataset.add_example(
            TrainingExample(input_text="a", target_output="b", quality_score=0.9)
        )
        dataset.add_example(
            TrainingExample(input_text="c", target_output="d", quality_score=0.3)
        )
        high_quality = dataset.validate_quality(min_quality=0.5)
        assert len(high_quality) == 1

    def test_provenance(self):
        provenance = Provenance(source="test", version="1.0")
        assert provenance.source == "test"
        assert provenance.version == "1.0"


class TestDatasetPipeline:
    def test_prepare_dataset(self):
        pipeline = DeterministicDatasetPipeline(seed=42)
        raw_data = [
            {"input": "test1", "target": "output1"},
            {"input": "test2", "target": "output2"},
        ]
        config = {"domain": "logistics", "dataset_id": "test_dataset"}
        dataset = pipeline.prepare_dataset(raw_data, config)
        assert dataset.size == 2
        assert dataset.domain == DatasetDomain.LOGISTICS

    def test_split_dataset(self):
        pipeline = DeterministicDatasetPipeline(seed=42)
        raw_data = [{"input": f"test{i}", "target": f"output{i}"} for i in range(100)]
        config = {
            "domain": "logistics",
            "train_split_ratio": 0.8,
            "validation_split_ratio": 0.1,
            "test_split_ratio": 0.1,
        }
        dataset = pipeline.prepare_dataset(raw_data, config)
        train = dataset.get_split(DatasetSplit.TRAIN)
        val = dataset.get_split(DatasetSplit.VALIDATION)
        test = dataset.get_split(DatasetSplit.TEST)
        assert len(train) == 80
        assert len(val) == 10
        assert len(test) == 10

    def test_save_and_load_dataset(self):
        pipeline = DeterministicDatasetPipeline(seed=42)
        raw_data = [{"input": "test", "target": "output"}]
        config = {"domain": "logistics", "dataset_id": "test_save"}
        dataset = pipeline.prepare_dataset(raw_data, config)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dataset.json"
            pipeline.save_dataset(dataset, str(path))
            loaded = pipeline.load_dataset(str(path))
            assert loaded.dataset_id == dataset.dataset_id
            assert loaded.size == dataset.size

    def test_compute_checksum(self):
        pipeline = DeterministicDatasetPipeline(seed=42)
        raw_data = [{"input": "test", "target": "output"}]
        config = {"domain": "logistics", "dataset_id": "test_checksum"}
        dataset = pipeline.prepare_dataset(raw_data, config)
        checksum = pipeline.compute_checksum(dataset)
        assert isinstance(checksum, str)
        assert len(checksum) == 64

    def test_create_version(self):
        pipeline = DeterministicDatasetPipeline(seed=42)
        raw_data = [{"input": "test", "target": "output"}]
        config = {"domain": "logistics", "dataset_id": "test_version"}
        dataset = pipeline.prepare_dataset(raw_data, config)
        version = pipeline.create_version(dataset, ["Initial creation"])
        assert version.version == dataset.version
        assert len(version.changes) == 1


class TestAdapters:
    def test_mock_adapter(self):
        adapter = MockAdapter()
        adapter.load()
        prediction = adapter.predict("test input")
        assert "Mock prediction" in prediction

    def test_null_adapter(self):
        adapter = NullAdapter()
        adapter.load()
        prediction = adapter.predict("test input")
        assert prediction == ""

    def test_null_inference_engine(self):
        engine = NullInferenceEngine()
        adapter = NullAdapter()
        engine.initialize(adapter)
        assert engine.health_check()
        result = engine.infer("test")
        assert result == ""

    def test_adapter_save_load(self):
        adapter = MockAdapter()
        adapter.load()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "adapter.json"
            adapter.save(str(path))
            assert path.exists()

    def test_abstract_adapter(self):
        with pytest.raises(TypeError):
            ModelAdapter()


class TestLoRAConfig:
    def test_default_config(self):
        config = LoRAConfig()
        assert config.method == AdaptationMethod.LORA
        assert config.rank == 8
        assert config.alpha == 16

    def test_qlora_config(self):
        config = LoRAConfig(
            method=AdaptationMethod.QLORA,
            quantization_bits=4,
        )
        assert config.method == AdaptationMethod.QLORA
        assert config.quantization_bits == 4

    def test_config_validation(self):
        config = LoRAConfig(
            method=AdaptationMethod.QLORA,
            quantization_bits=None,
        )
        errors = config.validate_config()
        assert any("quantization" in e.lower() for e in errors)

    def test_training_config(self):
        config = TrainingConfig()
        args = config.get_training_args()
        assert "output_dir" in args
        assert "seed" in args


class TestEvaluation:
    def test_accuracy_evaluation(self):
        runner = DeterministicEvaluationRunner()
        adapter = MockAdapter()
        adapter.load()
        dataset = TrainingDataset(
            dataset_id="test",
            name="Test",
            domain=DatasetDomain.LOGISTICS,
        )
        dataset.add_example(
            TrainingExample(
                input_text="test input",
                target_output="Mock prediction for: test input",
                split=DatasetSplit.TEST,
            )
        )
        accuracy = runner.evaluate_accuracy(adapter, dataset)
        assert accuracy == 1.0

    def test_safety_evaluation(self):
        runner = DeterministicEvaluationRunner()
        adapter = MockAdapter()
        adapter.load()
        test_cases = [
            {"input": "test", "forbidden_output": "DANGEROUS"},
        ]
        result = runner.evaluate_safety(adapter, test_cases)
        assert result["safe"] == 1

    def test_domain_validity(self):
        runner = DeterministicEvaluationRunner()
        adapter = MockAdapter()
        adapter.load()
        dataset = TrainingDataset(
            dataset_id="test",
            name="Test",
            domain=DatasetDomain.LOGISTICS,
        )
        dataset.add_example(
            TrainingExample(
                input_text="test",
                target_output="output",
                split=DatasetSplit.TEST,
            )
        )
        validity = runner.evaluate_domain_validity(adapter, dataset)
        assert 0.0 <= validity <= 1.0

    def test_compare_with_baseline(self):
        runner = DeterministicEvaluationRunner()
        adapted = MockAdapter(adapter_id="adapted")
        baseline = MockAdapter(adapter_id="baseline")
        adapted.load()
        baseline.load()
        dataset = TrainingDataset(
            dataset_id="test",
            name="Test",
            domain=DatasetDomain.LOGISTICS,
        )
        dataset.add_example(
            TrainingExample(
                input_text="test",
                target_output="output",
                split=DatasetSplit.TEST,
            )
        )
        result = runner.compare_with_baseline(adapted, baseline, dataset)
        assert "accuracy_delta" in result
        assert "regression" in result


class TestEvaluationDataset:
    def test_logistics_dataset(self):
        generator = EvaluationDatasetGenerator()
        dataset = generator.generate_logistics_dataset(num_examples=5)
        assert dataset.size == 5
        assert dataset.domain == DatasetDomain.LOGISTICS

    def test_safety_test_cases(self):
        generator = EvaluationDatasetGenerator()
        cases = generator.generate_safety_test_cases()
        assert len(cases) >= 5
        assert all("forbidden_output" in c for c in cases)

    def test_regression_dataset(self):
        generator = EvaluationDatasetGenerator()
        dataset = generator.generate_regression_dataset()
        assert dataset.size >= 3
        assert all(ex.split == DatasetSplit.TEST for ex in dataset.examples)
