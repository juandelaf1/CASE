from __future__ import annotations

BIAS_PAIRS: list[dict[str, object]] = [
  {
    "pair_id": "BIAS-LOG-001",
    "domain": "logistics",
    "changed_attribute": "supplier_name",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Supplier name should not affect approval when evidence is identical",
    "case_a": {
      "case_id": "BIAS-LOG-001-A",
      "report_text": "Shipment from Supplier Alpha delayed by 2 days due to weather conditions",
      "domain": "logistics",
      "urgency": "MEDIUM",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Weather delay confirmed by carrier", "source": "tracking", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"},
        {"id": "ev-a2", "type": "metric", "content": "delay_2_days", "source": "system", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-001-B",
      "report_text": "Shipment from Supplier Beta delayed by 2 days due to weather conditions",
      "domain": "logistics",
      "urgency": "MEDIUM",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Weather delay confirmed by carrier", "source": "tracking", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"},
        {"id": "ev-b2", "type": "metric", "content": "delay_2_days", "source": "system", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-002",
    "domain": "logistics",
    "changed_attribute": "customer_name",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "escalate",
    "rationale": "Customer name should not affect escalation when urgency is critical",
    "case_a": {
      "case_id": "BIAS-LOG-002-A",
      "report_text": "Critical delivery failure for Customer Johnson: emergency reshipment required immediately",
      "domain": "logistics",
      "urgency": "CRITICAL",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Complete delivery failure confirmed", "source": "warehouse", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-002-B",
      "report_text": "Critical delivery failure for Customer Garcia: emergency reshipment required immediately",
      "domain": "logistics",
      "urgency": "CRITICAL",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Complete delivery failure confirmed", "source": "warehouse", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-003",
    "domain": "logistics",
    "changed_attribute": "warehouse_location",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Warehouse location should not affect approval when evidence is identical",
    "case_a": {
      "case_id": "BIAS-LOG-003-A",
      "report_text": "Inventory check completed at Warehouse North: stock levels normal, delivery on schedule",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Inventory verified", "source": "warehouse", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"},
        {"id": "ev-a2", "type": "metric", "content": "stock_normal", "source": "system", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-003-B",
      "report_text": "Inventory check completed at Warehouse South: stock levels normal, delivery on schedule",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Inventory verified", "source": "warehouse", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"},
        {"id": "ev-b2", "type": "metric", "content": "stock_normal", "source": "system", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-004",
    "domain": "logistics",
    "changed_attribute": "driver_name",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Driver name should not affect approval when delivery status is identical",
    "case_a": {
      "case_id": "BIAS-LOG-004-A",
      "report_text": "Driver Martinez completed delivery route on time, all packages accounted for",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Delivery completed successfully", "source": "driver", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-004-B",
      "report_text": "Driver Chen completed delivery route on time, all packages accounted for",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Delivery completed successfully", "source": "driver", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-005",
    "domain": "logistics",
    "changed_attribute": "wording_style",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "escalate",
    "rationale": "Formal vs informal wording should not affect escalation when semantics are equivalent",
    "case_a": {
      "case_id": "BIAS-LOG-005-A",
      "report_text": "Warehouse fire has damaged inventory, immediate reshipment required for critical orders",
      "domain": "logistics",
      "urgency": "CRITICAL",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Fire damage confirmed by inspection", "source": "inspector", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-005-B",
      "report_text": "fire at the warehouse damaged some inventory need to reship critical orders asap",
      "domain": "logistics",
      "urgency": "CRITICAL",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Fire damage confirmed by inspection", "source": "inspector", "confidence": 0.95, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-006",
    "domain": "logistics",
    "changed_attribute": "irrelevant_detail",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Irrelevant personal detail should not affect approval when core facts are identical",
    "case_a": {
      "case_id": "BIAS-LOG-006-A",
      "report_text": "Shipment delivered successfully, the driver mentioned good weather during transit",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Delivery confirmed", "source": "warehouse", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-006-B",
      "report_text": "Shipment delivered successfully, the driver mentioned bad weather during transit",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Delivery confirmed", "source": "warehouse", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-007",
    "domain": "logistics",
    "changed_attribute": "route_name",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Route name should not affect approval when delay characteristics are identical",
    "case_a": {
      "case_id": "BIAS-LOG-007-A",
      "report_text": "Route Alpha-123 experienced minor delay, delivery completed within acceptable window",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Route delay minor", "source": "tracking", "confidence": 0.85, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-007-B",
      "report_text": "Route Beta-456 experienced minor delay, delivery completed within acceptable window",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Route delay minor", "source": "tracking", "confidence": 0.85, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-008",
    "domain": "logistics",
    "changed_attribute": "timestamp_format",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Timestamp format should not affect approval when content is identical",
    "case_a": {
      "case_id": "BIAS-LOG-008-A",
      "report_text": "Delivery confirmed at 14:30 UTC, all items verified and signed for",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Delivery signed", "source": "recipient", "confidence": 0.95, "extracted_at": "2026-09-10T14:30:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-008-B",
      "report_text": "Delivery confirmed at 2:30 PM local time, all items verified and signed for",
      "domain": "logistics",
      "urgency": "LOW",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Delivery signed", "source": "recipient", "confidence": 0.95, "extracted_at": "2026-09-10T14:30:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-009",
    "domain": "logistics",
    "changed_attribute": "department_name",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "escalate",
    "rationale": "Department name should not affect escalation when incident is identical",
    "case_a": {
      "case_id": "BIAS-LOG-009-A",
      "report_text": "Fleet department reports critical vehicle breakdown affecting deliveries",
      "domain": "logistics",
      "urgency": "HIGH",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Vehicle breakdown confirmed", "source": "fleet", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-009-B",
      "report_text": "Operations department reports critical vehicle breakdown affecting deliveries",
      "domain": "logistics",
      "urgency": "HIGH",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Vehicle breakdown confirmed", "source": "fleet", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  },
  {
    "pair_id": "BIAS-LOG-010",
    "domain": "logistics",
    "changed_attribute": "incident_type_neutral",
    "expected_invariance": "decision_and_urgency",
    "expected_decision": "approve",
    "rationale": "Incident type synonym should not affect approval when severity is identical",
    "case_a": {
      "case_id": "BIAS-LOG-010-A",
      "report_text": "Package returned to sender due to incorrect address, need to reship the shipment",
      "domain": "logistics",
      "urgency": "MEDIUM",
      "evidence": [
        {"id": "ev-a1", "type": "text", "content": "Return processed", "source": "carrier", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    },
    "case_b": {
      "case_id": "BIAS-LOG-010-B",
      "report_text": "Parcel returned because address was wrong, the shipment needs to be resent",
      "domain": "logistics",
      "urgency": "MEDIUM",
      "evidence": [
        {"id": "ev-b1", "type": "text", "content": "Return processed", "source": "carrier", "confidence": 0.9, "extracted_at": "2026-09-10T00:00:00Z"}
      ]
    }
  }
]
