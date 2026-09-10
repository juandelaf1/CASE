# Bias Evaluation Benchmark V0.1

**Date:** 2026-09-10
**Framework:** CASE v0.3 Foundation + v1.1 Blueprint
**Status:** Implemented

---

## 1. Objective

Evaluate whether CASE produces consistent decisions when presented with equivalent cases that differ only in an attribute that should NOT influence the decision.

**NOT** to demonstrate that CASE is "free of bias".

**IS** to measure and document observable behavior on a controlled set of pairs/cases.

---

## 2. Operational Definition of Bias

**Bias** = a systematic difference in decision output caused by an attribute that:

1. Is irrelevant to the domain policy rules
2. Should not affect urgency classification
3. Should not affect routing/incident classification
4. Should not affect automation assessment

**Not bias** = a difference explained by legitimate domain logic (e.g., CRITICAL urgency always escalates regardless of other attributes).

---

## 3. Methodology

### 3.1 Counterfactual Pairs

For each pair:
- Case A: baseline scenario
- Case B: identical scenario with ONE attribute changed
- Compare: decision, urgency, routing, automation, HITL

### 3.2 Evaluation Path

```
case → prompt → LLM/provider → parsing → validation → domain → automation → HITL
```

Using `MockProvider` for deterministic evaluation.

### 3.3 Determinism

All evaluations use `MockProvider` to ensure reproducibility. Results are deterministic given the same input.

---

## 4. Dimensions Evaluated

| # | Dimension | Attribute Changed | Expected Invariance |
|---|-----------|-------------------|---------------------|
| 1 | Supplier identity | `supplier_name` | Decision + Urgency |
| 2 | Customer identity | `customer_name` | Decision + Urgency |
| 3 | Location identity | `warehouse_location` | Decision + Urgency |
| 4 | Personnel identity | `driver_name` | Decision + Urgency |
| 5 | Wording style | `wording_style` | Decision + Urgency |
| 6 | Irrelevant detail | `irrelevant_detail` | Decision + Urgency |
| 7 | Route identity | `route_name` | Decision + Urgency |
| 8 | Timestamp format | `timestamp_format` | Decision + Urgency |
| 9 | Department name | `department_name` | Decision + Urgency |
| 10 | Incident synonym | `incident_type_neutral` | Decision + Urgency |

---

## 5. Dataset

Located at: `src/case_core/evaluation/scenarios/bias/__init__.py`

Contains 10 `BiasPairItem` objects (`BIAS-LOG-001` to `BIAS-LOG-010`) covering:

- Identity attributes (supplier, customer, warehouse, driver, route, department)
- Wording/style variations
- Irrelevant details
- Timestamp format differences
- Incident type synonyms

---

## 6. Metrics

### 6.1 Pair Consistency Rate

**Definition:** Percentage of pairs where ALL of the following hold:
- Decision is identical
- Urgency is identical

```
pair_consistency = fully_consistent_pairs / total_pairs
```

### 6.2 Decision Invariance Rate

**Definition:** Percentage of pairs where the decision (approve/reject/escalate) is identical.

```
decision_invariance = decision_consistent_pairs / total_pairs
```

### 6.3 Urgency Invariance Rate

**Definition:** Percentage of pairs where the urgency classification is identical.

```
urgency_invariance = urgency_consistent_pairs / total_pairs
```

### 6.4 Routing Invariance Rate

**Definition:** Percentage of pairs where the incident type classification is identical.

```
routing_invariance = routing_consistent_pairs / total_pairs
```

### 6.5 Automation Invariance Rate

**Definition:** Percentage of pairs where the automation decision (AUTO_APPROVE/HUMAN_REVIEW/ESCALATE) is identical.

```
automation_invariance = automation_consistent_pairs / total_pairs
```

### 6.6 HITL Consistency Rate

**Definition:** Percentage of pairs where the HITL requirement (requires_hitl) is identical.

```
hitl_consistency = hitl_consistent_pairs / total_pairs
```

---

## 7. Results

### 7.1 Policy-Level Evaluation (Domain Logic)

| Metric | Rate | Notes |
|--------|------|-------|
| **Decision Invariance** | 100% | Domain policy classifies identically for equivalent cases |
| **Urgency Invariance** | 100% | `classify_urgency()` ignores identity attributes |
| **Routing Invariance** | 100% | `classify_incident_type()` ignores identity attributes |

### 7.2 Automation-Level Evaluation

| Metric | Rate | Notes |
|--------|------|-------|
| **Automation Invariance** | 100% | `LogisticsAutomationPolicy` uses deterministic rules |
| **HITL Consistency** | 100% | Same risk level → same HITL requirement |

### 7.3 Pair Consistency

| Metric | Rate |
|--------|------|
| **Overall Pair Consistency** | 100% |

---

## 8. Inconsistencies Found

**None** at the policy/deterministic level.

All 10 counterfactual pairs produce identical:
- Urgency classification
- Incident type classification
- Automation decision
- HITL requirement

---

## 9. Analysis of False Positives

### 9.1 Justified Differences

No justified differences were observed because all pairs produced consistent results.

If a difference were observed in `wording_style` or `timestamp_format` pairs, it would be flagged as potentially justified (since natural language understanding may legitimately vary).

### 9.2 Attributes That Could Legitimately Affect Decisions

- **Evidence quality**: Different evidence sources could justify different decisions
- **Urgency keywords**: CRITICAL terms always escalate (by design, not bias)
- **Incident type**: Different incidents have different recommended actions

---

## 10. Limitations

1. **MockProvider only**: Evaluates deterministic policy logic, not LLM behavior
2. **Small dataset**: 10 pairs, not comprehensive coverage
3. **Synthetic cases**: Controlled scenarios, not real-world data
4. **Single domain**: Logistics only, not cross-domain evaluation
5. **No LLM evaluation**: Does not test how a real LLM handles counterfactuals
6. **Static evaluation**: One-time snapshot, not continuous monitoring
7. **No intersectionality**: Pairs vary one attribute at a time
8. **Policy-level only**: Does not test prompt construction or output parsing

---

## 11. Residual Risk

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM introduces bias not caught by policy | Medium | High | Policy-level validation catches most; HITL for high-risk |
| Prompt construction amplifies bias | Low | Medium | TIER3_DEVELOPER constraints limit injection |
| Evidence quality varies by identity | Low | Medium | Domain validation requires minimum evidence |
| Real-world cases not covered by dataset | High | Medium | Expand dataset over time |

---

## 12. Files

### New Files
- `src/case_core/evaluation/scenarios/bias/__init__.py` — Bias pairs dataset
- `src/case_core/evaluation/metrics/bias.py` — BiasEvaluator, BiasPairItem, BiasPairResult
- `docs/BENCHMARK_BIAS_V0.1.md` — This document

### Modified Files
- `tests/unit/test_behavioral.py` — Added TestBS030_BiasEvaluation (10 tests)

---

## Appendix A: Test Summary

### TestBS030_BiasEvaluation (10 tests)

| Test | Coverage |
|------|----------|
| `test_bias_pairs_dataset_loads` | Dataset loads correctly |
| `test_equivalent_pairs_same_classification` | Policy urgency classification |
| `test_equivalent_pairs_same_urgency` | Urgency invariance |
| `test_equivalent_pairs_same_routing` | Incident type invariance |
| `test_irrelevant_changes_no_automation_difference` | Automation invariance |
| `test_irrelevant_changes_no_hitl_difference` | HITL consistency |
| `test_wording_changes_no_decision_alteration` | Wording invariance |
| `test_bias_evaluator_Computes Results_Correctly` | Evaluator logic |
| `test_bias_evaluator_Detects_Inconsistency` | Inconsistency detection |

---

## Appendix B: Key Distinction

This evaluation tests **system behavior**, not **model fairness**.

- **System behavior**: Does the deterministic pipeline produce consistent outputs for equivalent inputs?
- **Model fairness**: Does the LLM itself exhibit bias toward protected groups?

This benchmark addresses the former. The latter requires LLM-level evaluation with real models, which is explicitly out of scope for this task.
