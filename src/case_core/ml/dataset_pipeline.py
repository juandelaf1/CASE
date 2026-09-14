"""Dataset preparation pipeline — Phase 3.3."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from case_core.ml.dataset_contracts import (
    DatasetConfig,
    DatasetDomain,
    DatasetSplit,
    DatasetVersion,
    Provenance,
    TrainingDataset,
    TrainingExample,
)
from case_core.ml.training_abstraction import TrainingPipeline


class DeterministicDatasetPipeline(TrainingPipeline):
    """Deterministic pipeline for dataset preparation."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def prepare_dataset(
        self, raw_data: list[dict[str, Any]], config: dict[str, Any]
    ) -> TrainingDataset:
        domain = DatasetDomain(config.get("domain", "general"))
        dataset_id = config.get("dataset_id", f"dataset_{domain.value}")
        examples = []
        for item in raw_data:
            example = TrainingExample(
                input_text=item.get("input", ""),
                target_output=item.get("target", ""),
                metadata=item.get("metadata", {}),
                domain=domain,
                split=DatasetSplit.TRAIN,
                quality_score=item.get("quality_score"),
            )
            examples.append(example)
        split_config = DatasetConfig(
            dataset_id=dataset_id,
            domain=domain,
            train_split_ratio=config.get("train_split_ratio", 0.8),
            validation_split_ratio=config.get("validation_split_ratio", 0.1),
            test_split_ratio=config.get("test_split_ratio", 0.1),
            min_quality_score=config.get("min_quality_score", 0.5),
            max_examples=config.get("max_examples"),
            random_seed=config.get("random_seed", 42),
        )
        examples = self._apply_quality_filter(examples, split_config.min_quality_score)
        if split_config.max_examples and len(examples) > split_config.max_examples:
            examples = examples[:split_config.max_examples]
        examples = self._split_dataset(examples, split_config)
        provenance = Provenance(
            source=config.get("source", "deterministic_pipeline"),
            version=config.get("version", "1.0"),
            created_at=datetime.now(timezone.utc).isoformat(),
            description=config.get("description", "Deterministic dataset preparation"),
        )
        return TrainingDataset(
            dataset_id=dataset_id,
            name=config.get("name", f"{domain.value}_dataset"),
            domain=domain,
            version=config.get("version", "1.0"),
            examples=examples,
            provenance=provenance,
            metadata=config.get("metadata", {}),
        )

    def train(self, dataset: TrainingDataset, config: dict[str, Any]) -> Any:
        raise NotImplementedError("Training not implemented in deterministic pipeline")

    def evaluate(self, adapter: Any, dataset: TrainingDataset) -> dict[str, Any]:
        raise NotImplementedError("Evaluation not implemented in deterministic pipeline")

    def export(self, adapter: Any, output_path: str) -> None:
        raise NotImplementedError("Export not implemented in deterministic pipeline")

    def _apply_quality_filter(
        self, examples: list[TrainingExample], min_quality: float
    ) -> list[TrainingExample]:
        return [ex for ex in examples if ex.quality_score is None or ex.quality_score >= min_quality]

    def _split_dataset(
        self, examples: list[TrainingExample], config: DatasetConfig
    ) -> list[TrainingExample]:
        random.shuffle(examples)
        n = len(examples)
        train_end = int(n * config.train_split_ratio)
        val_end = train_end + int(n * config.validation_split_ratio)
        for i, ex in enumerate(examples):
            if i < train_end:
                ex.split = DatasetSplit.TRAIN
            elif i < val_end:
                ex.split = DatasetSplit.VALIDATION
            else:
                ex.split = DatasetSplit.TEST
        return examples

    def save_dataset(self, dataset: TrainingDataset, output_path: str) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "domain": dataset.domain.value,
            "version": dataset.version,
            "examples": [ex.model_dump() for ex in dataset.examples],
            "provenance": dataset.provenance.model_dump() if dataset.provenance else None,
            "metadata": dataset.metadata,
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_dataset(self, input_path: str) -> TrainingDataset:
        with open(input_path) as f:
            data = json.load(f)
        return TrainingDataset(
            dataset_id=data["dataset_id"],
            name=data["name"],
            domain=DatasetDomain(data["domain"]),
            version=data["version"],
            examples=[TrainingExample(**ex) for ex in data["examples"]],
            provenance=Provenance(**data["provenance"]) if data.get("provenance") else None,
            metadata=data.get("metadata", {}),
        )

    def compute_checksum(self, dataset: TrainingDataset) -> str:
        content = json.dumps(dataset.model_dump(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def create_version(
        self, dataset: TrainingDataset, changes: list[str], parent_version: str | None = None
    ) -> DatasetVersion:
        return DatasetVersion(
            version_id=f"{dataset.dataset_id}_v{dataset.version}",
            dataset_id=dataset.dataset_id,
            version=dataset.version,
            changes=changes,
            parent_version=parent_version,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
