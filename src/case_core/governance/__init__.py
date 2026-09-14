"""Advanced Governance and Security — Phase 7."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecurityLevel(str, Enum):
    """Security levels for CASE operations."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


class AccessRole(str, Enum):
    """Roles for access control."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"
    AUDITOR = "auditor"


class SecurityEvent(BaseModel):
    """Security event for audit trail."""

    event_id: str
    event_type: str
    severity: str
    source: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    user_id: str | None = None


class ComplianceRecord(BaseModel):
    """Compliance record for regulatory requirements."""

    record_id: str
    framework: ComplianceFramework
    control_id: str
    status: str
    evidence: list[str] = Field(default_factory=list)
    timestamp: str


class AccessPolicy(BaseModel):
    """Access policy for role-based access control."""

    policy_id: str
    role: AccessRole
    resource: str
    permissions: list[str] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)


class GovernanceConfig(BaseModel):
    """Configuration for governance framework."""

    security_level: SecurityLevel = SecurityLevel.INTERNAL
    compliance_frameworks: list[ComplianceFramework] = Field(
        default_factory=lambda: [ComplianceFramework.GDPR, ComplianceFramework.SOC2]
    )
    audit_retention_days: int = 365
    max_session_duration_hours: int = 8
    require_mfa: bool = True
    password_min_length: int = 12
    session_timeout_minutes: int = 30


class SecurityManager:
    """Manages security operations for CASE."""

    def __init__(self, config: GovernanceConfig | None = None):
        self.config = config or GovernanceConfig()
        self._security_events: list[SecurityEvent] = []
        self._access_policies: list[AccessPolicy] = []

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        source: str,
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            event_id=f"se-{len(self._security_events) + 1}",
            event_type=event_type,
            severity=severity,
            source=source,
            details=details or {},
            timestamp="2026-01-01T00:00:00Z",
            user_id=user_id,
        )
        self._security_events.append(event)
        return event

    def get_security_events(
        self,
        event_type: str | None = None,
        severity: str | None = None,
    ) -> list[SecurityEvent]:
        events = self._security_events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]
        return events

    def add_access_policy(self, policy: AccessPolicy) -> None:
        self._access_policies.append(policy)

    def check_access(self, role: AccessRole, resource: str, action: str) -> bool:
        for policy in self._access_policies:
            if policy.role == role and policy.resource == resource:
                if action in policy.permissions:
                    return True
        return False

    def validate_password(self, password: str) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if len(password) < self.config.password_min_length:
            issues.append(f"Password must be at least {self.config.password_min_length} characters")
        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            issues.append("Password must contain at least one special character")
        return len(issues) == 0, issues

    def get_security_summary(self) -> dict[str, Any]:
        return {
            "total_events": len(self._security_events),
            "events_by_type": {},
            "events_by_severity": {},
            "access_policies_count": len(self._access_policies),
        }


class ComplianceManager:
    """Manages compliance operations for CASE."""

    def __init__(self, config: GovernanceConfig | None = None):
        self.config = config or GovernanceConfig()
        self._compliance_records: list[ComplianceRecord] = []

    def add_compliance_record(self, record: ComplianceRecord) -> None:
        self._compliance_records.append(record)

    def get_compliance_status(self, framework: ComplianceFramework) -> dict[str, Any]:
        records = [r for r in self._compliance_records if r.framework == framework]
        total = len(records)
        compliant = sum(1 for r in records if r.status == "compliant")
        return {
            "framework": framework.value,
            "total_controls": total,
            "compliant": compliant,
            "non_compliant": total - compliant,
            "compliance_rate": compliant / total if total > 0 else 0.0,
        }

    def get_overall_compliance(self) -> dict[str, Any]:
        statuses: dict[str, dict[str, Any]] = {}
        for framework in self.config.compliance_frameworks:
            statuses[framework.value] = self.get_compliance_status(framework)
        return statuses

    def validate_gdpr_requirements(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if not data.get("data_subject_consent"):
            issues.append("Missing data subject consent")
        if not data.get("data_processing_purpose"):
            issues.append("Missing data processing purpose")
        if not data.get("data_retention_period"):
            issues.append("Missing data retention period")
        if data.get("cross_border_transfer", False):
            if not data.get("adequate_protection", False):
                issues.append("Cross-border transfer without adequate protection")
        return len(issues) == 0, issues

    def get_compliance_summary(self) -> dict[str, Any]:
        return {
            "total_records": len(self._compliance_records),
            "frameworks": [f.value for f in self.config.compliance_frameworks],
            "overall_status": self.get_overall_compliance(),
        }


class GovernanceFramework:
    """Main governance framework for CASE."""

    def __init__(self, config: GovernanceConfig | None = None):
        self.config = config or GovernanceConfig()
        self.security = SecurityManager(self.config)
        self.compliance = ComplianceManager(self.config)

    def initialize_default_policies(self) -> None:
        self.security.add_access_policy(AccessPolicy(
            policy_id="viewer-policy",
            role=AccessRole.VIEWER,
            resource="cases",
            permissions=["read"],
        ))
        self.security.add_access_policy(AccessPolicy(
            policy_id="analyst-policy",
            role=AccessRole.ANALYST,
            resource="cases",
            permissions=["read", "create", "update"],
        ))
        self.security.add_access_policy(AccessPolicy(
            policy_id="manager-policy",
            role=AccessRole.MANAGER,
            resource="cases",
            permissions=["read", "create", "update", "delete", "approve"],
        ))
        self.security.add_access_policy(AccessPolicy(
            policy_id="admin-policy",
            role=AccessRole.ADMIN,
            resource="cases",
            permissions=["read", "create", "update", "delete", "approve", "configure"],
        ))
        self.security.add_access_policy(AccessPolicy(
            policy_id="auditor-policy",
            role=AccessRole.AUDITOR,
            resource="cases",
            permissions=["read", "audit"],
        ))

    def get_governance_status(self) -> dict[str, Any]:
        return {
            "security_level": self.config.security_level.value,
            "compliance_frameworks": [f.value for f in self.config.compliance_frameworks],
            "security_summary": self.security.get_security_summary(),
            "compliance_summary": self.compliance.get_compliance_summary(),
            "require_mfa": self.config.require_mfa,
            "audit_retention_days": self.config.audit_retention_days,
        }

    def audit_decision(self, decision_id: str, decision: str, confidence: float, risk_level: str) -> SecurityEvent:
        return self.security.log_security_event(
            event_type="decision_audit",
            severity="info",
            source="governance_framework",
            details={
                "decision_id": decision_id,
                "decision": decision,
                "confidence": confidence,
                "risk_level": risk_level,
            },
        )

    def audit_data_access(self, user_id: str, resource: str, action: str) -> SecurityEvent:
        return self.security.log_security_event(
            event_type="data_access",
            severity="info",
            source="governance_framework",
            details={"resource": resource, "action": action},
            user_id=user_id,
        )

    def audit_security_violation(self, violation_type: str, details: dict[str, Any]) -> SecurityEvent:
        return self.security.log_security_event(
            event_type="security_violation",
            severity="critical",
            source="governance_framework",
            details=details,
        )
