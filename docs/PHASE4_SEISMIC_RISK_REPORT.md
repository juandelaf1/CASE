# Phase 4: Seismic Risk Integration — Report

**Date:** 2026-09-15
**Status:** IMPLEMENTED
**Branch:** `case/phase-4-real-integration`

---

## Executive Summary

CASE now has its first real external data integration: seismic risk assessment using USGS Earthquake Hazards API data. This demonstrates CASE handling real-world, public-domain data through its existing pipeline with no architectural modifications.

---

## What Was Built

### USGS Adapter (`src/usgs_adapter/client.py`)
- Fetches earthquakes M >= 4.5 from USGS FDSNWS API (past 30 days)
- Parses GeoJSON response into normalized `SeismicEvent` dataclass
- Handles timeouts, HTTP errors, malformed responses gracefully
- No CASE core imports (respects I12/I13 invariants)

### SeismicRiskPolicy (`src/case_core/domain/seismic_policy.py`)
- Domain: `seismic_risk`
- Validates metric/text evidence
- Classifies urgency by magnitude thresholds:
  - M >= 7.0 → CRITICAL
  - M >= 5.5 → HIGH
  - M >= 4.5 → MEDIUM
  - M < 4.5 → LOW
- Recommends domain-specific actions per event type

### SeismicAutomationPolicy (`src/case_core/domain/seismic_automation.py`)
- Assesses risk based on magnitude, depth, tsunami flag, confidence
- Determines automation decision:
  - CRITICAL → ESCALATE (human review required)
  - HIGH → HUMAN_REVIEW
  - MEDIUM/LOW → AUTO_APPROVE
- Computes risk factors and policy violations

### Composition Wiring (`src/case_core/composition.py`)
- `SeismicRiskPolicy` registered in DomainRegistry
- `SeismicAutomationPolicy` mapped to `"seismic_risk"` domain
- No changes to TriageEngine, ReliabilityPipeline, or contracts

---

## Test Results

| Category | Before | After | Delta |
|----------|--------|-------|-------|
| Unit tests | 594 | 644 | +50 |
| Skipped | 14 | 14 | 0 |
| Ruff errors (new code) | 0 | 0 | 0 |
| Mypy errors | 0 | 0 | 0 |

### New Test Files
- `tests/unit/test_seismic_domain.py` — 45 mocked tests (policy, automation, USGS client, architecture boundaries)
- `tests/integration/test_seismic_usgs.py` — 5 live tests (USGS API, full pipeline with mock provider)

---

## Data Provenance

| Field | Value |
|-------|-------|
| Source | USGS Earthquake Hazards Program |
| URL | https://earthquake.usgs.gov/fdsnws/event/1/query |
| License | Public domain (US Government work) |
| Format | GeoJSON (FDSNWS standard) |
| Access | REST API, no authentication required |
| Rate Limit | 1 request/second (USGS guideline) |
| PII | None |
| Sensitive Data | None |

---

## Architecture Compliance

| Invariant | Status |
|-----------|--------|
| I01: Domain-agnostic core | ✅ No `if domain == "seismic_risk"` in core logic |
| I02: Provider-agnostic | ✅ LLM provider untouched |
| I03: Raw LLM never trusted | ✅ ReliabilityPipeline validates all output |
| I04: Type-safe boundaries | ✅ Pydantic v2 at all contract boundaries |
| I12: No domain leakage in core | ✅ USGS adapter has no case_core imports |
| I13: Provider-specific behind interfaces | ✅ No provider imports in domain logic |

---

## End-to-End Flow

```
USGS API (public, no auth)
    ↓
USGSClient.fetch_recent()
    ↓
list[SeismicEvent]
    ↓ (for each event)
OperationalCase(
    case_id="SEISMIC-{event_id}",
    report_text="M{mag} earthquake at {place}",
    domain="seismic_risk",
    urgency=<by magnitude>,
    evidence=[METRIC: mag, depth],
    metadata={lat, lon, tsunami, felt_count}
)
    ↓
TriageEngine.execute(case)
    ↓
DomainRegistry.get("seismic_risk") → SeismicRiskPolicy
    ↓
PromptBuilder.build(case) → LLMRequest
    ↓
LLMProvider.complete(request) → LLMResponse
    ↓
ReliabilityPipeline.run()
    ↓
TriageDecision(
    action=approve/escalate/reject,
    reason=<LLM-generated>,
    urgency=CRITICAL/HIGH/MEDIUM/LOW,
    confidence=0.0–1.0
)
    ↓
SQLite persistence + audit trail
```

---

## Limitations

1. **No ML model** — risk classification is deterministic (magnitude thresholds), not learned
2. **Single data source** — only USGS; no IBTrACS, GDACS, or volcanic data
3. **No geospatial indexing** — no H3 grid, no proximity queries
4. **No alerting** — decisions are logged but not pushed to external systems
5. **Portfolio project** — not a production earthquake monitoring system

---

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `src/usgs_adapter/__init__.py` | Created | 3 |
| `src/usgs_adapter/client.py` | Created | ~140 |
| `src/case_core/domain/seismic_policy.py` | Created | ~130 |
| `src/case_core/domain/seismic_automation.py` | Created | ~120 |
| `src/case_core/composition.py` | Modified | +4 lines |
| `tests/unit/test_seismic_domain.py` | Created | ~540 |
| `tests/integration/test_seismic_usgs.py` | Created | ~120 |
| `docs/SEISMIC_RISK_INTEGRATION_PROPOSAL.md` | Created | ~180 |
| `docs/PORTFOLIO_DISCOVERY.md` | Created | ~100 |
| `docs/INTEGRATION_CANDIDATES.md` | Created | ~90 |
| `CHANGELOG.md` | Modified | +15 lines |

---

## Next Steps (Phase 4 Stages 2–14)

- Stage 2: End-to-end evaluation with real USGS data
- Stage 3: Error analysis and edge cases
- Stage 4: Performance benchmarking
- Stage 5: Documentation completeness verification
- Stage 6: Clean git commit
