"""Training abstraction — Phase 3.1.

Separates training/adaptation from CASE runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from case_core.ml.dataset_contracts import TrainingDataset


class ModelAdapter(ABC):
    """Abstract interface for model adapters (LoRA, QLoRA, etc.)."""

    @property
    @abstractmethod
    def adapter_id(self) -> str:
        ...

    @property
    @abstractmethod
    def base_model(self) -> str:
        ...

    @abstractmethod
    def load(self, adapter_path: str | None = None) -> None:
        ...

    @abstractmethod
    def save(self, output_path: str) -> None:
        ...

    @abstractmethod
    def predict(self, input_text: str) -> str:
        ...

    @abstractmethod
    def predict_batch(self, input_texts: list[str]) -> list[str]:
        ...


class TrainingPipeline(ABC):
    """Abstract interface for training pipelines."""

    @abstractmethod
    def prepare_dataset(self, raw_data: list[dict[str, Any]], config: dict[str, Any]) -> TrainingDataset:
        ...

    @abstractmethod
    def train(self, dataset: TrainingDataset, config: dict[str, Any]) -> ModelAdapter:
        ...

    @abstractmethod
    def evaluate(self, adapter: ModelAdapter, dataset: TrainingDataset) -> dict[str, Any]:
        ...

    @abstractmethod
    def export(self, adapter: ModelAdapter, output_path: str) -> None:
        ...


class InferenceEngine(ABC):
    """Abstract interface for inference engines."""

    @abstractmethod
    def initialize(self, adapter: ModelAdapter) -> None:
        ...

    @abstractmethod
    def infer(self, input_text: str) -> str:
        ...

    @abstractmethod
    def infer_batch(self, input_texts: list[str]) -> list[str]:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


class EvaluationRunner(ABC):
    """Abstract interface for model evaluation."""

    @abstractmethod
    def evaluate_accuracy(self, adapter: ModelAdapter, dataset: TrainingDataset) -> float:
        ...

    @abstractmethod
    def evaluate_safety(self, adapter: ModelAdapter, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        ...

    @abstractmethod
    def evaluate_domain_validity(self, adapter: ModelAdapter, dataset: TrainingDataset) -> float:
        ...

    @abstractmethod
    def compare_with_baseline(
        self, adapted_adapter: ModelAdapter, baseline_adapter: ModelAdapter, dataset: TrainingDataset
    ) -> dict[str, Any]:
        ...
