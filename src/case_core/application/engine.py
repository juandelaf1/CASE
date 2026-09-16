from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from case_core.contracts.audit import AuditEvent
from case_core.contracts.decision import AIProposal, TriageDecision
from case_core.contracts.error import CASEError, ErrorCategory
from case_core.contracts.lifecycle import ProcessingLifecycle
from case_core.contracts.operational_case import OperationalCase
from case_core.domain.registry import DomainRegistry
from case_core.evaluation.cost import CostModel
from case_core.ports.audit import AuditPort
from case_core.ports.automation import AutomationPolicy
from case_core.ports.decision_repository import DecisionRepositoryPort
from case_core.ports.domain import DomainPolicy
from case_core.ports.llm import LLMProvider
from case_core.prompts.builder import PromptBuilder
from case_core.react import execute_react
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
        automation_policy_fn: Callable[[str], AutomationPolicy | None] | None = None,
        cost_model: CostModel | None = None,
        time_fn: Any = None,
    ) -> None:
        self._domain_registry = domain_registry
        self._provider = provider
        self._audit_port = audit_port
        self._decision_repository = decision_repository
        self._automation_policy_fn = automation_policy_fn
        self._cost_model = cost_model
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
        engine_start = self._time_fn()

        case.status = ProcessingLifecycle.PROMPT_BUILDING
        result.processing_lifecycle = ProcessingLifecycle.PROMPT_BUILDING

        react_trace = execute_react(case, domain_policy.get_domain_context())

        builder = PromptBuilder(domain_policy=domain_policy)
        llm_request = builder.build(case)

        case.status = ProcessingLifecycle.PROVIDING
        result.processing_lifecycle = ProcessingLifecycle.PROVIDING

        llm_response = await self._provider.complete(llm_request)

        if llm_response.finish_reason in ("error", "timeout", "authentication_error", "provider_unavailable"):
            terminal_errors = {
                "error": (ErrorCategory.SYSTEM, "Provider returned error"),
                "timeout": (ErrorCategory.TRANSIENT, "Provider timeout"),
                "authentication_error": (ErrorCategory.AUTHENTICATION, "Authentication failed"),
                "provider_unavailable": (ErrorCategory.TRANSIENT, "Provider unavailable"),
            }
            cat, msg = terminal_errors.get(llm_response.finish_reason, (ErrorCategory.SYSTEM, "Provider error"))
            detail = llm_response.metadata.get("detail", "") if llm_response.metadata else ""
            rate_limit = llm_response.finish_reason == "error" and llm_response.metadata and llm_response.metadata.get("status_code") == 429
            provider_err = CASEError(
                category=cat,
                message=f"{msg}: {detail}" if detail else msg,
                recoverable=rate_limit or llm_response.finish_reason in ("timeout", "provider_unavailable"),
                retryable=rate_limit or llm_response.finish_reason in ("timeout", "provider_unavailable"),
                details={"requires_manual_review": not rate_limit, "finish_reason": llm_response.finish_reason},
            )
            case.status = ProcessingLifecycle.TERMINAL_FAILURE
            result.error = provider_err
            result.processing_lifecycle = ProcessingLifecycle.TERMINAL_FAILURE
            await self._emit_audit(case, "PROVIDER_ERROR", {"finish_reason": llm_response.finish_reason, "detail": detail})
            return result

        case.status = ProcessingLifecycle.PARSING_RESPONSE
        result.processing_lifecycle = ProcessingLifecycle.PARSING_RESPONSE

        pipeline = ReliabilityPipeline(
            domain_policy=domain_policy,
            audit_port=self._audit_port,
            time_fn=self._time_fn,
            automation_policy=self._automation_policy_fn(case.domain) if self._automation_policy_fn else None,
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

        decision.original_ai_proposal = AIProposal(
            action=decision.action,
            reason=decision.reason,
            urgency=decision.urgency,
            confidence=decision.confidence,
            evidence_summary=decision.evidence_summary,
            decision_rationale=decision.decision_rationale,
            decision_factors=decision.decision_factors,
            summary=decision.summary,
        )

        decision.processing_time_ms = (self._time_fn() - engine_start) * 1000

        decision.metadata["provider_info"] = {
            "provider": llm_response.provider,
            "model": llm_response.model,
            "prompt_tokens": llm_response.usage.prompt_tokens,
            "completion_tokens": llm_response.usage.completion_tokens,
            "total_tokens": llm_response.usage.total_tokens,
            "latency_ms": llm_response.latency_ms,
            "finish_reason": llm_response.finish_reason,
        }

        decision.metadata["react_trace"] = react_trace.to_dict()

        if self._cost_model:
            cost_estimate = self._cost_model.estimate(
                llm_response.provider,
                llm_response.model,
                llm_response.usage,
            )
            decision.metadata["cost"] = cost_estimate.model_dump()

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
