from __future__ import annotations

import pytest

from case_core.application.engine import TriageEngine
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.registry import DomainRegistry
from case_core.domain.supply_chain_disruption_policy import (
    SupplyChainDisruptionAutomation,
    SupplyChainDisruptionPolicy,
)
from case_core.providers.mock import MockProvider


def _case(text: str, urgency: UrgencyLevel = UrgencyLevel.HIGH) -> OperationalCase:
    return OperationalCase(
        case_id="SC-1",
        report_text=text,
        domain="supply_chain_disruption",
        urgency=urgency,
        evidence=[EvidenceItem(id="ev-1", type=EvidenceType.TEXT, content=text, source="ops", confidence=0.9, extracted_at="2026-01-01T00:00:00Z")],
    )


def test_policy_basics():
    p = SupplyChainDisruptionPolicy()
    ok, _ = p.validate_evidence(_case("port delay").evidence)
    assert ok
    assert p.classify_urgency(_case("critical port closed shutdown")) == "CRITICAL"
    assert p.classify_disruption_type(_case("customs clearance hold at border")) is not None


@pytest.mark.asyncio
async def test_supply_chain_disruption_runs_through_engine():
    registry = DomainRegistry()
    registry.register(SupplyChainDisruptionPolicy())
    engine = TriageEngine(
        domain_registry=registry,
        provider=MockProvider(),
        automation_policy_fn=lambda d: SupplyChainDisruptionAutomation() if d == "supply_chain_disruption" else None,
    )
    result = await engine.execute(_case("Supplier factory shutdown causes critical shortage"))
    assert result.error is None
    assert result.decision is not None
    assert result.decision.domain == "supply_chain_disruption"
