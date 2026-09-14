"""Specialist model contracts — Phase 4."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SpecialistType(str, Enum):
    """Types of specialist models."""

    CLASSIFICATION = "classification"
    RISK_ASSESSMENT = "risk_assessment"
    ANOMALY_DETECTION = "anomaly_detection"
    ROUTING = "routing"
    SCORING = "scoring"


class ModelCapability(BaseModel):
    """Capabilities of a specialist model."""

    model_id: str
    model_type: SpecialistType
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_latency_ms: int = Field(default=1000, ge=0)
    supports_batch: bool = True
    requires_context: bool = False
    fallback_value: Any = None


class SpecialistPrediction(BaseModel):
    """Prediction from a specialist model."""

    prediction_id: str
    model_id: str
    input_text: str
    output: Any
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_fallback: bool = False


class SpecialistEnsemble(BaseModel):
    """Configuration for combining specialist predictions."""

    ensemble_id: str
    specialist_ids: list[str] = Field(default_factory=list)
    weighting: dict[str, float] = Field(default_factory=dict)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    require_all: bool = False
    conflict_resolution: str = "highest_confidence"


class SpecialistRegistry(BaseModel):
    """Registry of available specialist models."""

    registry_id: str = "default"
    specialists: dict[str, ModelCapability] = Field(default_factory=dict)
    fallback_model_id: str | None = None

    def register(self, capability: ModelCapability) -> None:
        self.specialists[capability.model_id] = capability

    def get(self, model_id: str) -> ModelCapability | None:
        return self.specialists.get(model_id)

    def list_by_type(self, model_type: SpecialistType) -> list[ModelCapability]:
        return [cap for cap in self.specialists.values() if cap.model_type == model_type]
