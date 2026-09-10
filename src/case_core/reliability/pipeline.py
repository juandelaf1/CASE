import asyncio
import json
import time
from typing import Any

from case_core.contracts.audit import AuditEvent
from case_core.contracts.automation import AutomationDecision, RiskAssessment
from case_core.contracts.decision import TriageDecision
from case_core.contracts.error import CASEError, ErrorCategory
from case_core.contracts.lifecycle import DecisionLifecycle, ProcessingLifecycle
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.audit import AuditPort
from case_core.ports.automation import AutomationPolicy
from case_core.ports.domain import DomainPolicy
from case_core.reliability.automation import AutomationEvaluator

MAX_VALIDATION_RETRIES = 3
MAX_TRANSIENT_RETRIES = 2
BACKOFF_BASE_SECONDS = 1
TOTAL_TIMEOUT_SECONDS = 30

DECISION_FIELDS = {"decision", "reason", "urgency", "confidence", "evidence_summary"}
VALID_DECISIONS = {"approve", "reject", "escalate"}
VALID_URGENCIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _backoff(attempt: int) -> float:
    return BACKOFF_BASE_SECONDS * (2 ** attempt)


class ReliabilityPipeline:
    def __init__(
        self,
        domain_policy: DomainPolicy,
        audit_port: AuditPort | None = None,
        time_fn: Any = None,
        automation_policy: AutomationPolicy | None = None,
    ) -> None:
        self._domain_policy = domain_policy
        self._audit_port = audit_port
        self._time_fn = time_fn or time.time
        self._automation_policy = automation_policy
        self._automation_evaluator = (
            AutomationEvaluator(automation_policy) if automation_policy else None
        )

    async def _emit_audit(
        self,
        case: OperationalCase,
        event_type: str,
        details: dict,
        decision_id: str | None = None,
    ) -> None:
        if self._audit_port is None:
            return
        event = AuditEvent(
            event_id=f"ae-{case.case_id}-{event_type}-{int(self._time_fn() * 1000)}",
            case_id=case.case_id,
            decision_id=decision_id,
            event_type=event_type,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._time_fn())),
            details=details,
        )
        await self._audit_port.log_event(event)

    def parse(self, raw_content: str) -> tuple[dict | None, CASEError | None]:
        try:
            data = json.loads(raw_content)
            return data, None
        except json.JSONDecodeError as e:
            return None, CASEError(
                category=ErrorCategory.PARSING,
                message=f"Invalid JSON: {e}",
                recoverable=True,
                retryable=True,
            )

    def schema_validate(self, data: dict) -> tuple[dict | None, CASEError | None]:
        missing = DECISION_FIELDS - set(data.keys())
        if missing:
            return None, CASEError(
                category=ErrorCategory.SCHEMA_VALIDATION,
                message=f"Missing required fields: {missing}",
                recoverable=True,
                retryable=True,
            )

        if data["decision"] not in VALID_DECISIONS:
            return None, CASEError(
                category=ErrorCategory.SCHEMA_VALIDATION,
                message=f"Invalid decision: {data['decision']}",
                recoverable=True,
                retryable=True,
            )

        if data["urgency"] not in VALID_URGENCIES:
            return None, CASEError(
                category=ErrorCategory.SCHEMA_VALIDATION,
                message=f"Invalid urgency: {data['urgency']}",
                recoverable=True,
                retryable=True,
            )

        if not isinstance(data["confidence"], (int, float)):
            return None, CASEError(
                category=ErrorCategory.SCHEMA_VALIDATION,
                message="Confidence must be a number",
                recoverable=True,
                retryable=False,
            )

        if not (0.0 <= data["confidence"] <= 1.0):
            return None, CASEError(
                category=ErrorCategory.SEMANTIC_VALIDATION,
                message=f"Confidence {data['confidence']} out of range [0.0, 1.0]",
                recoverable=True,
                retryable=False,
            )

        return data, None

    def semantic_validate(self, data: dict) -> tuple[dict | None, CASEError | None]:
        if not data.get("reason") or len(data["reason"].strip()) < 10:
            return None, CASEError(
                category=ErrorCategory.SEMANTIC_VALIDATION,
                message="Reason too short or empty",
                recoverable=True,
                retryable=True,
            )

        if not data.get("evidence_summary") or len(data["evidence_summary"].strip()) < 5:
            return None, CASEError(
                category=ErrorCategory.SEMANTIC_VALIDATION,
                message="Evidence summary too short",
                recoverable=True,
                retryable=True,
            )

        return data, None

    def domain_validate(self, data: dict, case: OperationalCase) -> tuple[dict | None, CASEError | None]:
        ok, msg = self._domain_policy.validate_evidence(case.evidence)
        if not ok:
            return None, CASEError(
                category=ErrorCategory.DOMAIN_VALIDATION,
                message=f"Domain validation failed: {msg}",
                recoverable=False,
                retryable=False,
            )

        return data, None

    def validate_all(self, raw_content: str, case: OperationalCase) -> tuple[dict | None, CASEError | None]:
        data, err = self.parse(raw_content)
        if err:
            return None, err

        assert data is not None
        data, err = self.schema_validate(data)
        if err:
            return None, err

        assert data is not None
        data, err = self.semantic_validate(data)
        if err:
            return None, err

        assert data is not None
        data, err = self.domain_validate(data, case)
        if err:
            return None, err

        return data, None

    def assess_automation(
        self,
        case: OperationalCase,
        data: dict[str, Any],
        validation_passed: bool,
        confidence: float,
    ) -> RiskAssessment | None:
        if self._automation_evaluator is None:
            return None

        evidence_count = len(case.evidence)
        return self._automation_evaluator.evaluate(
            case=case,
            data=data,
            validation_passed=validation_passed,
            evidence_count=evidence_count,
            confidence=confidence,
        )

    def build_decision(
        self,
        data: dict,
        case: OperationalCase,
        processing_time_ms: float,
        automation_assessment: RiskAssessment | None = None,
    ) -> TriageDecision:
        metadata: dict[str, Any] = {}
        if automation_assessment:
            metadata["automation_assessment"] = automation_assessment.model_dump_ext()

        return TriageDecision(
            decision_id=f"dec-{case.case_id}",
            case_id=case.case_id,
            domain=case.domain,
            action=data["decision"],
            reason=data["reason"],
            urgency=data["urgency"],
            confidence=float(data["confidence"]),
            evidence_summary=data["evidence_summary"],
            lifecycle=DecisionLifecycle.AI_PROPOSED,
            processing_time_ms=processing_time_ms,
            metadata=metadata,
        )

    async def run(
        self,
        raw_content: str,
        case: OperationalCase,
        provider: Any = None,
        llm_request: Any = None,
    ) -> tuple[TriageDecision | None, CASEError | None]:
        start = self._time_fn()
        validation_attempts = 0
        transient_attempts = 0

        await self._emit_audit(case, "CASE_RECEIVED", {"domain": case.domain})

        data, err = self.validate_all(raw_content, case)
        if err is None:
            assert data is not None
            elapsed_ms = (self._time_fn() - start) * 1000

            automation_assessment = self.assess_automation(
                case=case,
                data=data,
                validation_passed=True,
                confidence=float(data["confidence"]),
            )

            decision = self.build_decision(data, case, elapsed_ms, automation_assessment)

            await self._emit_audit(
                case, "AI_GENERATED",
                {"action": decision.action, "confidence": decision.confidence},
                decision.decision_id,
            )

            if automation_assessment:
                await self._emit_audit(
                    case, "AUTOMATION_ASSESSED",
                    automation_assessment.model_dump_ext(),
                    decision.decision_id,
                )

                if automation_assessment.automation_decision == AutomationDecision.AUTO_APPROVE:
                    decision.lifecycle = DecisionLifecycle.APPROVED
                    await self._emit_audit(
                        case, "AUTO_APPROVED",
                        {"justification": automation_assessment.justification},
                        decision.decision_id,
                    )
                elif automation_assessment.automation_decision == AutomationDecision.ESCALATE:
                    decision.lifecycle = DecisionLifecycle.ESCALATED
                    await self._emit_audit(
                        case, "AUTO_ESCALATED",
                        {"justification": automation_assessment.justification},
                        decision.decision_id,
                    )
                else:
                    decision.lifecycle = DecisionLifecycle.UNDER_REVIEW
                    await self._emit_audit(
                        case, "AUTO_HUMAN_REVIEW",
                        {"justification": automation_assessment.justification},
                        decision.decision_id,
                    )

            await self._emit_audit(
                case, "FINAL_DECISION",
                {"action": decision.action, "lifecycle": decision.lifecycle.value},
                decision.decision_id,
            )
            return decision, None

        validation_attempts += 1

        while err is not None and err.retryable and validation_attempts < MAX_VALIDATION_RETRIES:
            await self._emit_audit(
                case, "VALIDATION_FAILED",
                {"category": err.category.value, "message": err.message, "attempt": validation_attempts},
            )
            await self._emit_audit(
                case, "REPAIR_TRIGGERED",
                {"attempt": validation_attempts, "backoff_seconds": _backoff(validation_attempts - 1)},
            )

            await asyncio.sleep(_backoff(validation_attempts - 1))

            if provider and llm_request:
                try:
                    llm_response = await asyncio.wait_for(
                        provider.complete(llm_request),
                        timeout=TOTAL_TIMEOUT_SECONDS - (self._time_fn() - start),
                    )
                    raw_content = llm_response.raw_output
                except TimeoutError:
                    await self._emit_audit(case, "PROVIDER_TIMEOUT", {"attempt": validation_attempts})
                    err = CASEError(
                        category=ErrorCategory.TRANSIENT,
                        message="Provider timeout",
                        recoverable=True,
                        retryable=True,
                    )
                    validation_attempts += 1
                    continue
                except Exception as e:
                    await self._emit_audit(case, "PROVIDER_ERROR", {"attempt": validation_attempts, "error": str(e)})
                    transient_attempts += 1
                    if transient_attempts >= MAX_TRANSIENT_RETRIES:
                        break
                    validation_attempts += 1
                    continue

            data, err = self.validate_all(raw_content, case)
            validation_attempts += 1

            if self._time_fn() - start >= TOTAL_TIMEOUT_SECONDS:
                await self._emit_audit(case, "TOTAL_TIMEOUT", {"elapsed_seconds": self._time_fn() - start})
                break

        if err is not None:
            elapsed_ms = (self._time_fn() - start) * 1000
            decision_id = f"dec-{case.case_id}-failed"
            await self._emit_audit(
                case, "HUMAN_REVIEW",
                {
                    "reason": err.message,
                    "category": err.category.value,
                    "validation_attempts": validation_attempts,
                    "transient_attempts": transient_attempts,
                },
                decision_id,
            )
            err.details = {
                "processing_lifecycle": ProcessingLifecycle.TERMINAL_FAILURE.value,
                "requires_manual_review": True,
                "validation_attempts": validation_attempts,
            }
            return None, err

        assert data is not None
        elapsed_ms = (self._time_fn() - start) * 1000

        automation_assessment = self.assess_automation(
            case=case,
            data=data,
            validation_passed=True,
            confidence=float(data["confidence"]),
        )

        decision = self.build_decision(data, case, elapsed_ms, automation_assessment)

        await self._emit_audit(
            case, "AI_GENERATED",
            {"action": decision.action, "confidence": decision.confidence},
            decision.decision_id,
        )

        if automation_assessment:
            await self._emit_audit(
                case, "AUTOMATION_ASSESSED",
                automation_assessment.model_dump_ext(),
                decision.decision_id,
            )

            if automation_assessment.automation_decision == AutomationDecision.AUTO_APPROVE:
                decision.lifecycle = DecisionLifecycle.APPROVED
                await self._emit_audit(
                    case, "AUTO_APPROVED",
                    {"justification": automation_assessment.justification},
                    decision.decision_id,
                )
            elif automation_assessment.automation_decision == AutomationDecision.ESCALATE:
                decision.lifecycle = DecisionLifecycle.ESCALATED
                await self._emit_audit(
                    case, "AUTO_ESCALATED",
                    {"justification": automation_assessment.justification},
                    decision.decision_id,
                )
            else:
                decision.lifecycle = DecisionLifecycle.UNDER_REVIEW
                await self._emit_audit(
                    case, "AUTO_HUMAN_REVIEW",
                    {"justification": automation_assessment.justification},
                    decision.decision_id,
                )

        await self._emit_audit(
            case, "FINAL_DECISION",
            {"action": decision.action, "lifecycle": decision.lifecycle.value},
            decision.decision_id,
        )
        return decision, None
