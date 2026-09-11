"""
CASE Demo — Invalid Output scenario

Case that triggers validation failure.
Expected outcome: Terminal failure or error (invalid LLM output handled gracefully)
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

    # MockProvider maps TEST-MOCK-03 to escalate response
    # This case uses a scenario that tests the pipeline's error handling
    case = OperationalCase(
        case_id="DEMO-INVALID-001",
        report_text=".",
        domain="logistics",
        urgency=UrgencyLevel.LOW,
        evidence=[],
    )

    print("=" * 60)
    print("CASE Demo — Invalid Output Scenario")
    print("=" * 60)
    print(f"Case ID:    {case.case_id}")
    print(f"Domain:     {case.domain}")
    print(f"Urgency:    {case.urgency.value}")
    print(f"Evidence:   {len(case.evidence)} items (empty)")
    print("-" * 60)

    result = await engine.execute(case)

    if result.error:
        print(f"ERROR:      {result.error.message}")
        print(f"Category:   {result.error.category.value}")
        print(f"Recoverable: {result.error.recoverable}")
        print(f"Lifecycle:  {result.processing_lifecycle.value}")
        print("-" * 60)
        print("Expected:   Error (empty evidence triggers domain validation)")
        print("Match:      YES")
    else:
        d = result.decision
        print(f"Decision:   {d.action}")
        print(f"Reason:     {d.reason}")
        print(f"Lifecycle:  {d.lifecycle.value}")
        print("-" * 60)
        print("Expected:   Error or HUMAN_REVIEW")
        print(f"Match:      {'YES' if d.action in ('reject', 'escalate') else 'CHECK'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
