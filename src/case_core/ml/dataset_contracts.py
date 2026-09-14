"""Dataset contracts for ML training — Phase 3."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DatasetDomain(str, Enum):
    """Domain of the training dataset."""

    LOGISTICS = "logistics"
    URBAN = "urban"
    INFRASTRUCTURE = "infrastructure"
    GENERAL = "general"


class DatasetSplit(str, Enum):
    """Standard dataset splits."""

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class Provenance(BaseModel):
    """Provenance information for a dataset."""

    source: str
    version: str = "1.0"
    created_at: str | None = None
    author: str | None = None
    description: str | None = None
    license: str | None = None
    checksum: str | None = None


class TrainingExample(BaseModel):
    """A single training example."""

    input_text: str
    target_output: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    domain: DatasetDomain = DatasetDomain.GENERAL
    split: DatasetSplit = DatasetSplit.TRAIN
    quality_score: float | None = Field(default=None, ge=0, le=1)


class TrainingDataset(BaseModel):
    """A collection of training examples with metadata."""

    dataset_id: str
    name: str
    domain: DatasetDomain
    version: str = "1.0"
    examples: list[TrainingExample] = Field(default_factory=list)
    provenance: Provenance | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.examples)

    def get_split(self, split: DatasetSplit) -> list[TrainingExample]:
        return [ex for ex in self.examples if ex.split == split]

    def add_example(self, example: TrainingExample) -> None:
        self.examples.append(example)

    def validate_quality(self, min_quality: float = 0.5) -> list[TrainingExample]:
        return [ex for ex in self.examples if ex.quality_score is not None and ex.quality_score >= min_quality]


class DatasetVersion(BaseModel):
    """Version tracking for datasets."""

    version_id: str
    dataset_id: str
    version: str
    changes: list[str] = Field(default_factory=list)
    parent_version: str | None = None
    created_at: str | None = None


class DatasetConfig(BaseModel):
    """Configuration for dataset preparation."""

    dataset_id: str
    domain: DatasetDomain
    train_split_ratio: float = Field(default=0.8, ge=0, le=1)
    validation_split_ratio: float = Field(default=0.1, ge=0, le=1)
    test_split_ratio: float = Field(default=0.1, ge=0, le=1)
    min_quality_score: float = Field(default=0.5, ge=0, le=1)
    max_examples: int | None = None
    random_seed: int = 42
