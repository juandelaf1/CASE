"""
CASE Demo — ESCALATE scenario

Critical case requiring supervisor attention.
Expected outcome: ESCALATE (critical risk, emergency keywords)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from case_core.composition import create_app_dependencies
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel


async def main():
    deps = create_app_dependencies()
    engine = deps.engine

    case = OperationalCase(
        case_id="TEST-MOCK-03-DEMO",
        report_text="CRITICAL: Warehouse fire has damaged inventory. Emergency reshipment required for critical orders. Multiple suppliers affected.",
        domain="logistics",
        urgency=UrgencyLevel.CRITICAL,
        evidence=[
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.TEXT,
                content="Fire damage confirmed by on-site inspector. Estimated 40% inventory loss.",
                source="inspector_report",
                confidence=0.95,
                extracted_at="2026-09-11T10:00:00Z",
            ),
            EvidenceItem(
                id="ev-002",
                type=EvidenceType.METRIC,
                content="inventory_loss_40_percent",
                source="damage_assessment",
                confidence=0.90,
                extracted_at="2026-09-11T10:00:00Z",
            ),
        ],
    )

    print("=" * 60)
    print("CASE Demo — ESCALATE Scenario")
    print("=" * 60)
    print(f"Case ID:    {case.case_id}")
    print(f"Domain:     {case.domain}")
    print(f"Urgency:    {case.urgency.value}")
    print(f"Evidence:   {len(case.evidence)} items")
    print("-" * 60)

    result = await engine.execute(case)

    if result.error:
        print(f"ERROR: {result.error.message}")
        print(f"Category: {result.error.category.value}")
        return

    d = result.decision
    print(f"Decision:   {d.action}")
    print(f"Reason:     {d.reason}")
    print(f"Urgency:    {d.urgency}")
    print(f"Confidence: {d.confidence}")
    print(f"Lifecycle:  {d.lifecycle.value}")
    print(f"Summary:    {d.evidence_summary}")
    print("-" * 60)
    print(f"Expected:   ESCALATE (critical urgency, high risk)")
    print(f"Match:      {'YES' if d.action == 'escalate' else 'CHECK'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
