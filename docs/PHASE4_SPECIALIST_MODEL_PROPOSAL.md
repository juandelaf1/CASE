# Phase 4 — Specialist Model Proposal

> Created: 2026-09-15
> Status: PROPOSED — not yet approved

---

## Analysis of Phase 3 Error Profile

From live Groq testing, the error profile shows:

| Error Type | Count | Root Cause |
|------------|-------|------------|
| Domain validation (no evidence) | 1 | UrbanPolicy correctly rejects no-evidence cases |
| Schema validation (malformed JSON) | 0 | Groq returns valid JSON |
| Provider timeout | 0 | ~100ms average latency |
| Rate limit | 0 | Free tier sufficient |
| Authentication | 0 | Key valid |

**Conclusion:** No systematic model quality errors. Domain validation is working as designed.

---

## Specialist Model Criteria

A specialist model is recommended ONLY when:

1. A specific task has consistent error patterns
2. The task is well-defined and bounded
3. Sufficient training data exists
4. The benefit justifies the complexity
5. Integration boundary is clean

---

## Current Assessment

| Task | Error Rate | Specialist Needed? | Rationale |
|------|-----------|-------------------|-----------|
| Decision classification | 0% | NO | MockProvider and Groq both produce valid decisions |
| Urgency assessment | 0% | NO | Consistent across providers |
| Evidence evaluation | 0% | NO | Domain policy handles correctly |
| Schema compliance | 0% | NO | Groq structured output works |
| Domain routing | 0% | NO | Registry works correctly |

---

## Future Triggers for Specialist Models

Consider specialist models IF any of these occur:

1. **Classification errors > 5%** with real LLM on domain-specific cases
2. **Routing errors** where wrong domain is selected
3. **Evidence evaluation failures** where LLM misinterprets evidence quality
4. **Cost optimization** needed for high-volume production
5. **Latency requirements** < 50ms (current: ~100ms)

---

## Recommended Next Steps

1. Continue with current architecture (no specialist models)
2. Monitor error patterns with real provider
3. If errors emerge, create targeted specialist for that specific task
4. Re-evaluate after Phase 5 (if applicable)

---

## Integration Boundary (If Implemented)

```
CASE Core (unchanged)
  → SpecialistModel (new port)
    → KeywordClassifier (adapter)
    → KeywordRiskScorer (adapter)
```

No specialist model code in CASE core. All specialist logic behind ports.
