# Risk-Based Automation V0.1

**Date:** 2026-09-10
**Framework:** CASE v0.3 Foundation + v1.1 Blueprint
**Status:** Implemented

---

## 1. Motivation

The current HITL (Human-in-the-Loop) flow treats all AI proposals equally: every decision requires human review. This creates unnecessary overhead for low-risk, routine decisions that could be safely automated.

Risk-Based Automation introduces a deterministic layer that evaluates each AI proposal and routes it to the appropriate handling path:

- **AUTO_APPROVE**: Low-risk decisions that can be automated
- **HUMAN_REVIEW**: Medium-risk decisions requiring human oversight
- **ESCALATE**: High/critical-risk decisions requiring immediate human attention

**Key principle:** The LLM does NOT decide if its proposal can be automated. Automation authorization derives from deterministic rules in the domain policy layer.

---

## 2. Decision Model

### 2.1 Flow

```
LLM Proposal
    ↓
Validation (schema, semantic, domain)
    ↓
Automation Assessment (deterministic)
    ↓
├─ AUTO_APPROVE → DecisionLifecycle.APPROVED
├─ HUMAN_REVIEW → DecisionLifecycle.UNDER_REVIEW
└─ ESCALATE → DecisionLifecycle.ESCALATED
```

### 2.2 Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `AutomationDecision` | `contracts/automation.py` | Enum: AUTO_APPROVE, HUMAN_REVIEW, ESCALATE |
| `RiskLevel` | `contracts/automation.py` | Enum: LOW, MEDIUM, HIGH, CRITICAL |
| `RiskAssessment` | `contracts/automation.py` | Model: assessment result with factors, violations, justification |
| `AutomationPolicy` | `ports/automation.py` | ABC: interface for domain-specific risk assessment |
| `AutomationEvaluator` | `reliability/automation.py` | Evaluates automation decisions using policy |
| `LogisticsAutomationPolicy` | `domain/logistics_automation.py` | Logistics-specific risk matrix |

---

## 3. Automation Criteria

### 3.1 AUTO_APPROVE Conditions

ALL of the following must be true:

- Risk level: LOW
- Validation status: valid
- Evidence quality: sufficient (≥2 sources, confidence ≥0.6)
- Confidence: ≥0.7
- No policy violations
- No required HITL conditions

### 3.2 HUMAN_REVIEW Conditions

ANY of the following:

- Risk level: MEDIUM or HIGH
- Confidence: <0.6
- Evidence quality: insufficient
- Policy violations (non-critical)
- Decision action: reject
- Ambiguous or conflicting signals

### 3.3 ESCALATE Conditions

ANY of the following:

- Risk level: CRITICAL
- Critical urgency with policy violation
- Action: escalate (from LLM proposal)

---

## 4. Risk Factors

The `LogisticsAutomationPolicy` evaluates these factors:

| Factor | Source | Impact |
|--------|--------|--------|
| `urgency_critical` | Urgency = CRITICAL | Risk → CRITICAL, policy violation |
| `urgency_high` | Urgency = HIGH | Risk → HIGH |
| `urgency_medium` | Urgency = MEDIUM | Risk → MEDIUM |
| `validation_failed` | Schema/semantic/domain error | Risk → HIGH, policy violation |
| `evidence_insufficient` | <2 sources or confidence <0.6 | Risk elevation |
| `confidence_low` | Confidence <0.5 | Risk elevation |
| `confidence_moderate` | Confidence 0.5-0.7 | Factor noted |
| `action_escalate` | LLM proposed escalate | Risk → HIGH |
| `action_reject` | LLM proposed reject | Risk → MEDIUM |

### 4.1 Effective Urgency

The system takes the maximum of:
- LLM-proposed urgency (from JSON response)
- Case-reported urgency (from operational case)

This prevents manipulation where an attacker could downgrade urgency in the LLM response.

---

## 5. Logistics Example

### 5.1 LOW Risk → AUTO_APPROVE

```json
{
  "decision": "approve",
  "reason": "Standard delivery on schedule with sufficient evidence",
  "urgency": "LOW",
  "confidence": 0.85,
  "evidence_summary": "Delivery confirmed by warehouse and tracking system"
}
```

- Urgency: LOW
- Confidence: 0.85 (≥0.7)
- Evidence: 2+ sources
- Result: AUTO_APPROVE

### 5.2 MEDIUM Risk → HUMAN_REVIEW

```json
{
  "decision": "approve",
  "reason": "Shipment delay being investigated with moderate confidence",
  "urgency": "MEDIUM",
  "confidence": 0.65,
  "evidence_summary": "Investigation ongoing with partial evidence collected"
}
```

- Urgency: MEDIUM
- Confidence: 0.65 (<0.7)
- Result: HUMAN_REVIEW

### 5.3 CRITICAL Risk → ESCALATE

```json
{
  "decision": "escalate",
  "reason": "Emergency situation requiring immediate escalation",
  "urgency": "CRITICAL",
  "confidence": 0.9,
  "evidence_summary": "Critical incident with multiple confirming sources"
}
```

- Urgency: CRITICAL
- Policy violation: critical_urgency_requires_escalation
- Result: ESCALATE

---

## 6. HITL Integration

### 6.1 Backward Compatibility

The automation layer is optional. If no `AutomationPolicy` is provided:
- Pipeline behaves exactly as before
- All decisions remain `AI_PROPOSED`
- HITL cycle unchanged

### 6.2 With Automation

```
AI_PROPOSED → validation → automation assessment
    ↓
AUTO_APPROVE → APPROVED (final decision)
UNDER_REVIEW → human review → APPROVED/MODIFIED/REJECTED/ESCALATED
ESCALATED → human handling
```

### 6.3 Existing HITL Endpoints

No changes required. The existing endpoints continue to work:

- `POST /cases/{id}/under-review` → Manually move to UNDER_REVIEW
- `POST /cases/{id}/approve` → Approve with human override
- `POST /cases/{id}/reject` → Reject with human override
- `POST /cases/{id}/escalate` → Escalate manually
- `POST /cases/{id}/modify` → Modify and approve

---

## 7. Audit

### 7.1 Automation Audit Events

| Event Type | When | Details |
|------------|------|---------|
| `AUTOMATION_ASSESSED` | After assessment | Full RiskAssessment model dump |
| `AUTO_APPROVED` | AUTO_APPROVE decision | Justification |
| `AUTO_HUMAN_REVIEW` | HUMAN_REVIEW decision | Justification |
| `AUTO_ESCALATED` | ESCALATE decision | Justification |

### 7.2 Audit Trail Example

```json
{
  "event_id": "ae-LOG-001-AUTOMATION_ASSESSED-1726000000000",
  "case_id": "LOG-001",
  "decision_id": "dec-LOG-001",
  "event_type": "AUTOMATION_ASSESSED",
  "timestamp": "2026-09-10T12:00:00Z",
  "details": {
    "risk_level": "LOW",
    "automation_decision": "auto_approve",
    "confidence": 0.85,
    "factors": [],
    "requires_hitl": false,
    "policy_violations": [],
    "evidence_quality": "strong",
    "validation_status": "valid",
    "justification": "Risk: LOW; Decision: auto_approve"
  }
}
```

### 7.3 Distinguishing Decision Types

| Decision Type | Lifecycle | Audit Events |
|---------------|-----------|--------------|
| Automated | APPROVED | AUTOMATION_ASSESSED, AUTO_APPROVED |
| Human-reviewed | UNDER_REVIEW → APPROVED | AUTOMATION_ASSESSED, AUTO_HUMAN_REVIEW, HITL_APPROVED |
| Human-modified | UNDER_REVIEW → MODIFIED | AUTOMATION_ASSESSED, AUTO_HUMAN_REVIEW, HITL_MODIFIED |
| Escalated | ESCALATED | AUTOMATION_ASSESSED, AUTO_ESCALATED |

---

## 8. Security

### 8.1 Threat Model

An attacker may attempt to:
- Force AUTO_APPROVE by manipulating urgency to LOW
- Bypass automation by inflating confidence
- Inject schema violations to skip automation

### 8.2 Defenses

| Attack | Defense |
|--------|---------|
| Downgrade urgency in LLM response | Effective urgency = max(LLM, case) |
| Inflate confidence | Confidence alone insufficient; risk factors evaluated |
| Schema manipulation | Validation catches before automation assessment |
| Policy bypass | Deterministic rules in policy layer, not LLM |

### 8.3 Regression Tests

- `test_malicious_input_cannot_force_auto_approve`: Attempts to force LOW urgency on CRITICAL case
- `test_manipulated_confidence_cannot_bypass_automation`: Attempts to use high confidence on CRITICAL case
- `test_schema_manipulation_blocks_automation`: Attempts invalid urgency enum

---

## 9. Limitations

1. **Deterministic rules only:** No ML-based risk scoring; rules are manually defined
2. **Domain-specific:** Each domain requires its own `AutomationPolicy` implementation
3. **No adaptive thresholds:** Risk thresholds are static, not learned from data
4. **No cross-case analysis:** Each case evaluated independently
5. **MockProvider only:** Real LLMs may produce different risk distributions

---

## 10. Files Changed

### New Files
- `src/case_core/contracts/automation.py` — AutomationDecision, RiskLevel, RiskAssessment
- `src/case_core/ports/automation.py` — AutomationPolicy ABC
- `src/case_core/reliability/automation.py` — AutomationEvaluator
- `src/case_core/domain/logistics_automation.py` — LogisticsAutomationPolicy
- `docs/RISK_BASED_AUTOMATION_V0.1.md` — This document

### Modified Files
- `src/case_core/reliability/pipeline.py` — Added automation_policy parameter, assess_automation method, audit events
- `tests/unit/test_behavioral.py` — Added TestBS029_RiskBasedAutomation (12 tests)
- `tests/unit/test_security.py` — Added TestBS029_AutomationSecurity (3 tests)

---

## Appendix A: Test Summary

### TestBS029_RiskBasedAutomation (12 tests)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_low_risk_valid_auto_approve` | LOW urgency, valid, sufficient evidence | AUTO_APPROVE |
| `test_low_risk_insufficient_evidence_human_review` | LOW urgency, low confidence | HUMAN_REVIEW |
| `test_medium_risk_human_review` | MEDIUM urgency | HUMAN_REVIEW |
| `test_high_risk_human_review` | HIGH urgency | HUMAN_REVIEW |
| `test_critical_risk_escalate` | CRITICAL urgency | ESCALATE |
| `test_schema_invalid_no_automation` | Invalid decision enum | Schema error |
| `test_semantic_invalid_no_automation` | Reason too short | Semantic error |
| `test_domain_invalid_no_automation` | No evidence | Domain error |
| `test_policy_violation_no_automation` | CRITICAL with approve | Policy violation |
| `test_disagreement_ambiguity_human_review` | Conflicting evidence | HUMAN_REVIEW |
| `test_automated_decision_audited` | Audit trail verification | Events logged |
| `test_hitl_existing_still_works` | No automation policy | AI_PROPOSED |

### TestBS029_AutomationSecurity (3 tests)

| Test | Attack | Defense |
|------|--------|---------|
| `test_malicious_input_cannot_force_auto_approve` | Force LOW on CRITICAL | Effective urgency escalation |
| `test_manipulated_confidence_cannot_bypass_automation` | High confidence on CRITICAL | Risk factors override |
| `test_schema_manipulation_blocks_automation` | Invalid urgency enum | Schema validation |
