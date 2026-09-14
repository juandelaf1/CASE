"""Tests for Specialist Models — Phase 4."""

import pytest

from case_core.ml.specialist_contracts import (
    ModelCapability,
    SpecialistEnsemble,
    SpecialistPrediction,
    SpecialistRegistry,
    SpecialistType,
)
from case_core.ml.specialist_models import (
    ClassificationSpecialist,
    EnsembleSpecialist,
    RiskSpecialist,
    RoutingSpecialist,
    SpecialistModel,
    SpecialistRegistryManager,
)


class TestSpecialistContracts:
    def test_model_capability(self):
        cap = ModelCapability(
            model_id="test_model",
            model_type=SpecialistType.CLASSIFICATION,
            input_types=["text"],
            output_types=["label"],
        )
        assert cap.model_id == "test_model"
        assert cap.model_type == SpecialistType.CLASSIFICATION

    def test_specialist_prediction(self):
        pred = SpecialistPrediction(
            prediction_id="pred_1",
            model_id="model_1",
            input_text="test",
            output={"label": "A"},
            confidence=0.9,
        )
        assert pred.confidence == 0.9
        assert pred.output["label"] == "A"

    def test_specialist_ensemble(self):
        ensemble = SpecialistEnsemble(
            ensemble_id="ens_1",
            specialist_ids=["m1", "m2"],
            weighting={"m1": 0.6, "m2": 0.4},
        )
        assert len(ensemble.specialist_ids) == 2

    def test_specialist_registry(self):
        registry = SpecialistRegistry()
        cap = ModelCapability(
            model_id="test",
            model_type=SpecialistType.CLASSIFICATION,
        )
        registry.register(cap)
        assert registry.get("test") is not None
        assert len(registry.list_by_type(SpecialistType.CLASSIFICATION)) == 1


class TestClassificationSpecialist:
    def test_creation(self):
        specialist = ClassificationSpecialist(
            model_id="cls_1",
            labels=["approve", "reject", "escalate"],
        )
        assert specialist.model_id == "cls_1"
        assert specialist.health_check()

    def test_predict(self):
        specialist = ClassificationSpecialist(
            model_id="cls_1",
            labels=["approve", "reject"],
        )
        pred = specialist.predict("approve this shipment")
        assert pred.output["label"] == "approve"
        assert pred.confidence > 0.5

    def test_predict_batch(self):
        specialist = ClassificationSpecialist(
            model_id="cls_1",
            labels=["A", "B"],
        )
        preds = specialist.predict_batch(["A", "B", "C"])
        assert len(preds) == 3

    def test_health_check_empty_labels(self):
        specialist = ClassificationSpecialist(
            model_id="cls_1",
            labels=[],
        )
        assert not specialist.health_check()


class TestRiskSpecialist:
    def test_creation(self):
        specialist = RiskSpecialist(model_id="risk_1")
        assert specialist.model_id == "risk_1"
        assert specialist.health_check()

    def test_predict_critical(self):
        specialist = RiskSpecialist(model_id="risk_1")
        pred = specialist.predict("Critical emergency shipment")
        assert pred.output["risk_level"] == "CRITICAL"
        assert pred.output["risk_score"] >= 0.9

    def test_predict_low(self):
        specialist = RiskSpecialist(model_id="risk_1")
        pred = specialist.predict("Simple package delivery")
        assert pred.output["risk_level"] == "LOW"
        assert pred.output["risk_score"] <= 0.3

    def test_risk_factors(self):
        specialist = RiskSpecialist(model_id="risk_1")
        pred = specialist.predict("Hazardous materials urgent delivery")
        factors = pred.output["factors"]
        assert "hazardous_materials" in factors
        assert "time_pressure" in factors


class TestRoutingSpecialist:
    def test_creation(self):
        specialist = RoutingSpecialist(model_id="route_1")
        assert specialist.model_id == "route_1"
        assert specialist.health_check()

    def test_predict(self):
        specialist = RoutingSpecialist(model_id="route_1")
        pred = specialist.predict("Ship from A to B")
        assert "route_type" in pred.output
        assert "estimated_hours" in pred.output


class TestEnsembleSpecialist:
    def test_creation(self):
        cls_spec = ClassificationSpecialist(model_id="cls_1", labels=["A", "B"])
        risk_spec = RiskSpecialist(model_id="risk_1")
        ensemble = EnsembleSpecialist(
            model_id="ens_1",
            specialists=[cls_spec, risk_spec],
        )
        assert ensemble.model_id == "ens_1"
        assert ensemble.health_check()

    def test_predict(self):
        cls_spec = ClassificationSpecialist(model_id="cls_1", labels=["A", "B"])
        risk_spec = RiskSpecialist(model_id="risk_1")
        ensemble = EnsembleSpecialist(
            model_id="ens_1",
            specialists=[cls_spec, risk_spec],
        )
        pred = ensemble.predict("Test input")
        assert "consensus" in pred.output
        assert pred.output["num_specialists"] == 2


class TestSpecialistRegistryManager:
    def test_register_and_list(self):
        manager = SpecialistRegistryManager()
        spec = ClassificationSpecialist(model_id="cls_1", labels=["A", "B"])
        manager.register_specialist(spec)
        specialists = manager.list_specialists()
        assert len(specialists) == 1

    def test_list_by_type(self):
        manager = SpecialistRegistryManager()
        cls_spec = ClassificationSpecialist(model_id="cls_1", labels=["A"])
        risk_spec = RiskSpecialist(model_id="risk_1")
        manager.register_specialist(cls_spec)
        manager.register_specialist(risk_spec)
        cls_list = manager.list_specialists(SpecialistType.CLASSIFICATION)
        risk_list = manager.list_specialists(SpecialistType.RISK_ASSESSMENT)
        assert len(cls_list) == 1
        assert len(risk_list) == 1

    def test_get_specialist(self):
        manager = SpecialistRegistryManager()
        spec = RoutingSpecialist(model_id="route_1")
        manager.register_specialist(spec)
        result = manager.get_specialist("route_1")
        assert result is not None
        assert result.model_id == "route_1"


class TestAbstractSpecialist:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            SpecialistModel()


class TestSpecialistType:
    def test_all_types(self):
        assert SpecialistType.CLASSIFICATION.value == "classification"
        assert SpecialistType.RISK_ASSESSMENT.value == "risk_assessment"
        assert SpecialistType.ANOMALY_DETECTION.value == "anomaly_detection"
        assert SpecialistType.ROUTING.value == "routing"
        assert SpecialistType.SCORING.value == "scoring"
