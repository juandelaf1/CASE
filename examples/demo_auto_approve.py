"""
CASE Demo — AUTO_APPROVE scenario

Low-risk logistics case with sufficient evidence.
Expected outcome: AUTO_APPROVE (low risk, valid schema, high confidence)
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
        case_id="TEST-MOCK-08-AUTO",
        report_text="Routine logistics warehouse checklist completed successfully. All standard parameters within limits.",
        domain="logistics",
        urgency=UrgencyLevel.LOW,
        evidence=[
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.TEXT,
                content="Standard checklist signed and completed",
                source="warehouse_app",
                confidence=0.92,
                extracted_at="2026-09-11T10:00:00Z",
            ),
            EvidenceItem(
                id="ev-002",
                type=EvidenceType.METRIC,
                content="verification_score_100",
                source="audit_system",
                confidence=0.95,
                extracted_at="2026-09-11T10:00:00Z",
            ),
        ],
    )

    print("=" * 60)
    print("CASE Demo — AUTO_APPROVE Scenario")
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
    print(f"Expected:   AUTO_APPROVE (lifecycle: approved)")
    print(f"Match:      {'YES' if d.lifecycle.value == 'approved' else 'NO'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
