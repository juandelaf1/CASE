# Integration Proposal: Seismic Risk Assessment

**Date:** 2026-09-15
**Author:** Juan de la Fuente
**Status:** PROPOSED

---

## 1. Problem Statement

**Operational problem:** Assess seismic risk for geographic locations using real-time USGS earthquake data.

**Current state:** CASE has 3 registered domains (urban_operations, logistics, infrastructure). No domain handles seismic/geological risk. The infrastructure domain (`InfrastructurePolicy`) is generic — it does not ingest or evaluate real seismic data.

**Desired outcome:** A new `seismic_risk` domain that:
1. Ingests real earthquake data from USGS (M >= 4.5, past 30 days)
2. Creates `OperationalCase` records with seismic evidence
3. Routes through CASE pipeline (TriageEngine → ReliabilityPipeline → Decision)
4. Produces actionable decisions (approve/escalate/reject) based on risk level

---

## 2. Input

| Field | Source | Format |
|-------|--------|--------|
| Earthquake magnitude | USGS API | float (M 4.5–10+) |
| Earthquake depth | USGS API | float (km) |
| Location (lat/lon) | USGS API | float coordinates |
| Place description | USGS API | string |
| Timestamp | USGS API | ISO 8601 |
| Felt reports | USGS API | integer (CDI) |
| Tsunami flag | USGS API | boolean |

**Data source:** USGS Earthquake Hazards API — `https://earthquake.usgs.gov/fdsnws/event/1/query`
**License:** Public domain (US Government work)
**Access method:** REST API (JSON response)

---

## 3. Adapter Design

### USGS Adapter Module

```
src/usgs_adapter/
├── __init__.py
└── client.py          # USGSClient: fetch recent earthquakes, parse to normalized dicts
```

**Responsibilities:**
- Fetch earthquakes from USGS API (M >= 4.5, past 30 days)
- Parse JSON response into normalized Python dicts
- Handle network errors, rate limits, empty responses
- No CASE imports (respects I12/I13 — no domain leakage in core)

**Output format:**
```python
@dataclass
class SeismicEvent:
    event_id: str        # USGS event ID
    magnitude: float     # Moment magnitude
    depth_km: float      # Depth below surface
    latitude: float
    longitude: float
    place: str           # Human-readable description
    timestamp: str       # ISO 8601
    felt_count: int      # Number of felt reports
    tsunami: bool        # Tsunami flag
```

### Domain Policy

```
src/case_core/domain/seismic_policy.py    # SeismicRiskPolicy(DomainPolicy)
src/case_core/domain/seismic_automation.py # SeismicAutomationPolicy(AutomationPolicy)
```

**SeismicRiskPolicy:**
- `domain_name = "seismic_risk"`
- `validate_evidence()`: requires METRIC evidence with magnitude, depth, location
- `classify_urgency()`: magnitude-based (M >= 7 = CRITICAL, M >= 5.5 = HIGH, M >= 4.5 = MEDIUM)
- `classify_seismic_event_type()`: categorize by magnitude/depth/tsunami
- `get_recommended_actions()`: map event type to actions
- `get_domain_context()`: seismic risk context for prompt builder

**SeismicAutomationPolicy:**
- `assess_risk()`: magnitude + depth + tsunami → risk level
- `get_risk_factors()`: list of contributing factors
- `get_automation_rules()`: when to auto-approve vs. human review

### Composition Wiring

```python
# In composition.py
from case_core.domain.seismic_policy import SeismicRiskPolicy
from case_core.domain.seismic_automation import SeismicAutomationPolicy

registry.register(SeismicRiskPolicy())
_AUTOMATION_POLICIES["seismic_risk"] = SeismicAutomationPolicy()
```

---

## 4. CASE Core Flow

```
USGS API → USGSClient → SeismicEvent[] → for each event:
  → OperationalCase(
      case_id=seismic-{event_id},
      report_text="{place} M{magnitude} earthquake at depth {depth_km}km",
      domain="seismic_risk",
      urgency=<classified by magnitude>,
      evidence=[METRIC: magnitude, depth, location],
      metadata={lat, lon, tsunami, felt_count, usgs_event_id}
    )
  → TriageEngine.execute(case)
    → DomainRegistry.get("seismic_risk") → SeismicRiskPolicy
    → PromptBuilder.build(case) → LLMRequest
    → LLMProvider.complete(request) → LLMResponse
    → ReliabilityPipeline.run()
      → Parse JSON → Schema validate → Semantic validate → Domain validate
      → Automation assess (SeismicAutomationPolicy)
      → Build TriageDecision
    → Return TriageResult
  → Store decision → Log audit event
```

---

## 5. Output

**TriageDecision fields populated:**
- `action`: approve (low risk), escalate (medium risk), reject (high risk — escalate to humans)
- `reason`: LLM-generated explanation based on seismic evidence
- `urgency`: CRITICAL (M >= 7), HIGH (M >= 5.5), MEDIUM (M >= 4.5)
- `confidence`: 0.0–1.0 (LLM confidence in decision)
- `evidence_summary`: summary of seismic evidence considered

**Risk classification (non-LLM, deterministic):**
| Magnitude | Risk Level | Automation Decision |
|-----------|-----------|-------------------|
| M >= 7.0 | CRITICAL | HUMAN_REVIEW (requires HITL) |
| M >= 5.5 | HIGH | HUMAN_REVIEW |
| M >= 4.5 | MEDIUM | AUTO_APPROVE |
| M < 4.5 | LOW | AUTO_APPROVE |

---

## 6. Metrics

| Metric | Baseline (current) | Target (after integration) |
|--------|-------------------|--------------------------|
| End-to-end pipeline latency | N/A (no seismic domain) | < 5s per earthquake (LLM + validation) |
| USGS data fetch latency | N/A | < 3s for 30-day catalog |
| Decision accuracy | N/A | Deterministic risk matches LLM classification in >= 80% of cases |
| Pipeline success rate | N/A | >= 95% of earthquakes produce valid decisions |
| Error rate | N/A | < 5% parsing/validation failures |

---

## 7. Failure Modes

| Failure | Cause | Response |
|---------|-------|----------|
| USGS API timeout | Network issue | Retry 2x with exponential backoff, then skip event |
| USGS API returns empty | No recent M >= 4.5 earthquakes | Log info, return empty list |
| Malformed USGS JSON | API change | Log error, skip event, continue |
| LLM timeout | Provider issue | Retry via ReliabilityPipeline |
| LLM returns invalid JSON | Provider issue | Parse error → retry |
| Schema validation fails | LLM output missing fields | Retry with fresh LLM call |
| Domain validation fails | Insufficient evidence | Return error, skip event |

---

## 8. Fallback

- If USGS API unavailable: log warning, return empty list, system remains operational for other domains
- If LLM unavailable: ReliabilityPipeline handles retry/fallback per existing logic
- If seismic domain not registered: TriageEngine returns `DOMAIN_VALIDATION` error (existing behavior)

---

## 9. Security & Privacy

- USGS data is public domain — no PII, no sensitive data
- No credentials needed for USGS API
- No data stored externally
- All data stays in local SQLite (existing persistence)
- Rate limiting: respect USGS API guidelines (1 request/second)

---

## 10. Cost & Complexity

- **New files:** 4 (USGS client, seismic policy, seismic automation, tests)
- **Modified files:** 2 (composition.py — add 4 lines, CHANGELOG.md)
- **New dependencies:** 0 (uses existing httpx/requests)
- **Complexity:** LOW — follows established patterns exactly
- **Lines of code:** ~300 new (client ~100, policy ~100, automation ~50, tests ~300)

---

## 11. Acceptance Criteria

1. `USGSClient.fetch_recent()` returns list of `SeismicEvent` objects
2. `SeismicRiskPolicy` validates seismic evidence correctly
3. `SeismicRiskPolicy` classifies urgency by magnitude thresholds
4. `SeismicAutomationPolicy` assesses risk correctly
5. Full pipeline: seismic event → OperationalCase → TriageEngine → TriageDecision
6. Unit tests pass (mocked USGS response)
7. Integration tests pass (real USGS API, optional)
8. All existing tests still pass (594 baseline)
9. ruff clean, mypy clean
10. Documentation complete
