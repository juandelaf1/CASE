# Specialist Model Decision

**Date:** 2026-09-15
**Status:** NOT JUSTIFIED

---

## Decision

**NO specialist model will be introduced at this stage.**

---

## Evidence Basis

### What Was Tested
- 3 real USAID shipment cases through full CASE pipeline
- Deterministic classification (ShipmentClassification)
- LLM-based triage (Mock provider — no Groq/Ollama available)
- Risk assessment (LogisticsAutomationPolicy)

### Findings
1. **0 pipeline errors** — all 3 cases flow through successfully
2. **Classification works** — deterministic rules produce reasonable results
3. **Mock limitation** — mock provider returns static response, not a model failure
4. **No systematic LLM errors** — would need Groq/Ollama to test real LLM behavior

### Conditions for Specialist Model (NOT MET)
| Condition | Required | Observed |
|-----------|----------|----------|
| Systematic LLM misclassification | Yes | Not tested (mock used) |
| Domain-specific terminology failures | Yes | Not tested |
| Measurable accuracy gap | Yes | Not measured |
| Real LLM available | Yes | No (mock only) |

### Why NOT Now
1. **Insufficient evidence** — mock provider doesn't produce real LLM errors
2. **No real LLM tested** — Groq key not available, Ollama not running
3. **Classification works** — deterministic rules handle basic triage adequately
4. **Cost/benefit** — fine-tuning requires evidence of failure, which doesn't exist yet

### When to Reconsider
- After testing with real LLM (Groq/Ollama) on 50+ cases
- If LLM consistently misclassifies logistics-specific terminology
- If accuracy gap between general LLM and domain needs is >15%
- If latency/cost of general LLM is prohibitive for logistics volume

---

## Future Proposal (IF evidence supports it)

If real LLM testing reveals systematic errors, the specialist model would be:

**Approach:** Lightweight classifier (not fine-tuned LLM)
**Architecture:** Logistic regression or small neural net on shipment features
**Input:** weight_kg, value_usd, freight_cost, product_group, shipment_mode, country
**Output:** risk_level, logistics_class, urgency
**Training:** USAID SCMS dataset (10,324 records) with ground truth labels
**Benefit:** Deterministic, fast, no LLM dependency for classification

**This is NOT proposed now — only documented as future option.**

---

## Recommendation

Continue with current architecture:
- Deterministic classification for basic triage
- General LLM for nuanced reasoning (when available)
- No specialist model until evidence demands it
