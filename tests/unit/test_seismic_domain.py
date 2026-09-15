"""Unit tests for seismic risk domain integration.

Tests SeismicRiskPolicy, SeismicAutomationPolicy, and USGSClient
with mocked responses. No network calls.
"""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, "src")

from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.seismic_automation import SeismicAutomationPolicy
from case_core.domain.seismic_policy import (
    SeismicEventType,
    SeismicRiskLevel,
    SeismicRiskPolicy,
    classify_magnitude,
    classify_risk_level,
)
from usgs_adapter.client import SeismicEvent, USGSClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_seismic_case(
    magnitude: float = 5.0,
    depth_km: float = 10.0,
    tsunami: bool = False,
    lat: float = 35.0,
    lon: float = 139.0,
    place: str = "Tokyo, Japan",
) -> OperationalCase:
    return OperationalCase(
        case_id="SEISMIC-TEST-001",
        report_text=f"M{magnitude} earthquake at {place}",
        domain="seismic_risk",
        urgency=UrgencyLevel.MEDIUM,
        evidence=[
            EvidenceItem(
                id="ev-seismic-001",
                type=EvidenceType.METRIC,
                content=json.dumps({"magnitude": magnitude, "depth_km": depth_km}),
                source="usgs",
                confidence=0.95,
                extracted_at="2026-09-15T00:00:00Z",
            )
        ],
        metadata={
            "magnitude": magnitude,
            "depth_km": depth_km,
            "tsunami": tsunami,
            "latitude": lat,
            "longitude": lon,
            "place": place,
        },
    )


def _mock_usgs_response(events: list[dict] | None = None) -> dict:
    if events is None:
        events = [
            {
                "id": "us7000abcdef",
                "properties": {
                    "mag": 6.2,
                    "place": "20km NE of Tokyo, Japan",
                    "time": 1726358400000,
                    "felt": 150,
                    "tsunami": 0,
                    "type": "earthquake",
                    "magType": "mw",
                    "sig": 590,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [139.7, 35.7, 30.0],
                },
            }
        ]
    return {"type": "FeatureCollection", "features": events}


def _make_usgs_event(
    event_id: str = "test-event-001",
    mag: float = 5.0,
    depth: float = 10.0,
    lat: float = 35.0,
    lon: float = 139.0,
    place: str = "Test Location",
    tsunami: int = 0,
) -> dict:
    return {
        "id": event_id,
        "properties": {
            "mag": mag,
            "place": place,
            "time": 1726358400000,
            "felt": 0,
            "tsunami": tsunami,
            "type": "earthquake",
            "magType": "mw",
            "sig": 0,
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat, depth],
        },
    }


# ---------------------------------------------------------------------------
# SeismicRiskPolicy tests
# ---------------------------------------------------------------------------

class TestSeismicRiskPolicyConstruction:
    def test_domain_name(self):
        policy = SeismicRiskPolicy()
        assert policy.domain_name == "seismic_risk"

    def test_implements_domain_policy(self):
        from case_core.ports.domain import DomainPolicy
        policy = SeismicRiskPolicy()
        assert isinstance(policy, DomainPolicy)


class TestSeismicRiskPolicyValidation:
    def test_validate_evidence_with_metric(self):
        policy = SeismicRiskPolicy()
        evidence = [
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.METRIC,
                content='{"magnitude": 5.0}',
                source="usgs",
                confidence=0.9,
                extracted_at="2026-09-15T00:00:00Z",
            )
        ]
        valid, msg = policy.validate_evidence(evidence)
        assert valid is True

    def test_validate_evidence_with_text(self):
        policy = SeismicRiskPolicy()
        evidence = [
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.TEXT,
                content="Earthquake felt in downtown area",
                source="report",
                confidence=0.8,
                extracted_at="2026-09-15T00:00:00Z",
            )
        ]
        valid, msg = policy.validate_evidence(evidence)
        assert valid is True

    def test_validate_evidence_empty_rejects(self):
        policy = SeismicRiskPolicy()
        valid, msg = policy.validate_evidence([])
        assert valid is False
        assert "No evidence" in msg

    def test_validate_evidence_wrong_type_rejects(self):
        policy = SeismicRiskPolicy()
        evidence = [
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.IMAGE,
                content="photo.jpg",
                source="camera",
                confidence=0.5,
                extracted_at="2026-09-15T00:00:00Z",
            )
        ]
        valid, msg = policy.validate_evidence(evidence)
        assert valid is False
        assert "text or metric" in msg


class TestSeismicRiskPolicyUrgency:
    def test_critical_for_m7(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=7.5)
        assert policy.classify_urgency(case) == "CRITICAL"

    def test_high_for_m5_5(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=6.0)
        assert policy.classify_urgency(case) == "HIGH"

    def test_medium_for_m4_5(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=5.0)
        assert policy.classify_urgency(case) == "MEDIUM"

    def test_low_for_below_threshold(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=3.0)
        assert policy.classify_urgency(case) == "LOW"


class TestSeismicRiskPolicyClassification:
    def test_classify_magnitude_major(self):
        assert classify_magnitude(7.5) == SeismicEventType.MAJOR

    def test_classify_magnitude_strong(self):
        assert classify_magnitude(6.0) == SeismicEventType.STRONG

    def test_classify_magnitude_moderate(self):
        assert classify_magnitude(5.0) == SeismicEventType.MODERATE

    def test_classify_magnitude_minor(self):
        assert classify_magnitude(3.0) == SeismicEventType.MINOR

    def test_classify_risk_level_critical(self):
        assert classify_risk_level(7.5) == SeismicRiskLevel.CRITICAL

    def test_classify_risk_level_high(self):
        assert classify_risk_level(6.0) == SeismicRiskLevel.HIGH

    def test_classify_risk_level_medium(self):
        assert classify_risk_level(5.0) == SeismicRiskLevel.MEDIUM

    def test_classify_risk_level_low(self):
        assert classify_risk_level(3.0) == SeismicRiskLevel.LOW


class TestSeismicRiskPolicyActions:
    def test_major_has_emergency_actions(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=7.5)
        actions = policy.get_recommended_actions(case)
        assert "activate_emergency_protocol" in actions
        assert "notify_authorities" in actions

    def test_strong_has_notification_actions(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=6.0)
        actions = policy.get_recommended_actions(case)
        assert "notify_emergency_services" in actions

    def test_moderate_has_logging_actions(self):
        policy = SeismicRiskPolicy()
        case = _make_seismic_case(magnitude=5.0)
        actions = policy.get_recommended_actions(case)
        assert "log_event" in actions
        assert "monitor_aftershocks" in actions


class TestSeismicRiskPolicyContext:
    def test_domain_context_keys(self):
        policy = SeismicRiskPolicy()
        ctx = policy.get_domain_context()
        assert ctx["domain"] == "seismic_risk"
        assert "event_types" in ctx
        assert "magnitude_thresholds" in ctx
        assert "recommended_actions" in ctx


# ---------------------------------------------------------------------------
# SeismicAutomationPolicy tests
# ---------------------------------------------------------------------------

class TestSeismicAutomationPolicyConstruction:
    def test_domain_name(self):
        policy = SeismicAutomationPolicy()
        assert policy.domain_name == "seismic_risk"

    def test_implements_automation_policy(self):
        from case_core.ports.automation import AutomationPolicy
        policy = SeismicAutomationPolicy()
        assert isinstance(policy, AutomationPolicy)


class TestSeismicAutomationPolicyAssessRisk:
    def test_major_magnitude_escalates(self):
        policy = SeismicAutomationPolicy()
        case = _make_seismic_case(magnitude=7.5)
        assessment = policy.assess_risk(
            case=case,
            data={"decision": "escalate", "urgency": "CRITICAL"},
            validation_status="valid",
            evidence_quality="high",
            confidence=0.9,
        )
        assert assessment.risk_level.value == "CRITICAL"
        assert assessment.requires_hitl is True
        assert "major_magnitude" in assessment.factors

    def test_strong_magnitude_human_review(self):
        policy = SeismicAutomationPolicy()
        case = _make_seismic_case(magnitude=6.0)
        assessment = policy.assess_risk(
            case=case,
            data={"decision": "approve", "urgency": "HIGH"},
            validation_status="valid",
            evidence_quality="high",
            confidence=0.8,
        )
        assert assessment.risk_level.value == "HIGH"
        assert assessment.requires_hitl is True

    def test_moderate_magnitude_auto_approve(self):
        policy = SeismicAutomationPolicy()
        case = _make_seismic_case(magnitude=5.0)
        assessment = policy.assess_risk(
            case=case,
            data={"decision": "approve", "urgency": "MEDIUM"},
            validation_status="valid",
            evidence_quality="medium",
            confidence=0.85,
        )
        assert assessment.risk_level.value == "MEDIUM"
        assert assessment.requires_hitl is False

    def test_tsunami_increases_risk(self):
        policy = SeismicAutomationPolicy()
        case = _make_seismic_case(magnitude=5.0, tsunami=True)
        assessment = policy.assess_risk(
            case=case,
            data={"decision": "approve", "urgency": "MEDIUM"},
            validation_status="valid",
            evidence_quality="medium",
            confidence=0.85,
        )
        assert assessment.risk_level.value == "HIGH"
        assert "tsunami_flag" in assessment.factors

    def test_low_confidence_triggers_hitl(self):
        policy = SeismicAutomationPolicy()
        case = _make_seismic_case(magnitude=5.0)
        assessment = policy.assess_risk(
            case=case,
            data={"decision": "approve", "urgency": "MEDIUM"},
            validation_status="valid",
            evidence_quality="medium",
            confidence=0.4,
        )
        assert assessment.requires_hitl is True
        assert "confidence_low" in assessment.factors


class TestSeismicAutomationPolicyFactors:
    def test_get_risk_factors(self):
        policy = SeismicAutomationPolicy()
        factors = policy.get_risk_factors()
        assert "magnitude_level" in factors
        assert "depth_category" in factors
        assert "tsunami_flag" in factors


class TestSeismicAutomationPolicyRules:
    def test_automation_rules_keys(self):
        policy = SeismicAutomationPolicy()
        rules = policy.get_automation_rules()
        assert "auto_approve_conditions" in rules
        assert "human_review_conditions" in rules
        assert "escalate_conditions" in rules


# ---------------------------------------------------------------------------
# USGSClient tests
# ---------------------------------------------------------------------------

class TestUSGSClientConstruction:
    def test_default_construction(self):
        client = USGSClient()
        assert client._min_magnitude == 4.5
        assert client._lookback_days == 30

    def test_custom_params(self):
        client = USGSClient(min_magnitude=5.0, lookback_days=7)
        assert client._min_magnitude == 5.0
        assert client._lookback_days == 7


class TestUSGSClientParsing:
    def test_parse_valid_event(self):
        client = USGSClient()
        feature = _make_usgs_event(mag=6.2, depth=30.0, place="Tokyo, Japan")
        event = client._parse_event(feature)
        assert event is not None
        assert event.event_id == "test-event-001"
        assert event.magnitude == 6.2
        assert event.depth_km == 30.0
        assert event.place == "Tokyo, Japan"
        assert event.tsunami is False

    def test_parse_tsunami_event(self):
        client = USGSClient()
        feature = _make_usgs_event(mag=7.0, tsunami=1)
        event = client._parse_event(feature)
        assert event is not None
        assert event.tsunami is True

    def test_parse_invalid_event_returns_none(self):
        client = USGSClient()
        event = client._parse_event({"id": "bad", "properties": {}, "geometry": {}})
        assert event is None


class TestUSGSClientFetchRecent:
    def test_fetch_recent_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_usgs_response()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("usgs_adapter.client.httpx.Client", return_value=mock_client):
            client = USGSClient()
            events = client.fetch_recent()

        assert len(events) == 1
        assert events[0].magnitude == 6.2
        assert events[0].place == "20km NE of Tokyo, Japan"

    def test_fetch_recent_empty(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"type": "FeatureCollection", "features": []}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("usgs_adapter.client.httpx.Client", return_value=mock_client):
            client = USGSClient()
            events = client.fetch_recent()

        assert events == []

    def test_fetch_recent_timeout(self):
        import httpx
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("usgs_adapter.client.httpx.Client", return_value=mock_client):
            client = USGSClient()
            events = client.fetch_recent()

        assert events == []

    def test_fetch_recent_http_error(self):
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("usgs_adapter.client.httpx.Client", return_value=mock_client):
            client = USGSClient()
            events = client.fetch_recent()

        assert events == []


class TestUSGSClientHealthCheck:
    def test_health_check_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("usgs_adapter.client.httpx.Client", return_value=mock_client):
            client = USGSClient()
            assert client.health_check() is True

    def test_health_check_failure(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("usgs_adapter.client.httpx.Client", return_value=mock_client):
            client = USGSClient()
            assert client.health_check() is False


class TestSeismicEvent:
    def test_to_dict(self):
        event = SeismicEvent(
            event_id="test-001",
            magnitude=5.5,
            depth_km=20.0,
            latitude=35.0,
            longitude=139.0,
            place="Tokyo",
            timestamp="2026-09-15T00:00:00+00:00",
            felt_count=10,
            tsunami=False,
        )
        d = event.to_dict()
        assert d["event_id"] == "test-001"
        assert d["magnitude"] == 5.5
        assert d["tsunami"] is False


# ---------------------------------------------------------------------------
# Architecture boundary tests
# ---------------------------------------------------------------------------

class TestSeismicPolicyNoCoreCoupling:
    def test_usgs_adapter_no_core_imports(self):
        import inspect

        from usgs_adapter.client import USGSClient
        source = inspect.getsource(USGSClient)
        assert "from case_core" not in source
        assert "from case_core.domain" not in source

    def test_seismic_policy_only_contracts_imports(self):
        import inspect

        from case_core.domain.seismic_policy import SeismicRiskPolicy
        source = inspect.getsource(SeismicRiskPolicy)
        assert "from case_core.providers" not in source
        assert "from case_core.application" not in source
