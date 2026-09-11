from __future__ import annotations

from dataclasses import dataclass

from case_core.application.engine import TriageEngine
from case_core.domain.default_automation import DefaultAutomationPolicy
from case_core.domain.infrastructure_policy import InfrastructurePolicy
from case_core.domain.logistics_automation import LogisticsAutomationPolicy
from case_core.domain.logistics_policy import LogisticsPolicy
from case_core.domain.registry import DomainRegistry
from case_core.domain.urban_policy import UrbanPolicy
from case_core.ports.automation import AutomationPolicy
from case_core.ports.llm import LLMProvider
from case_core.providers.mock import MockProvider
from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository


_LOGISTICS_AUTOMATION = LogisticsAutomationPolicy()
_DEFAULT_AUTOMATION = DefaultAutomationPolicy()

_AUTOMATION_POLICIES: dict[str, AutomationPolicy] = {
    "logistics": _LOGISTICS_AUTOMATION,
    "urban_operations": _DEFAULT_AUTOMATION,
    "infrastructure": _DEFAULT_AUTOMATION,
}


def _resolve_automation_policy(domain: str) -> AutomationPolicy | None:
    return _AUTOMATION_POLICIES.get(domain)


@dataclass
class AppDependencies:
    engine: TriageEngine
    registry: DomainRegistry
    audit_adapter: SQLiteAuditAdapter
    decision_repo: SQLiteDecisionRepository


def create_app_dependencies() -> AppDependencies:
    registry = DomainRegistry()
    registry.register(UrbanPolicy())
    registry.register(LogisticsPolicy())
    registry.register(InfrastructurePolicy())

    provider: LLMProvider = MockProvider()
    audit_adapter = SQLiteAuditAdapter()
    decision_repo = SQLiteDecisionRepository()

    engine = TriageEngine(
        domain_registry=registry,
        provider=provider,
        audit_port=audit_adapter,
        decision_repository=decision_repo,
        automation_policy_fn=_resolve_automation_policy,
    )

    return AppDependencies(
        engine=engine,
        registry=registry,
        audit_adapter=audit_adapter,
        decision_repo=decision_repo,
    )
