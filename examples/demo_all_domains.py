"""
CASE Demo — All Three Operational Domains

Demonstrates case submission and processing across:
1. Logistics
2. Urban Operations
3. Infrastructure
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

    cases = [
        OperationalCase(
            case_id="TEST-MOCK-05-LOG",
            report_text="Logistics route optimization for regional distribution center",
            domain="logistics",
            urgency=UrgencyLevel.MEDIUM,
            evidence=[
                EvidenceItem(
                    id="ev-log-1",
                    type=EvidenceType.TEXT,
                    content="Route efficiency report attached",
                    source="logistics_system",
                    confidence=0.9,
                    extracted_at="2026-09-11T10:00:00Z",
                )
            ],
        ),
        OperationalCase(
            case_id="TEST-MOCK-01-URB",
            report_text="Pothole repair requested at Main Street and 5th Avenue",
            domain="urban_operations",
            urgency=UrgencyLevel.MEDIUM,
            evidence=[
                EvidenceItem(
                    id="ev-urb-1",
                    type=EvidenceType.TEXT,
                    content="Citizen report verified by field team",
                    source="311_app",
                    confidence=0.88,
                    extracted_at="2026-09-11T10:00:00Z",
                )
            ],
        ),
        OperationalCase(
            case_id="TEST-MOCK-04-INF",
            report_text="Power substation transformer temperature anomaly detected",
            domain="infrastructure",
            urgency=UrgencyLevel.CRITICAL,
            evidence=[
                EvidenceItem(
                    id="ev-inf-1",
                    type=EvidenceType.METRIC,
                    content="Transformer temp 98C (threshold 85C)",
                    source="scada_sensor",
                    confidence=0.98,
                    extracted_at="2026-09-11T10:00:00Z",
                )
            ],
        ),
    ]

    print("=" * 70)
    print("CASE Demo — All Three Operational Domains")
    print("=" * 70)

    for case in cases:
        print(f"\nProcessing domain: {case.domain.upper()}")
        print(f"  Case ID:  {case.case_id}")
        print(f"  Report:   {case.report_text[:60]}...")
        result = await engine.execute(case)
        if result.error:
            print(f"  ERROR:    {result.error.message}")
        else:
            d = result.decision
            print(f"  Action:   {d.action.upper()}")
            print(f"  Reason:   {d.reason}")
            print(f"  Lifecycle:{d.lifecycle.value}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
