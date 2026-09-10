from enum import Enum
from typing import Any

from pydantic import BaseModel


class AutomationDecision(str, Enum):
    AUTO_APPROVE = "auto_approve"
    HUMAN_REVIEW = "human_review"
    ESCALATE = "escalate"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskAssessment(BaseModel):
    decision_id: str
    case_id: str
    domain: str
    risk_level: RiskLevel
    automation_decision: AutomationDecision
    confidence: float
    factors: list[str]
    requires_hitl: bool
    policy_violations: list[str]
    evidence_quality: str
    validation_status: str
    justification: str

    def model_dump_ext(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "domain": self.domain,
            "risk_level": self.risk_level.value,
            "automation_decision": self.automation_decision.value,
            "confidence": self.confidence,
            "factors": self.factors,
            "requires_hitl": self.requires_hitl,
            "policy_violations": self.policy_violations,
            "evidence_quality": self.evidence_quality,
            "validation_status": self.validation_status,
            "justification": self.justification,
        }
