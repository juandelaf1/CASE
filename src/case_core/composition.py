from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from case_core.application.engine import TriageEngine
from case_core.domain.default_automation import DefaultAutomationPolicy
from case_core.domain.infrastructure_policy import InfrastructurePolicy
from case_core.domain.logistics_automation import LogisticsAutomationPolicy
from case_core.domain.logistics_policy import LogisticsPolicy
from case_core.domain.registry import DomainRegistry
from case_core.domain.urban_policy import UrbanPolicy
from case_core.ports.automation import AutomationPolicy
from case_core.ports.llm import LLMProvider
from case_core.providers.cloud import CloudProvider
from case_core.providers.groq import GroqProvider
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


def _get_db_path() -> str:
    db_path = os.environ.get("CASE_DB_PATH", "case_audit.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_path


@dataclass
class AppDependencies:
    engine: TriageEngine
    registry: DomainRegistry
    audit_adapter: SQLiteAuditAdapter
    decision_repo: SQLiteDecisionRepository


def _resolve_provider() -> LLMProvider:
    provider_name = os.environ.get("CASE_PROVIDER", "mock").lower()

    if provider_name == "groq":
        return GroqProvider()
    elif provider_name == "cloud":
        return CloudProvider()
    elif provider_name == "ollama":
        from case_core.providers.ollama import OllamaProvider

        return OllamaProvider()
    else:
        return MockProvider()


def create_app_dependencies() -> AppDependencies:
    registry = DomainRegistry()
    registry.register(UrbanPolicy())
    registry.register(LogisticsPolicy())
    registry.register(InfrastructurePolicy())

    provider: LLMProvider = _resolve_provider()
    db_path = _get_db_path()
    audit_adapter = SQLiteAuditAdapter(db_path=db_path)
    decision_repo = SQLiteDecisionRepository(db_path=db_path)

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
