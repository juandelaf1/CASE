"""
CASE Demo — Human-in-the-Loop (HITL) Lifecycle Workflow

Demonstrates decision state transitions:
AI_PROPOSED -> UNDER_REVIEW -> MODIFIED / APPROVED
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from case_core.composition import create_app_dependencies
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.lifecycle import DecisionLifecycle
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel


async def main():
    deps = create_app_dependencies()
    engine = deps.engine
    decision_repo = deps.decision_repo
    audit_adapter = deps.audit_adapter

    case = OperationalCase(
        case_id="TEST-MOCK-02-HITL",
        report_text="Package delayed in transit due to weather. Customer requesting full refund.",
        domain="logistics",
        urgency=UrgencyLevel.HIGH,
        evidence=[
            EvidenceItem(
                id="ev-hitl-1",
                type=EvidenceType.TEXT,
                content="Weather delay confirmed",
                source="tracking",
                confidence=0.85,
                extracted_at="2026-09-11T10:00:00Z",
            )
        ],
    )

    print("=" * 70)
    print("CASE Demo — Human-In-The-Loop (HITL) Lifecycle Workflow")
    print("=" * 70)

    # Step 1: AI Proposal
    print("\n[Step 1] Executing CASE Triage Engine...")
    result = await engine.execute(case)
    decision = result.decision
    print(f"  AI Proposed Action:    {decision.action}")
    print(f"  AI Lifecycle State:    {decision.lifecycle.value}")
    print(f"  Decision ID:           {decision.decision_id}")

    # Step 2: Transition to UNDER_REVIEW
    print("\n[Step 2] Human Operator opens case for review...")
    await decision_repo.update_lifecycle(
        decision.decision_id,
        DecisionLifecycle.UNDER_REVIEW.value,
        actor="operator_jane",
        justification="Reviewing evidence details",
    )
    updated = await decision_repo.get_decision(decision.decision_id)
    print(f"  New Lifecycle State:    {updated.lifecycle.value}")

    # Step 3: Human Override / Modify
    print("\n[Step 3] Operator overrides decision from 'reject' to 'approve' with override note...")
    updated.action = "approve"
    updated.reason = "Approved voucher override for loyal customer despite delay"
    updated.lifecycle = DecisionLifecycle.MODIFIED
    await decision_repo.save_decision(updated)

    final = await decision_repo.get_decision(decision.decision_id)
    print(f"  Final Action:          {final.action}")
    print(f"  Final Lifecycle State: {final.lifecycle.value}")
    print(f"  Modified Reason:       {final.reason}")

    # Step 4: Audit trail
    events = await audit_adapter.get_events_by_case(case.case_id)
    print(f"\n[Step 4] Audit Trail ({len(events)} events recorded):")
    for e in events:
        print(f"  - [{e.timestamp}] {e.event_type} by actor={e.actor}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
