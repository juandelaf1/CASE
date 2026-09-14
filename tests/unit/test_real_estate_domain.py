"""Tests for Real Estate Domain Pack — Phase 6."""


from case_core.contracts.automation import AutomationDecision, RiskLevel
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.real_estate_policy import (
    PropertyType,
    RealEstateAutomationPolicy,
    RealEstateIncidentType,
    RealEstatePolicy,
    RealEstateUrgency,
    TransactionType,
)


def make_case(report_text: str, case_id: str = "case_1") -> OperationalCase:
    return OperationalCase(
        case_id=case_id,
        domain="real_estate",
        report_text=report_text,
        urgency=UrgencyLevel.MEDIUM,
    )


class TestRealEstatePolicy:
    def test_domain_name(self):
        policy = RealEstatePolicy()
        assert policy.domain_name == "real_estate"

    def test_validate_evidence_with_text(self):
        policy = RealEstatePolicy()
        evidence = [EvidenceItem(
            id="e1",
            type=EvidenceType.TEXT,
            content="test",
            source="test",
            confidence=0.9,
            extracted_at="2026-01-01T00:00:00Z",
        )]
        assert policy.validate_evidence(evidence) == (True, "Evidence validated")

    def test_validate_evidence_with_metric(self):
        policy = RealEstatePolicy()
        evidence = [EvidenceItem(
            id="e2",
            type=EvidenceType.METRIC,
            content="value: 100",
            source="test",
            confidence=0.9,
            extracted_at="2026-01-01T00:00:00Z",
        )]
        assert policy.validate_evidence(evidence) == (True, "Evidence validated")

    def test_validate_evidence_empty(self):
        policy = RealEstatePolicy()
        assert policy.validate_evidence([]) == (False, "No evidence provided for real estate case")

    def test_classify_urgency_critical(self):
        policy = RealEstatePolicy()
        case = make_case("Emergency property inspection required")
        assert policy.classify_urgency(case) == "CRITICAL"

    def test_classify_urgency_high(self):
        policy = RealEstatePolicy()
        case = make_case("Important deadline for closing")
        assert policy.classify_urgency(case) == "HIGH"

    def test_classify_urgency_low(self):
        policy = RealEstatePolicy()
        case = make_case("General property inquiry")
        assert policy.classify_urgency(case) == "LOW"

    def test_get_domain_context(self):
        policy = RealEstatePolicy()
        context = policy.get_domain_context()
        assert context["domain"] == "real_estate"
        assert "residential" in context["property_types"]

    def test_classify_incident_valuation(self):
        policy = RealEstatePolicy()
        case = make_case("Need property valuation for sale")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.VALUATION

    def test_classify_incident_inspection(self):
        policy = RealEstatePolicy()
        case = make_case("Schedule property inspection")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.INSPECTION

    def test_classify_incident_listing(self):
        policy = RealEstatePolicy()
        case = make_case("List property for sale on market")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.LISTING

    def test_classify_incident_negotiation(self):
        policy = RealEstatePolicy()
        case = make_case("Negotiate offer price")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.NEGOTIATION

    def test_classify_incident_closing(self):
        policy = RealEstatePolicy()
        case = make_case("Final closing walkthrough")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.CLOSING

    def test_classify_incident_dispute(self):
        policy = RealEstatePolicy()
        case = make_case("Property dispute with neighbor")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.DISPUTE

    def test_classify_incident_maintenance(self):
        policy = RealEstatePolicy()
        case = make_case("Maintenance repair needed")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.MAINTENANCE

    def test_classify_incident_compliance(self):
        policy = RealEstatePolicy()
        case = make_case("Check building compliance")
        assert policy.classify_incident_type(case) == RealEstateIncidentType.COMPLIANCE

    def test_get_recommended_actions(self):
        policy = RealEstatePolicy()
        actions = policy.get_recommended_actions(RealEstateIncidentType.VALUATION)
        assert len(actions) > 0
        assert any("appraisal" in a.lower() for a in actions)


class TestRealEstateAutomationPolicy:
    def test_domain_name(self):
        policy = RealEstateAutomationPolicy()
        assert policy.domain_name == "real_estate"

    def test_assess_risk_low(self):
        policy = RealEstateAutomationPolicy()
        case = make_case("Standard property inquiry")
        assessment = policy.assess_risk(
            case,
            {"urgency": "LOW"},
            "valid",
            "sufficient",
            0.9,
        )
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.automation_decision == AutomationDecision.AUTO_APPROVE

    def test_assess_risk_critical(self):
        policy = RealEstateAutomationPolicy()
        case = make_case("Emergency property issue")
        assessment = policy.assess_risk(
            case,
            {"urgency": "CRITICAL"},
            "valid",
            "sufficient",
            0.9,
        )
        assert assessment.risk_level == RiskLevel.CRITICAL
        assert assessment.automation_decision == AutomationDecision.ESCALATE

    def test_assess_risk_validation_failed(self):
        policy = RealEstateAutomationPolicy()
        case = make_case("Property listing")
        assessment = policy.assess_risk(
            case,
            {"urgency": "LOW"},
            "invalid",
            "sufficient",
            0.9,
        )
        assert assessment.risk_level == RiskLevel.HIGH

    def test_assess_risk_low_confidence(self):
        policy = RealEstateAutomationPolicy()
        case = make_case("Property valuation")
        assessment = policy.assess_risk(
            case,
            {"urgency": "LOW"},
            "valid",
            "sufficient",
            0.4,
        )
        assert assessment.requires_hitl is True

    def test_get_risk_factors(self):
        policy = RealEstateAutomationPolicy()
        factors = policy.get_risk_factors()
        assert "urgency_level" in factors
        assert "confidence_score" in factors

    def test_get_automation_rules(self):
        policy = RealEstateAutomationPolicy()
        rules = policy.get_automation_rules()
        assert rules["domain"] == "real_estate"
        assert "auto_approve_conditions" in rules


class TestEnums:
    def test_property_types(self):
        assert PropertyType.RESIDENTIAL.value == "residential"
        assert PropertyType.COMMERCIAL.value == "commercial"

    def test_transaction_types(self):
        assert TransactionType.SALE.value == "sale"
        assert TransactionType.LEASE.value == "lease"

    def test_incident_types(self):
        assert RealEstateIncidentType.VALUATION.value == "valuation"
        assert RealEstateIncidentType.INSPECTION.value == "inspection"

    def test_urgency_levels(self):
        assert RealEstateUrgency.LOW.value == "LOW"
        assert RealEstateUrgency.CRITICAL.value == "CRITICAL"
