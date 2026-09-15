# Phase 3 — Groq Decision Gate

**Date:** 2026-09-15
**Provider:** Groq (OpenAI-compatible API)
**Model:** qwen/qwen3.8-27b (default)
**Test Results:** 7/7 live tests pass, 26 mocked tests pass

---

## Decision: KEEP

Groq provides useful latency, acceptable quality, reliable structured output, and provider diversity.

### Evidence

| Metric | Result |
|--------|--------|
| Latency | ~100ms per request |
| Structured output | Works with additionalProperties:false schema fix |
| Quality | Returns valid JSON with correct decision/urgency/confidence |
| Reliability | 7/7 live tests pass |
| Cost | Not measured (Groq free tier) |
| Provider diversity | Adds real LLM option alongside MockProvider |

### Trade-offs

| Pro | Con |
|-----|-----|
| Very low latency | Limited model selection on free tier |
| OpenAI-compatible API | Requires additionalProperties:false schema fix |
| Free tier available | No cost tracking (no pricing endpoint) |
| Reliable structured output | Smaller model selection than OpenAI |

### Integration Boundary

```
CASE
  → LLMProvider (port)
    → GroqProvider (adapter)
      → Groq API (OpenAI-compatible)
```

No Groq-specific code in CASE core. All Groq logic behind the LLMProvider port.

---

## Phase 4 — Specialist Model Proposal

See `docs/PHASE4_SPECIALIST_MODEL_PROPOSAL.md`.

### Error Profile from Phase 3

| Error Type | Count | Source |
|------------|-------|--------|
| Domain validation (no evidence) | 1 | UrbanPolicy rejects no-evidence cases |
| Schema validation (malformed JSON) | 0 | Groq returns valid JSON |
| Provider timeout | 0 | ~100ms average |
| Rate limit | 0 | Free tier sufficient for testing |
| Authentication | 0 | Key valid |

### Recommendation

No specialist model needed yet. Error profile shows domain validation is working correctly (not a model quality issue). Continue with current architecture.

If future phases reveal systematic errors in specific tasks (e.g., classification, routing), then consider specialist models for those specific tasks.
