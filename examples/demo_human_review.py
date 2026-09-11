"""
CASE Demo — HUMAN_REVIEW scenario

Ambiguous case with mixed evidence.
Expected outcome: HUMAN_REVIEW (medium risk, ambiguous evidence)
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
        case_id="TEST-MOCK-02-DEMO",
        report_text="Warehouse inventory discrepancy detected. Possible causes: system error, theft, or miscount. Requires investigation.",
        domain="logistics",
        urgency=UrgencyLevel.HIGH,
        evidence=[
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.TEXT,
                content="Inventory count mismatch: expected 500, found 487",
                source="warehouse_system",
                confidence=0.80,
                extracted_at="2026-09-11T10:00:00Z",
            ),
        ],
    )

    print("=" * 60)
    print("CASE Demo — HUMAN_REVIEW Scenario")
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
    is_human = d.action in ("reject", "escalate") or d.lifecycle.value in ("AI_PROPOSED",)
    print(f"Expected:   HUMAN_REVIEW (reject/escalate/low-confidence)")
    print(f"Match:      {'YES' if is_human else 'CHECK'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
