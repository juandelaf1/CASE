from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from case_core.contracts.audit import AuditEvent
from case_core.contracts.decision import AIProposal, TriageDecision
from case_core.contracts.error import CASEError, ErrorCategory
from case_core.contracts.lifecycle import DecisionLifecycle, ProcessingLifecycle
from case_core.contracts.operational_case import OperationalCase
from case_core.domain.registry import DomainRegistry
from case_core.ports.audit import AuditPort
from case_core.ports.decision_repository import DecisionRepositoryPort
from case_core.ports.domain import DomainPolicy
from case_core.ports.llm import LLMProvider
from case_core.prompts.builder import PromptBuilder
from case_core.reliability.pipeline import ReliabilityPipeline


@dataclass
class TriageResult:
    decision: TriageDecision | None = None
    error: CASEError | None = None
    processing_lifecycle: ProcessingLifecycle = ProcessingLifecycle.RECEIVED


class TriageEngine:
    """Application-layer orchestrator for CASE triage execution.

    Responsibilities:
    - Domain resolution via DomainRegistry
    - Prompt construction via PromptBuilder
    - LLM invocation via LLMProvider port
    - Validation pipeline via ReliabilityPipeline (not duplicated)
    - Automation assessment (delegated to pipeline)
    - Decision construction and AIProposal creation
    - Decision persistence via DecisionRepositoryPort
    - Audit logging via AuditPort

    Does NOT contain:
    - Domain-specific logic (no if domain == "logistics")
    - Duplicate validation/retry logic
    - HTTP/transport concerns
    """

    def __init__(
        self,
        domain_registry: DomainRegistry,
        provider: LLMProvider,
        audit_port: AuditPort | None = None,
        decision_repository: DecisionRepositoryPort | None = None,
        time_fn: Any = None,
    ) -> None:
        self._domain_registry = domain_registry
        self._provider = provider
        self._audit_port = audit_port
        self._decision_repository = decision_repository
        self._time_fn = time_fn or time.time

    async def execute(self, case: OperationalCase) -> TriageResult:
        result = TriageResult(processing_lifecycle=ProcessingLifecycle.RECEIVED)

        await self._emit_audit(case, "CASE_RECEIVED", {"domain": case.domain})

        domain_policy = self._domain_registry.get(case.domain)
        if domain_policy is None:
            result.error = CASEError(
                category=ErrorCategory.DOMAIN_VALIDATION,
                message=f"Unknown domain: {case.domain}. Valid domains: {self._domain_registry.list_domains()}",
                recoverable=False,
                retryable=False,
            )
            result.processing_lifecycle = ProcessingLifecycle.TERMINAL_FAILURE
            return result

        try:
            return await self._execute_triage(case, domain_policy, result)
        except Exception as e:
            result.error = CASEError(
                category=ErrorCategory.SYSTEM,
                message=f"Unexpected error: {e}",
                recoverable=False,
                retryable=False,
            )
            result.processing_lifecycle = ProcessingLifecycle.TERMINAL_FAILURE
            return result

    async def _execute_triage(
        self,
        case: OperationalCase,
        domain_policy: DomainPolicy,
        result: TriageResult,
    ) -> TriageResult:
        case.status = ProcessingLifecycle.PROMPT_BUILDING
        result.processing_lifecycle = ProcessingLifecycle.PROMPT_BUILDING

        builder = PromptBuilder(domain_policy=domain_policy)
        llm_request = builder.build(case)

        case.status = ProcessingLifecycle.PROVIDING
        result.processing_lifecycle = ProcessingLifecycle.PROVIDING

        llm_response = await self._provider.complete(llm_request)

        case.status = ProcessingLifecycle.PARSING_RESPONSE
        result.processing_lifecycle = ProcessingLifecycle.PARSING_RESPONSE

        pipeline = ReliabilityPipeline(
            domain_policy=domain_policy,
            audit_port=self._audit_port,
            time_fn=self._time_fn,
        )

        decision, err = await pipeline.run(
            llm_response.raw_output,
            case,
            provider=self._provider,
            llm_request=llm_request,
        )

        if err is not None:
            case.status = ProcessingLifecycle.TERMINAL_FAILURE
            result.error = err
            result.processing_lifecycle = ProcessingLifecycle.TERMINAL_FAILURE
            return result

        if decision is None:
            case.status = ProcessingLifecycle.TERMINAL_FAILURE
            result.error = CASEError(
                category=ErrorCategory.SYSTEM,
                message="No decision produced",
                recoverable=False,
                retryable=False,
            )
            result.processing_lifecycle = ProcessingLifecycle.TERMINAL_FAILURE
            return result

        case.status = ProcessingLifecycle.COMPLETED
        case.decision = decision
        result.processing_lifecycle = ProcessingLifecycle.COMPLETED

        decision.lifecycle = DecisionLifecycle.AI_PROPOSED
        decision.original_ai_proposal = AIProposal(
            action=decision.action,
            reason=decision.reason,
            urgency=decision.urgency,
            confidence=decision.confidence,
            evidence_summary=decision.evidence_summary,
        )

        if self._decision_repository is not None:
            await self._decision_repository.save_decision(decision)

        result.decision = decision
        return result

    async def _emit_audit(
        self,
        case: OperationalCase,
        event_type: str,
        details: dict[str, Any],
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
