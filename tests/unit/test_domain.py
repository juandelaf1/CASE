import sys

import pytest

sys.path.insert(0, "src")

from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.registry import DomainRegistry
from case_core.domain.urban_policy import UrbanPolicy
from case_core.domain.logistics_policy import Department, IncidentType, LogisticsPolicy, RECOMMENDED_ACTIONS
from case_core.domain.infrastructure_policy import InfrastructurePolicy


def _make_case(text: str, domain: str = "urban_operations") -> OperationalCase:
    return OperationalCase(case_id="c1", report_text=text, domain=domain)


def _make_evidence(content: str = "test") -> EvidenceItem:
    return EvidenceItem(
        id="ev1",
        type=EvidenceType.TEXT,
        content=content,
        source="test",
        confidence=0.9,
        extracted_at="2026-09-08T12:00:00Z",
    )


class TestDomainRegistry:
    def test_register_and_get(self):
        reg = DomainRegistry()
        policy = UrbanPolicy()
        reg.register(policy)
        assert reg.get("urban_operations") is policy

    def test_get_nonexistent_returns_none(self):
        reg = DomainRegistry()
        assert reg.get("nonexistent") is None

    def test_list_domains(self):
        reg = DomainRegistry()
        reg.register(UrbanPolicy())
        reg.register(LogisticsPolicy())
        assert set(reg.list_domains()) == {"urban_operations", "logistics"}

    def test_validate_domain(self):
        reg = DomainRegistry()
        reg.register(UrbanPolicy())
        assert reg.validate_domain("urban_operations") is True
        assert reg.validate_domain("nonexistent") is False


class TestUrbanPolicy:
    def test_domain_name(self):
        assert UrbanPolicy().domain_name == "urban_operations"

    def test_validate_evidence_pass(self):
        ok, msg = UrbanPolicy().validate_evidence([_make_evidence()])
        assert ok is True

    def test_validate_evidence_empty_fails(self):
        ok, msg = UrbanPolicy().validate_evidence([])
        assert ok is False

    def test_classify_urgency_high(self):
        case = _make_case("Emergency in downtown area")
        assert UrbanPolicy().classify_urgency(case) == "HIGH"

    def test_classify_urgency_medium(self):
        case = _make_case("Broken streetlight on 5th ave")
        assert UrbanPolicy().classify_urgency(case) == "MEDIUM"

    def test_classify_urgency_low(self):
        case = _make_case("Routine maintenance check")
        assert UrbanPolicy().classify_urgency(case) == "LOW"

    def test_get_domain_context(self):
        ctx = UrbanPolicy().get_domain_context()
        assert ctx["domain"] == "urban_operations"
        assert "text" in ctx["evidence_types"]


class TestLogisticsPolicy:
    def test_domain_name(self):
        assert LogisticsPolicy().domain_name == "logistics"

    def test_classify_urgency_high(self):
        case = _make_case("Shipment delayed urgent", domain="logistics")
        assert LogisticsPolicy().classify_urgency(case) == "HIGH"

    def test_classify_urgency_critical(self):
        case = _make_case("Critical emergency shipment", domain="logistics")
        assert LogisticsPolicy().classify_urgency(case) == "CRITICAL"

    def test_classify_urgency_medium(self):
        case = _make_case("Route optimization needed", domain="logistics")
        assert LogisticsPolicy().classify_urgency(case) == "MEDIUM"

    def test_classify_urgency_low(self):
        case = _make_case("Routine logistics check", domain="logistics")
        assert LogisticsPolicy().classify_urgency(case) == "LOW"

    def test_validate_evidence_pass(self):
        ok, msg = LogisticsPolicy().validate_evidence([_make_evidence()])
        assert ok is True

    def test_validate_evidence_with_metric_pass(self):
        metric_ev = EvidenceItem(
            id="ev2", type=EvidenceType.METRIC, content="temp=5C",
            source="sensor", confidence=0.95, extracted_at="2026-09-08T12:00:00Z",
        )
        ok, msg = LogisticsPolicy().validate_evidence([metric_ev])
        assert ok is True

    def test_validate_evidence_empty_fails(self):
        ok, msg = LogisticsPolicy().validate_evidence([])
        assert ok is False
        assert "No evidence" in msg

    def test_validate_evidence_text_and_metric(self):
        ev = [_make_evidence(), EvidenceItem(
            id="ev2", type=EvidenceType.METRIC, content="temp=5C",
            source="sensor", confidence=0.95, extracted_at="2026-09-08T12:00:00Z",
        )]
        ok, msg = LogisticsPolicy().validate_evidence(ev)
        assert ok is True

    def test_classify_incident_type_delivery_delay(self):
        case = _make_case("Package delayed by 3 days", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) == IncidentType.DELIVERY_DELAY

    def test_classify_incident_type_delivery_failure(self):
        case = _make_case("Package lost in transit", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) == IncidentType.DELIVERY_FAILURE

    def test_classify_incident_type_stock_issue(self):
        case = _make_case("Warehouse stock shortage", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) == IncidentType.STOCK_ISSUE

    def test_classify_incident_type_warehouse_delay(self):
        case = _make_case("Warehouse processing backlog delay", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) == IncidentType.WAREHOUSE_DELAY

    def test_classify_incident_type_damaged_goods(self):
        case = _make_case("Goods damaged during transport", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) == IncidentType.DAMAGED_GOODS

    def test_classify_incident_type_transport_disruption(self):
        case = _make_case("Transport disruption due to weather", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) == IncidentType.TRANSPORT_DISRUPTION

    def test_classify_incident_type_none(self):
        case = _make_case("Routine checkup", domain="logistics")
        assert LogisticsPolicy().classify_incident_type(case) is None

    def test_get_recommended_actions(self):
        case = _make_case("Package delayed by 3 days", domain="logistics")
        actions = LogisticsPolicy().get_recommended_actions(case)
        assert "check_route_status" in actions

    def test_get_recommended_actions_failure(self):
        case = _make_case("Package lost in transit", domain="logistics")
        actions = LogisticsPolicy().get_recommended_actions(case)
        assert "initiate_reshipment" in actions

    def test_get_recommended_actions_unknown(self):
        case = _make_case("Routine checkup", domain="logistics")
        actions = LogisticsPolicy().get_recommended_actions(case)
        assert actions == ["investigate", "escalate_if_needed"]

    def test_get_domain_context(self):
        ctx = LogisticsPolicy().get_domain_context()
        assert ctx["domain"] == "logistics"
        assert "text" in ctx["evidence_types"]
        assert "incident_types" in ctx
        assert "departments" in ctx
        assert "recommended_actions" in ctx
        assert IncidentType.DELIVERY_DELAY.value in ctx["incident_types"]
        assert Department.FLEET.value in ctx["departments"]
        assert "check_route_status" in ctx["recommended_actions"][IncidentType.DELIVERY_DELAY.value]

    def test_incident_type_enum_values(self):
        assert IncidentType.DELIVERY_DELAY.value == "DELIVERY_DELAY"
        assert IncidentType.DELIVERY_FAILURE.value == "DELIVERY_FAILURE"
        assert IncidentType.WAREHOUSE_DELAY.value == "WAREHOUSE_DELAY"
        assert IncidentType.TRANSPORT_DISRUPTION.value == "TRANSPORT_DISRUPTION"
        assert IncidentType.DAMAGED_GOODS.value == "DAMAGED_GOODS"
        assert IncidentType.STOCK_ISSUE.value == "STOCK_ISSUE"

    def test_recommended_actions_all_incidents_covered(self):
        for incident in IncidentType:
            assert incident in RECOMMENDED_ACTIONS
            assert len(RECOMMENDED_ACTIONS[incident]) > 0

    def test_department_enum_values(self):
        assert Department.FLEET.value == "FLEET"
        assert Department.WAREHOUSE.value == "WAREHOUSE"
        assert Department.ROUTING.value == "ROUTING"
        assert Department.QUALITY.value == "QUALITY"
        assert Department.PROCUREMENT.value == "PROCUREMENT"


class TestInfrastructurePolicy:
    def test_domain_name(self):
        assert InfrastructurePolicy().domain_name == "infrastructure"

    def test_classify_urgency_critical(self):
        case = _make_case("Bridge structural collapse", domain="infrastructure")
        assert InfrastructurePolicy().classify_urgency(case) == "CRITICAL"

    def test_classify_urgency_high(self):
        case = _make_case("Road surface damage detected", domain="infrastructure")
        assert InfrastructurePolicy().classify_urgency(case) == "HIGH"

    def test_classify_urgency_medium(self):
        case = _make_case("Scheduled inspection", domain="infrastructure")
        assert InfrastructurePolicy().classify_urgency(case) == "MEDIUM"