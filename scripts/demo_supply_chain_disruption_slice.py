# ruff: noqa: T201
"""Synthetic slice demo: supply chain disruption -> case.evaluate -> governed decision.

Run: python scripts/demo_supply_chain_disruption_slice.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("CASE_PROVIDER", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from case_api.api.v1.app import app  # noqa: E402


def build_payload() -> dict:
    return {
        "contract_version": "case-eval/v0.1-draft",
        "capability_id": "case.evaluate",
        "correlation_id": "corr-poolar-scd-001",
        "idempotency_key": "idem-poolar-scd-004",
        "data_status": "synthetic",
        "payload": {
            "domain": "supply_chain_disruption",
            "summary": "Port closure and customs hold create critical shipment delay. Urgency: CRITICAL.",
            "urgency": "CRITICAL",
            "evidence": [
                {
                    "id": "ev-port",
                    "type": "text",
                    "content": "Port terminal closed due to severe weather; containers held.",
                    "source": "ops-feed",
                    "confidence": 0.92,
                },
                {
                    "id": "ev-customs",
                    "type": "text",
                    "content": "Customs clearance hold pending documentation review.",
                    "source": "compliance",
                    "confidence": 0.88,
                },
                {
                    "id": "ev-impact",
                    "type": "metric",
                    "content": "Estimated delay 72h; 3 priority orders affected.",
                    "source": "erp",
                    "confidence": 0.9,
                },
            ],
            "provider": "mock",
        },
    }


def main() -> int:
    client = TestClient(app)
    payload = build_payload()
    resp = client.post("/api/v1/evaluate", json=payload)
    print("STATUS", resp.status_code)
    body = resp.json()
    print(json.dumps(body, indent=2, ensure_ascii=False))
    if resp.status_code != 200:
        return 1
    result = body.get("result") or {}
    print("\n--- SLICE SUMMARY ---")
    print("case_ref:", result.get("case_ref"))
    print("action:", result.get("action"))
    print("urgency:", result.get("urgency"))
    print("confidence:", result.get("confidence"))
    print("requires_human_review:", result.get("requires_human_review"))
    print("lifecycle_hint:", result.get("lifecycle_hint"))
    print("summary:", result.get("summary"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
