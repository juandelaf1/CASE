# Phase 4: Demo Cases

**Date:** 2026-09-15
**Purpose:** 3 reproducible cases for Friday demo

---

## Case A: Standard Truck Shipment (Normal)

**Record:** USAID #82721 — Mozambique

| Field | Value |
|-------|-------|
| Shipment ID | USAID-82721 |
| Country | Mozambique |
| Mode | Truck |
| Product | ARV Adult |
| Weight | 150 kg |
| Value | $7,977 |
| Freight | $118 |
| Cargo Type | GENERAL |
| Priority | STANDARD |
| Risk Level | LOW |

**CASE Flow:**
```
OperationalCase(domain="logistics", urgency=LOW)
  → LogisticsPolicy validates evidence ✓
  → LLM produces: action=approve, urgency=LOW
  → ReliabilityPipeline validates ✓
  → RiskAssessment: LOW risk, auto_approve
  → Decision: approve
```

**Demo talking point:** Standard logistics case flows cleanly through pipeline. Low risk, auto-approved.

---

## Case B: Air Freight HIV Test Kit (Ambiguous)

**Record:** USAID #4 — Côte d'Ivoire

| Field | Value |
|-------|-------|
| Shipment ID | USAID-4 |
| Country | Côte d'Ivoire |
| Mode | Air |
| Product | HRDT HIV test kit |
| Weight | 171 kg |
| Value | $40,000 |
| Freight | $1,653 |
| Cargo Type | FRAGILE |
| Priority | STANDARD |
| Constraints | direct_drop, ex_works |
| Risk Level | LOW (classification) |

**CASE Flow:**
```
OperationalCase(domain="logistics", urgency=LOW)
  → LogisticsPolicy validates evidence ✓
  → LLM produces: action=escalate, urgency=HIGH (expected with real LLM)
  → ReliabilityPipeline validates ✓
  → RiskAssessment: HIGH risk, human_review
  → Decision: escalate
```

**Demo talking point:** High-value fragile cargo on air transport. LLM should escalate for human review due to value + fragility + international shipping.

---

## Case C: Heavy Pediatric Shipment (Critical)

**Record:** USAID #108 — Côte d'Ivoire

| Field | Value |
|-------|-------|
| Shipment ID | USAID-108 |
| Country | Côte d'Ivoire |
| Mode | Air |
| Product | ARV Pediatric |
| Weight | 2,126 kg |
| Value | $140,582 |
| Freight | $0 |
| Cargo Type | GENERAL |
| Priority | HIGH |
| Constraints | direct_drop, heavy_shipment |
| Needs Verification | True |
| Risk Level | LOW (classification) |

**CASE Flow:**
```
OperationalCase(domain="logistics", urgency=HIGH)
  → LogisticsPolicy validates evidence ✓
  → LLM produces: action=escalate, urgency=CRITICAL (expected with real LLM)
  → ReliabilityPipeline validates ✓
  → RiskAssessment: CRITICAL risk, ESCALATE
  → Decision: escalate
  → HITL: under_review
```

**Demo talking point:** Pediatric medication, heavy, high value, needs verification. System correctly escalates for human oversight. Full audit trail generated.

---

## Demo Script

### 1. Show Architecture
- Adapter loads real USAID data
- ShipmentProfile created
- Classification runs
- OperationalCase enters CASE Core

### 2. Run Case A (Normal)
- Show: low risk, auto-approved, audit logged
- Explain: standard flow, no human needed

### 3. Run Case B (Ambiguous)
- Show: medium/high risk, escalated
- Explain: fragile + high value + air = needs human review

### 4. Run Case C (Critical)
- Show: critical risk, escalated, HITL required
- Explain: pediatric + heavy + high value = maximum oversight

### 5. Show Evidence Trail
- Audit events for each case
- Risk assessments with factors
- Decision lifecycle (AI_PROPOSED → UNDER_REVIEW)

### 6. Key Messages
- Real data, not synthetic
- Domain-agnostic architecture
- Human oversight built in
- Full traceability
