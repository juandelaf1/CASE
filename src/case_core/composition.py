from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)

from case_core.application.engine import TriageEngine  # noqa: E402
from case_core.domain.infrastructure_automation import InfrastructureAutomationPolicy  # noqa: E402
from case_core.domain.infrastructure_policy import InfrastructurePolicy  # noqa: E402
from case_core.domain.logistics_automation import LogisticsAutomationPolicy  # noqa: E402
from case_core.domain.logistics_policy import LogisticsPolicy  # noqa: E402
from case_core.domain.registry import DomainRegistry  # noqa: E402
from case_core.domain.seismic_automation import SeismicAutomationPolicy  # noqa: E402
from case_core.domain.seismic_policy import SeismicRiskPolicy  # noqa: E402
from case_core.domain.urban_automation import UrbanAutomationPolicy  # noqa: E402
from case_core.domain.urban_policy import UrbanPolicy  # noqa: E402
from case_core.evaluation.cost import CostModel  # noqa: E402
from case_core.ports.automation import AutomationPolicy  # noqa: E402
from case_core.ports.llm import LLMProvider  # noqa: E402
from case_core.providers.circuit_breaker import CircuitBreakerProvider  # noqa: E402
from case_core.providers.cloud import CloudProvider  # noqa: E402
from case_core.providers.groq import GroqProvider  # noqa: E402
from case_core.providers.mock import MockProvider  # noqa: E402
from case_core.providers.ollama import OllamaProvider  # noqa: E402
from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter  # noqa: E402
from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository  # noqa: E402

_LOGISTICS_AUTOMATION = LogisticsAutomationPolicy()
_URBAN_AUTOMATION = UrbanAutomationPolicy()
_INFRASTRUCTURE_AUTOMATION = InfrastructureAutomationPolicy()
_SEISMIC_AUTOMATION = SeismicAutomationPolicy()

_AUTOMATION_POLICIES: dict[str, AutomationPolicy] = {
    "logistics": _LOGISTICS_AUTOMATION,
    "urban_operations": _URBAN_AUTOMATION,
    "infrastructure": _INFRASTRUCTURE_AUTOMATION,
    "seismic_risk": _SEISMIC_AUTOMATION,
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
    provider: LLMProvider
    providers: dict[str, LLMProvider]
    cost_model: CostModel


def _resolve_provider() -> LLMProvider:
    provider_name = os.environ.get("CASE_PROVIDER", "mock").lower()
    providers = _resolve_all_providers()
    return providers.get(provider_name) or providers["mock"]


def _resolve_all_providers() -> dict[str, LLMProvider]:
    failure_threshold = int(os.environ.get("CASE_CB_FAILURE_THRESHOLD", "5"))
    recovery_timeout = int(os.environ.get("CASE_CB_RECOVERY_TIMEOUT", "30"))

    raw_providers: dict[str, LLMProvider] = {
        "groq": GroqProvider(),
        "ollama": OllamaProvider(),
        "mock": MockProvider(),
    }
    if os.environ.get("CASE_CLOUD_API_KEY"):
        raw_providers["cloud"] = CloudProvider()

    providers: dict[str, LLMProvider] = {}
    for name, provider in raw_providers.items():
        providers[name] = CircuitBreakerProvider(
            provider,
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout,
        )
    return providers


def create_app_dependencies() -> AppDependencies:
    registry = DomainRegistry()
    registry.register(UrbanPolicy())
    registry.register(LogisticsPolicy())
    registry.register(InfrastructurePolicy())
    registry.register(SeismicRiskPolicy())

    providers = _resolve_all_providers()
    provider: LLMProvider = _resolve_provider()
    cost_model = CostModel()
    db_path = _get_db_path()
    audit_adapter = SQLiteAuditAdapter(db_path=db_path)
    decision_repo = SQLiteDecisionRepository(db_path=db_path)

    engine = TriageEngine(
        domain_registry=registry,
        provider=provider,
        providers=providers,
        audit_port=audit_adapter,
        decision_repository=decision_repo,
        automation_policy_fn=_resolve_automation_policy,
        cost_model=cost_model,
    )

    return AppDependencies(
        engine=engine,
        registry=registry,
        audit_adapter=audit_adapter,
        decision_repo=decision_repo,
        provider=provider,
        providers=providers,
        cost_model=cost_model,
    )
