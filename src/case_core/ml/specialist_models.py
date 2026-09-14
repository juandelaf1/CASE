"""Specialist model interfaces and adapters — Phase 4."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from case_core.ml.specialist_contracts import (
    ModelCapability,
    SpecialistEnsemble,
    SpecialistPrediction,
    SpecialistRegistry,
    SpecialistType,
)


class SpecialistModel(ABC):
    """Abstract interface for specialist models."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...

    @property
    @abstractmethod
    def capability(self) -> ModelCapability:
        ...

    @abstractmethod
    def predict(self, input_text: str, context: dict[str, Any] | None = None) -> SpecialistPrediction:
        ...

    @abstractmethod
    def predict_batch(self, input_texts: list[str], context: dict[str, Any] | None = None) -> list[SpecialistPrediction]:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


class ClassificationSpecialist(SpecialistModel):
    """Specialist for classification tasks."""

    def __init__(self, model_id: str, labels: list[str], confidence_threshold: float = 0.7):
        self._model_id = model_id
        self._labels = labels
        self._capability = ModelCapability(
            model_id=model_id,
            model_type=SpecialistType.CLASSIFICATION,
            input_types=["text"],
            output_types=["label", "confidence"],
            confidence_threshold=confidence_threshold,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def capability(self) -> ModelCapability:
        return self._capability

    def predict(self, input_text: str, context: dict[str, Any] | None = None) -> SpecialistPrediction:
        label = self._classify(input_text)
        confidence = self._get_confidence(input_text, label)
        return SpecialistPrediction(
            prediction_id=f"{self._model_id}_{hash(input_text)}",
            model_id=self._model_id,
            input_text=input_text,
            output={"label": label, "labels": self._labels},
            confidence=confidence,
        )

    def predict_batch(self, input_texts: list[str], context: dict[str, Any] | None = None) -> list[SpecialistPrediction]:
        return [self.predict(text, context) for text in input_texts]

    def health_check(self) -> bool:
        return len(self._labels) > 0

    def _classify(self, input_text: str) -> str:
        input_lower = input_text.lower()
        for label in self._labels:
            if label.lower() in input_lower:
                return label
        return self._labels[0] if self._labels else "unknown"

    def _get_confidence(self, input_text: str, label: str) -> float:
        input_lower = input_text.lower()
        if label.lower() in input_lower:
            return 0.95
        return 0.5


class RiskSpecialist(SpecialistModel):
    """Specialist for risk assessment."""

    def __init__(self, model_id: str, risk_levels: list[str] | None = None):
        self._model_id = model_id
        self._risk_levels = risk_levels or ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        self._capability = ModelCapability(
            model_id=model_id,
            model_type=SpecialistType.RISK_ASSESSMENT,
            input_types=["text", "structured_data"],
            output_types=["risk_level", "risk_score", "factors"],
            confidence_threshold=0.6,
            requires_context=True,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def capability(self) -> ModelCapability:
        return self._capability

    def predict(self, input_text: str, context: dict[str, Any] | None = None) -> SpecialistPrediction:
        risk_level = self._assess_risk(input_text, context)
        risk_score = self._calculate_risk_score(input_text, context)
        factors = self._extract_risk_factors(input_text, context)
        return SpecialistPrediction(
            prediction_id=f"{self._model_id}_{hash(input_text)}",
            model_id=self._model_id,
            input_text=input_text,
            output={"risk_level": risk_level, "risk_score": risk_score, "factors": factors},
            confidence=0.8,
        )

    def predict_batch(self, input_texts: list[str], context: dict[str, Any] | None = None) -> list[SpecialistPrediction]:
        return [self.predict(text, context) for text in input_texts]

    def health_check(self) -> bool:
        return len(self._risk_levels) > 0

    def _assess_risk(self, input_text: str, context: dict[str, Any] | None) -> str:
        input_lower = input_text.lower()
        if any(kw in input_lower for kw in ["critical", "urgent", "emergency"]):
            return "CRITICAL"
        if any(kw in input_lower for kw in ["high", "important", "significant"]):
            return "HIGH"
        if any(kw in input_lower for kw in ["medium", "moderate", "standard"]):
            return "MEDIUM"
        return "LOW"

    def _calculate_risk_score(self, input_text: str, context: dict[str, Any] | None) -> float:
        risk_level = self._assess_risk(input_text, context)
        scores = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8, "CRITICAL": 0.95}
        return scores.get(risk_level, 0.5)

    def _extract_risk_factors(self, input_text: str, context: dict[str, Any] | None) -> list[str]:
        factors = []
        input_lower = input_text.lower()
        if "hazardous" in input_lower:
            factors.append("hazardous_materials")
        if "perishable" in input_lower:
            factors.append("perishable_cargo")
        if "urgent" in input_lower:
            factors.append("time_pressure")
        if "heavy" in input_lower:
            factors.append("weight_constraints")
        return factors


class RoutingSpecialist(SpecialistModel):
    """Specialist for routing decisions."""

    def __init__(self, model_id: str):
        self._model_id = model_id
        self._capability = ModelCapability(
            model_id=model_id,
            model_type=SpecialistType.ROUTING,
            input_types=["origin", "destination", "constraints"],
            output_types=["route", "estimated_time", "estimated_cost"],
            confidence_threshold=0.7,
            requires_context=True,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def capability(self) -> ModelCapability:
        return self._capability

    def predict(self, input_text: str, context: dict[str, Any] | None = None) -> SpecialistPrediction:
        route = self._suggest_route(input_text, context)
        return SpecialistPrediction(
            prediction_id=f"{self._model_id}_{hash(input_text)}",
            model_id=self._model_id,
            input_text=input_text,
            output=route,
            confidence=0.75,
        )

    def predict_batch(self, input_texts: list[str], context: dict[str, Any] | None = None) -> list[SpecialistPrediction]:
        return [self.predict(text, context) for text in input_texts]

    def health_check(self) -> bool:
        return True

    def _suggest_route(self, input_text: str, context: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "route_type": "direct",
            "transport_mode": "truck",
            "estimated_hours": 24,
            "estimated_cost": 500.0,
        }


class EnsembleSpecialist(SpecialistModel):
    """Ensemble of multiple specialist models."""

    def __init__(self, model_id: str, specialists: list[SpecialistModel], ensemble_config: SpecialistEnsemble | None = None):
        self._model_id = model_id
        self._specialists = specialists
        self._config = ensemble_config or SpecialistEnsemble(ensemble_id=f"{model_id}_ensemble")
        self._capability = ModelCapability(
            model_id=model_id,
            model_type=SpecialistType.CLASSIFICATION,
            input_types=["text"],
            output_types=["predictions", "consensus"],
            confidence_threshold=0.7,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def capability(self) -> ModelCapability:
        return self._capability

    def predict(self, input_text: str, context: dict[str, Any] | None = None) -> SpecialistPrediction:
        predictions = [s.predict(input_text, context) for s in self._specialists]
        consensus = self._build_consensus(predictions)
        return SpecialistPrediction(
            prediction_id=f"{self._model_id}_{hash(input_text)}",
            model_id=self._model_id,
            input_text=input_text,
            output=consensus,
            confidence=consensus.get("confidence", 0.5),
        )

    def predict_batch(self, input_texts: list[str], context: dict[str, Any] | None = None) -> list[SpecialistPrediction]:
        return [self.predict(text, context) for text in input_texts]

    def health_check(self) -> bool:
        return all(s.health_check() for s in self._specialists)

    def _build_consensus(self, predictions: list[SpecialistPrediction]) -> dict[str, Any]:
        if not predictions:
            return {"consensus": "none", "confidence": 0.0}
        outputs = [p.output for p in predictions]
        confidences = [p.confidence for p in predictions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return {
            "consensus": outputs[0] if outputs else None,
            "num_specialists": len(predictions),
            "avg_confidence": avg_confidence,
            "individual_outputs": outputs,
        }


class SpecialistRegistryManager:
    """Manages specialist model registry."""

    def __init__(self) -> None:
        self._registry = SpecialistRegistry()

    def register_specialist(self, specialist: SpecialistModel) -> None:
        self._registry.register(specialist.capability)

    def get_specialist(self, model_id: str) -> ModelCapability | None:
        return self._registry.get(model_id)

    def list_specialists(self, model_type: SpecialistType | None = None) -> list[ModelCapability]:
        if model_type:
            return self._registry.list_by_type(model_type)
        return list(self._registry.specialists.values())

    def get_registry(self) -> SpecialistRegistry:
        return self._registry
