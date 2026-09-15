# Phase 3 — Provider Report

**Date:** 2026-09-15
**Status:** COMPLETE

---

## Provider

| Field | Value |
|-------|-------|
| Provider | Groq |
| API | OpenAI-compatible |
| Base URL | https://api.groq.com/openai/v1 |
| Model | qwen/qwen3.8-27b (default) |
| CASE Version | v1.0.0 + Phase 2 + Phase 3 |

---

## Configuration

| Env Variable | Purpose | Default |
|-------------|---------|---------|
| `CASE_PROVIDER` | Provider selection | `mock` |
| `CASE_GROQ_API_KEY` | Groq API key | (none) |
| `CASE_GROQ_MODEL` | Model identifier | `qwen/qwen3.8-27b` |
| `CASE_GROQ_BASE_URL` | API base URL | `https://api.groq.com/openai/v1` |

---

## Live Test Results

| Test | Result | Latency |
|------|--------|---------|
| Health check | PASS | ~50ms |
| Provider identity | PASS | — |
| Basic completion | PASS | ~100ms |
| Structured output | PASS | ~115ms |
| Pipeline: moderate case | PASS | ~1.5s |
| Pipeline: critical case | PASS | ~1.5s |
| Pipeline: no-evidence | PASS | ~0.5s |

**Total:** 7/7 pass

---

## Metrics

### Provider

| Metric | Value |
|--------|-------|
| Request success | 7/7 |
| Request failure | 0/7 |
| Average latency | ~100ms |

### Usage (from live tests)

| Metric | Value |
|--------|-------|
| Prompt tokens | ~150-200 per request |
| Completion tokens | ~50-100 per request |
| Total tokens | ~200-300 per request |

### CASE Validation

| Metric | Value |
|--------|-------|
| Schema validation | 100% pass |
| Semantic validation | 100% pass |
| Domain validation | 100% pass (1 expected terminal failure) |
| Retries | 0 |
| Repair | 0 |

---

## Structured Output

Groq supports structured output via `response_format: json_schema` with one requirement:

**All object types must have `additionalProperties: false`.**

This is handled by `_add_additional_properties_false()` in `GroqProvider._build_payload()`.

CASE validation remains active regardless of provider schema compliance.

---

## Failures

| Failure Type | Expected? | CASE Handling |
|-------------|-----------|---------------|
| Missing API key | Yes | Returns `authentication_error`, no crash |
| Invalid key | Yes | Returns `authentication_error` |
| Timeout | Yes | Returns `timeout`, retryable |
| Rate limit | Yes | Returns `rate_limit` |
| Malformed output | Yes | Returns error, parsing fails gracefully |
| Provider 5xx | Yes | Returns `provider_unavailable` |
| Domain validation | Yes | Terminal failure, no decision produced |

---

## Limitations

1. **Cost:** Not measured — Groq free tier doesn't expose pricing
2. **Model selection:** Limited on free tier
3. **Schema fix:** Required additionalProperties:false workaround
4. **Latency measurement:** Includes network overhead, not pure inference

---

## Recommendation

**KEEP** — Groq provides useful latency, acceptable quality, reliable structured output, and provider diversity. The provider integrates cleanly behind the LLMProvider port with no core changes.

---

## Files

| File | Purpose |
|------|---------|
| `src/case_core/providers/groq.py` | GroqProvider implementation |
| `tests/unit/test_groq_provider.py` | 26 mocked tests |
| `tests/integration/test_groq_live.py` | 7 live tests |
| `streamlit_app/views/provider_lab.py` | Updated with Groq support |
| `streamlit_app/views/comparison.py` | Provider comparison view |
| `docs/PHASE3_GROQ_DECISION.md` | Decision gate |
| `docs/PHASE4_SPECIALIST_MODEL_PROPOSAL.md` | Phase 4 proposal |
