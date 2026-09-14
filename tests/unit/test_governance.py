"""Tests for Advanced Governance and Security — Phase 7."""

from case_core.governance import (
    AccessPolicy,
    AccessRole,
    ComplianceFramework,
    ComplianceManager,
    ComplianceRecord,
    GovernanceConfig,
    GovernanceFramework,
    SecurityEvent,
    SecurityLevel,
    SecurityManager,
)


class TestSecurityManager:
    def test_log_security_event(self):
        manager = SecurityManager()
        event = manager.log_security_event(
            event_type="login",
            severity="info",
            source="auth",
            details={"ip": "127.0.0.1"},
        )
        assert event.event_type == "login"
        assert event.severity == "info"

    def test_get_security_events_by_type(self):
        manager = SecurityManager()
        manager.log_security_event(event_type="login", severity="info", source="auth")
        manager.log_security_event(event_type="logout", severity="info", source="auth")
        events = manager.get_security_events(event_type="login")
        assert len(events) == 1

    def test_add_access_policy(self):
        manager = SecurityManager()
        policy = AccessPolicy(
            policy_id="test-policy",
            role=AccessRole.ANALYST,
            resource="cases",
            permissions=["read", "write"],
        )
        manager.add_access_policy(policy)
        assert len(manager._access_policies) == 1

    def test_check_access_allowed(self):
        manager = SecurityManager()
        manager.add_access_policy(AccessPolicy(
            policy_id="test",
            role=AccessRole.ANALYST,
            resource="cases",
            permissions=["read"],
        ))
        assert manager.check_access(AccessRole.ANALYST, "cases", "read") is True

    def test_check_access_denied(self):
        manager = SecurityManager()
        manager.add_access_policy(AccessPolicy(
            policy_id="test",
            role=AccessRole.VIEWER,
            resource="cases",
            permissions=["read"],
        ))
        assert manager.check_access(AccessRole.VIEWER, "cases", "write") is False

    def test_validate_password_valid(self):
        manager = SecurityManager()
        valid, issues = manager.validate_password("StrongP@ss123")
        assert valid is True
        assert len(issues) == 0

    def test_validate_password_too_short(self):
        manager = SecurityManager()
        valid, issues = manager.validate_password("Short1!")
        assert valid is False
        assert any("at least" in i for i in issues)

    def test_validate_password_no_uppercase(self):
        manager = SecurityManager()
        valid, issues = manager.validate_password("lowercase123!")
        assert valid is False
        assert any("uppercase" in i for i in issues)

    def test_validate_password_no_special(self):
        manager = SecurityManager()
        valid, issues = manager.validate_password("NoSpecial123")
        assert valid is False
        assert any("special" in i for i in issues)

    def test_get_security_summary(self):
        manager = SecurityManager()
        manager.log_security_event(event_type="login", severity="info", source="auth")
        summary = manager.get_security_summary()
        assert summary["total_events"] == 1


class TestComplianceManager:
    def test_add_compliance_record(self):
        manager = ComplianceManager()
        record = ComplianceRecord(
            record_id="rec-1",
            framework=ComplianceFramework.GDPR,
            control_id="GDPR-001",
            status="compliant",
            evidence=["consent_form.pdf"],
            timestamp="2026-01-01T00:00:00Z",
        )
        manager.add_compliance_record(record)
        assert len(manager._compliance_records) == 1

    def test_get_compliance_status(self):
        manager = ComplianceManager()
        manager.add_compliance_record(ComplianceRecord(
            record_id="rec-1",
            framework=ComplianceFramework.GDPR,
            control_id="GDPR-001",
            status="compliant",
            timestamp="2026-01-01T00:00:00Z",
        ))
        status = manager.get_compliance_status(ComplianceFramework.GDPR)
        assert status["total_controls"] == 1
        assert status["compliant"] == 1

    def test_validate_gdpr_compliant(self):
        manager = ComplianceManager()
        data = {
            "data_subject_consent": True,
            "data_processing_purpose": "case_analysis",
            "data_retention_period": "365_days",
        }
        compliant, issues = manager.validate_gdpr_requirements(data)
        assert compliant is True
        assert len(issues) == 0

    def test_validate_gdpr_missing_consent(self):
        manager = ComplianceManager()
        data = {
            "data_processing_purpose": "case_analysis",
            "data_retention_period": "365_days",
        }
        compliant, issues = manager.validate_gdpr_requirements(data)
        assert compliant is False
        assert any("consent" in i.lower() for i in issues)

    def test_get_overall_compliance(self):
        manager = ComplianceManager()
        overall = manager.get_overall_compliance()
        assert "gdpr" in overall
        assert "soc2" in overall


class TestGovernanceFramework:
    def test_initialize_default_policies(self):
        framework = GovernanceFramework()
        framework.initialize_default_policies()
        assert len(framework.security._access_policies) == 5

    def test_audit_decision(self):
        framework = GovernanceFramework()
        event = framework.audit_decision("dec-1", "approve", 0.9, "LOW")
        assert event.event_type == "decision_audit"
        assert event.details["decision"] == "approve"

    def test_audit_data_access(self):
        framework = GovernanceFramework()
        event = framework.audit_data_access("user-1", "cases", "read")
        assert event.event_type == "data_access"
        assert event.user_id == "user-1"

    def test_audit_security_violation(self):
        framework = GovernanceFramework()
        event = framework.audit_security_violation("unauthorized_access", {"ip": "10.0.0.1"})
        assert event.event_type == "security_violation"
        assert event.severity == "critical"

    def test_get_governance_status(self):
        framework = GovernanceFramework()
        status = framework.get_governance_status()
        assert status["security_level"] == "internal"
        assert "gdpr" in status["compliance_frameworks"]

    def test_check_access_with_default_policies(self):
        framework = GovernanceFramework()
        framework.initialize_default_policies()
        assert framework.security.check_access(AccessRole.ANALYST, "cases", "read") is True
        assert framework.security.check_access(AccessRole.VIEWER, "cases", "write") is False


class TestEnums:
    def test_security_levels(self):
        assert SecurityLevel.PUBLIC.value == "public"
        assert SecurityLevel.RESTRICTED.value == "restricted"

    def test_compliance_frameworks(self):
        assert ComplianceFramework.GDPR.value == "gdpr"
        assert ComplianceFramework.SOC2.value == "soc2"

    def test_access_roles(self):
        assert AccessRole.VIEWER.value == "viewer"
        assert AccessRole.ADMIN.value == "admin"


class TestModels:
    def test_governance_config_defaults(self):
        config = GovernanceConfig()
        assert config.security_level == SecurityLevel.INTERNAL
        assert config.require_mfa is True
        assert config.password_min_length == 12

    def test_security_event_creation(self):
        event = SecurityEvent(
            event_id="se-1",
            event_type="test",
            severity="info",
            source="test",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.event_id == "se-1"
        assert event.details == {}

    def test_compliance_record_creation(self):
        record = ComplianceRecord(
            record_id="rec-1",
            framework=ComplianceFramework.GDPR,
            control_id="GDPR-001",
            status="compliant",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert record.framework == ComplianceFramework.GDPR
        assert record.evidence == []

    def test_access_policy_creation(self):
        policy = AccessPolicy(
            policy_id="pol-1",
            role=AccessRole.ANALYST,
            resource="cases",
            permissions=["read", "write"],
        )
        assert policy.role == AccessRole.ANALYST
        assert len(policy.permissions) == 2
