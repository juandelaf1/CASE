# V3 Ecosystem Integration Plan

**Branch:** `v3/ecosystem-integration`  
**Baseline:** `cfd4a3b` (v2.1 Hardening)  
**Date:** 2026-09-28

## Mission

Turn CASE from a strong decision-orchestration core into a coherent technical ecosystem by integrating only capabilities that demonstrate professional systems thinking — while keeping the core stable.

## Guiding Principle

Every integration must answer: **WHY**, **WHAT PROBLEM**, **INPUT**, **OUTPUT**, **CONTRACT**, **CONSUMER**, **INTEGRATION SEAM**, **VALUE**, **RISK**.

---

## Capability Matrix

### Legend

| Status | Meaning |
|--------|---------|
| CONNECTED | Part of the running pipeline |
| INTEGRATED | Wired into the system this phase |
| EXTENSION | Wired via API/UI, not core path |
| TESTED ISOLATED | Implemented and tested, not wired |
| DEFERRED | Architecturally sound but not justified now |

---

### 1. Domain Registry + 4 Domains (Connected)

| Field | Value |
|-------|-------|
| **Capability** | Domain policy registration + 4 domain policies |
| **Status** | CONNECTED |
| **Problem Solved** | Domain-agnostic triage with domain-specific evidence validation and urgency classification |
| **Input** | `OperationalCase` |
| **Output** | `DomainContext` (evidence validation, urgency, context dict) |
| **Contract** | `DomainPolicy` ABC in `ports/domain.py` |
| **Consumer** | `TriageEngine.execute()` via `DomainRegistry.get()` |
| **Integration Seam** | `composition.py:94-99` — `registry.register()` |
| **Tests** | `tests/unit/test_domain_*.py` (4 files) |
| **Value** | HIGH — core architectural feature |
| **Risk** | NONE — already connected |

---

### 2. Automation Policies (4 Connected)

| Field | Value |
|-------|-------|
| **Capability** | Risk-based automation routing per domain |
| **Status** | CONNECTED |
| **Problem Solved** | Deterministic risk assessment independent of LLM — decides auto-approve, human review, or escalation |
| **Input** | `OperationalCase` + validation/evidence/confidence data |
| **Output** | `RiskAssessment` (risk_level, automation_decision, requires_hitl) |
| **Contract** | `AutomationPolicy` ABC in `ports/automation.py` |
| **Consumer** | `AutomationEvaluator` → `TriageEngine` |
| **Integration Seam** | `composition.py:32-46` — `_resolve_automation_policy()` |
| **Tests** | `tests/unit/test_automation_*.py` (4 files) |
| **Value** | HIGH — deterministic safety boundary |
| **Risk** | NONE — already connected |

---

### 3. Provider Abstraction + Circuit Breaker (Connected)

| Field | Value |
|-------|-------|
| **Capability** | LLM provider abstraction with fault tolerance |
| **Status** | CONNECTED |
| **Problem Solved** | Provider-agnostic LLM calls with automatic circuit breaking on failures |
| **Input** | `Prompt` object |
| **Output** | `LLMResponse` (content, tokens, model, latency) |
| **Contract** | `LLMProvider` ABC in `ports/llm.py` |
| **Consumer** | `TriageEngine` via `provider` |
| **Integration Seam** | `composition.py:72-91` — all providers wrapped in `CircuitBreakerProvider` |
| **Tests** | `tests/unit/test_circuit_breaker_provider.py` (11 tests) |
| **Value** | HIGH — resilience + provider flexibility |
| **Risk** | NONE — already connected |

---

### 4. Reliability Pipeline (Connected)

| Field | Value |
|-------|-------|
| **Capability** | Multi-stage LLM output validation |
| **Status** | CONNECTED |
| **Problem Solved** | Raw LLM output is never trusted — validated through schema, domain, safety, confidence stages |
| **Input** | Raw LLM response + `OperationalCase` + `DomainContext` |
| **Output** | Validated `AIProposal` or `CASEError` |
| **Contract** | `ReliabilityPipeline` in `reliability/pipeline.py` |
| **Consumer** | `TriageEngine._execute_inner()` |
| **Integration Seam** | `engine.py:122` — `self._reliability_pipeline.validate()` |
| **Tests** | `tests/unit/test_reliability_pipeline.py` (14 tests) |
| **Value** | HIGH — trust boundary |
| **Risk** | NONE — already connected |

---

### 5. Persistence (SQLite) (Connected)

| Field | Value |
|-------|-------|
| **Capability** | Decision + audit persistence with append-only semantics |
| **Status** | CONNECTED |
| **Problem Solved** | Durable storage of decisions and audit events for HITL and compliance |
| **Input** | `TriageDecision` / `AuditEvent` |
| **Output** | Query results from SQLite |
| **Contract** | `DecisionRepository` ABC + `AuditPort` ABC |
| **Consumer** | `TriageEngine`, API endpoints, Streamlit UI |
| **Integration Seam** | `composition.py:104-106` |
| **Tests** | `tests/unit/test_persistence_roundtrip.py` (10), `tests/unit/test_audit_integrity.py` (6) |
| **Value** | HIGH — durability + auditability |
| **Risk** | NONE — already connected |

---

### 6. API (FastAPI) (Connected)

| Field | Value |
|-------|-------|
| **Capability** | 13 REST endpoints for triage, HITL, cases, providers, comparison, health |
| **Status** | CONNECTED |
| **Problem Solved** | HTTP interface for programmatic access to CASE |
| **Input** | HTTP requests (JSON) |
| **Output** | HTTP responses (JSON) |
| **Contract** | Pydantic request/response models in `app.py` |
| **Consumer** | External clients, Streamlit UI |
| **Integration Seam** | `app.py` — 13 endpoints |
| **Tests** | `tests/unit/test_api_*.py`, `tests/integration/test_api_*.py` |
| **Value** | HIGH — programmatic access |
| **Risk** | NONE — already connected |

---

### 7. Streamlit UI (Connected)

| Field | Value |
|-------|-------|
| **Capability** | 9-page web interface for case management, HITL, evaluation, comparison |
| **Status** | CONNECTED |
| **Problem Solved** | Human interface for case triage, review, and monitoring |
| **Input** | User interactions |
| **Output** | Visual displays of decisions, audit trails, provider metrics |
| **Contract** | `CASEClient` → API |
| **Consumer** | Human operators |
| **Integration Seam** | `streamlit_app/` — 9 views |
| **Tests** | `tests/unit/test_streamlit_client.py` (skipped — ModuleNotFoundError) |
| **Value** | HIGH — human interface |
| **Risk** | NONE — already connected |

---

### 8. API Key Auth (Connected, Hardened in v2.1)

| Field | Value |
|-------|-------|
| **Capability** | Constant-time API key authentication |
| **Status** | CONNECTED |
| **Problem Solved** | Prevents unauthorized API access with timing-attack protection |
| **Input** | HTTP request with `X-API-Key` header |
| **Output** | Pass/reject |
| **Contract** | `APIKeyAuthMiddleware` in `auth.py` |
| **Consumer** | FastAPI middleware |
| **Integration Seam** | `app.py:23` — `app.add_middleware()` |
| **Tests** | `tests/unit/test_auth.py` (10 tests) |
| **Value** | HIGH — security boundary |
| **Risk** | NONE — already connected |

---

### 9. Real Estate Domain Policy (Isolated → **INTEGRATED in V3**)

| Field | Value |
|-------|-------|
| **Capability** | Domain policy for real estate operations (valuation, inspection, listing, negotiation, closing, dispute, maintenance, compliance) |
| **Status** | **INTEGRATED** (V3) |
| **Problem Solved** | Demonstrates domain extensibility — 5th domain with zero core changes |
| **Input** | `OperationalCase` with `domain="real_estate"` |
| **Output** | `TriageDecision` with real-estate-specific classification |
| **Contract** | `RealEstatePolicy(DomainPolicy)` + `RealEstateAutomationPolicy(AutomationPolicy)` |
| **Consumer** | `DomainRegistry` via `composition.py` |
| **Integration Seam** | `composition.py` — `registry.register(RealEstatePolicy())` + automation policy |
| **Tests** | `tests/unit/test_real_estate_domain.py` (14 tests) |
| **Value** | HIGH — demonstrates pluggable architecture with zero core modifications |
| **Risk** | LOW — follows identical pattern as 4 existing domains |
| **Justification** | Already implemented and tested. Registration is 2 lines in composition.py. Proves the domain plugin architecture is real, not theoretical. |

---

### 10. USGS Seismic Adapter (Isolated → **EXTENSION in V3**)

| Field | Value |
|-------|-------|
| **Capability** | Fetch real seismic events from USGS Earthquake Hazards API |
| **Status** | **EXTENSION** (V3) — wired via API endpoint, not core path |
| **Problem Solved** | Enables real-world seismic data for demo/evaluation; proves external adapter integration pattern |
| **Input** | USGS API → `SeismicEvent` dataclass |
| **Output** | List of `SeismicEvent` objects |
| **Contract** | `USGSClient.fetch_recent() → list[SeismicEvent]` |
| **Consumer** | New `/api/v1/seismic/events` endpoint |
| **Integration Seam** | New API endpoint + UI component to display real seismic events |
| **Tests** | `tests/unit/test_seismic_domain.py` (USGSClient tests), `tests/integration/test_seismic_usgs.py` (live tests) |
| **Value** | MEDIUM — real data demo, adapter pattern demonstration |
| **Risk** | LOW — external dependency with graceful degradation (returns empty list on error) |
| **Justification** | Adapter is already built and tested. Wiring it as a non-core API endpoint demonstrates how external data sources integrate with CASE without polluting the core. Does NOT bypass the decision pipeline. |

---

### 11. Rate Limiter (Isolated → **EXTENSION in V3**)

| Field | Value |
|-------|-------|
| **Capability** | API request rate limiting |
| **Status** | **EXTENSION** (V3) — wired via middleware |
| **Problem Solved** | Prevents API abuse; demonstrates production-readiness patterns |
| **Input** | HTTP requests |
| **Output** | Allow/reject (429 Too Many Requests) |
| **Contract** | `RateLimiter.allow_request() → bool` |
| **Consumer** | FastAPI middleware |
| **Integration Seam** | `app.py` — middleware or dependency |
| **Tests** | `tests/unit/test_production_readiness.py` (RateLimiter tests) |
| **Value** | MEDIUM — production-like behavior |
| **Risk** | LOW — simple interface, configurable via env var |
| **Justification** | RateLimiter is already implemented. Wiring it adds minimal complexity and demonstrates production thinking. Configurable via `CASE_RATE_LIMIT` env var. |

---

### 12. Health Check Enhancement (Connected → **ENHANCED in V3**)

| Field | Value |
|-------|-------|
| **Capability** | System health monitoring |
| **Status** | **ENHANCED** (V3) — richer health data |
| **Problem Solved** | Current `/health` only checks DB; enhancement adds provider health, domain count, circuit breaker state |
| **Input** | None (GET request) |
| **Output** | `HealthStatus` dict with component breakdown |
| **Contract** | `/health` endpoint response |
| **Consumer** | Monitoring, load balancers, UI |
| **Integration Seam** | `app.py:221-241` — enhanced health endpoint |
| **Tests** | Existing API health tests + new component tests |
| **Value** | MEDIUM — operational visibility |
| **Risk** | LOW — additive change to existing endpoint |
| **Justification** | Minimal enhancement to existing endpoint. Shows systems thinking — a real system needs rich health data, not just "DB ok". |

---

### 13. Observability: Correlation IDs (Connected → **ENHANCED in V3**)

| Field | Value |
|-------|-------|
| **Capability** | Request correlation across decision lifecycle |
| **Status** | **ENHANCED** (V3) — `correlation_id` added to `AuditEvent` |
| **Problem Solved** | Currently no way to trace a request across multiple audit events; correlation IDs enable distributed tracing |
| **Input** | API request generates correlation ID |
| **Output** | `AuditEvent.correlation_id` populated on all events for a case |
| **Contract** | `AuditEvent` contract (additive field) |
| **Consumer** | Audit trail, future observability tools |
| **Integration Seam** | `AuditEvent` contract + API layer propagation |
| **Tests** | `tests/unit/test_audit_integrity.py` + new correlation tests |
| **Value** | MEDIUM — traceability |
| **Risk** | LOW — additive field with default, no breaking change |
| **Justification** | Single field addition to existing contract. Demonstrates observability thinking. No breaking change (default empty string). |

---

### 14. Governance Framework (Isolated)

| Field | Value |
|-------|-------|
| **Capability** | RBAC, compliance management, security event logging |
| **Status** | TESTED ISOLATED |
| **Problem Solved** | Role-based access control and compliance tracking |
| **Input** | Role + resource + action |
| **Output** | `bool` (access allowed) |
| **Contract** | `GovernanceFramework` in `governance/__init__.py` |
| **Consumer** | None (not wired) |
| **Integration Seam** | Future: API middleware for RBAC |
| **Tests** | `tests/unit/test_governance.py` (11 tests) |
| **Value** | MEDIUM for portfolio — demonstrates governance thinking |
| **Risk** | MEDIUM — wiring into auth would change existing behavior |
| **Decision** | TESTED ISOLATED — RBAC is a future capability; current API-key auth is sufficient for portfolio scope |

---

### 15. Specialist Models (Isolated)

| Field | Value |
|-------|-------|
| **Capability** | 4 keyword-based specialist models (safety, legal, technical, financial) |
| **Status** | TESTED ISOLATED |
| **Problem Solved** | Deterministic domain-specific analysis alongside LLM |
| **Input** | `OperationalCase` |
| **Output** | `SpecialistPrediction` (action, confidence, reasoning) |
| **Contract** | `SpecialistModel` ABC in `ml/specialist_contracts.py` |
| **Consumer** | None (not wired) |
| **Integration Seam** | Future: `TriageEngine` as parallel signal source |
| **Tests** | `tests/unit/test_specialist_models.py` (10 tests) |
| **Value** | LOW — keyword stubs, not real ML; wiring would add complexity without real value |
| **Risk** | LOW — clean interface |
| **Decision** | TESTED ISOLATED — keyword stubs are not worth wiring into the core path |

---

### 16. Hybrid Decision Engine (Isolated)

| Field | Value |
|-------|-------|
| **Capability** | Multi-source decision reconciliation (LLM + specialist + evidence + risk) |
| **Status** | TESTED ISOLATED |
| **Problem Solved** | Combines multiple decision sources into single output |
| **Input** | LLM output + specialist outputs + evidence + risk assessment |
| **Output** | `HybridDecision` |
| **Contract** | `HybridDecisionEngine` in `hybrid/decision_engine.py` |
| **Consumer** | None (not wired) |
| **Integration Seam** | Future: alternative to `TriageEngine` |
| **Tests** | `tests/unit/test_hybrid_decision_engine.py` (8 tests) |
| **Value** | LOW — duplicates `ReliabilityPipeline` + `AutomationEvaluator` |
| **Risk** | MEDIUM — architectural redundancy |
| **Decision** | DEFERRED — duplicates core functionality; would confuse the architecture |

---

### 17. ML Adaptation Framework (Isolated)

| Field | Value |
|-------|-------|
| **Capability** | Fine-tuning abstractions, dataset pipeline, evaluation runner |
| **Status** | TESTED ISOLATED |
| **Problem Solved** | Future: model adaptation and continuous improvement |
| **Input** | Training data + base model |
| **Output** | Adapted model |
| **Contract** | `ModelAdapter` ABC in `ml/adaptation.py` |
| **Consumer** | None (not wired) |
| **Integration Seam** | Future: `TriageEngine` with adapted model |
| **Tests** | `tests/unit/test_ml_adaptation.py` (9 tests) |
| **Value** | LOW — scaffolding only, no real ML |
| **Risk** | LOW — no core impact |
| **Decision** | TESTED ISOLATED — future capability |

---

### 18. Evaluation Framework (Partially Connected)

| Field | Value |
|-------|-------|
| **Capability** | Cost model (connected), bias evaluation (isolated), deterministic testing (isolated) |
| **Status** | PARTIALLY CONNECTED |
| **Problem Solved** | Cost estimation for LLM calls; bias detection; deterministic evaluation |
| **Input** | `TokenUsage` / evaluation dataset |
| **Output** | `CostEstimate` / `EvaluationResult` |
| **Contract** | `CostModel` in `evaluation/cost.py` |
| **Consumer** | `TriageEngine` (cost), UI (display) |
| **Integration Seam** | `composition.py:103` — `CostModel()` |
| **Tests** | `tests/unit/test_cost_model.py` (8 tests) |
| **Value** | MEDIUM — cost visibility |
| **Risk** | LOW |
| **Decision** | KEEP AS-IS — cost model connected, rest stays isolated |

---

### 19. Logistics Intelligence (Isolated)

| Field | Value |
|-------|-------|
| **Capability** | 10 logistics analysis modules (shipment understanding, classification, carrier matching, route recommendation, risk management, evaluation) |
| **Status** | TESTED ISOLATED |
| **Problem Solved** | Deep logistics-specific analysis |
| **Input** | `ShipmentInput` dataclass |
| **Output** | `ShipmentProfile`, `CarrierMatch`, `RouteRecommendation` |
| **Contract** | Pydantic models in `domain/logistics_*_contracts.py` |
| **Consumer** | None (not wired) |
| **Integration Seam** | Future: `LogisticsPolicy` as enrichment step |
| **Tests** | `tests/unit/test_logistics_*.py` (33 tests across 6 files) |
| **Value** | LOW — well-implemented but complex; wiring adds significant complexity |
| **Risk** | MEDIUM — many modules, potential duplication with core pipeline |
| **Decision** | TESTED ISOLATED — deep domain capability for future use |

---

### 20. `case_logistics` Package (Isolated)

| Field | Value |
|-------|-------|
| **Capability** | Standalone logistics domain package (duplicate of core logistics) |
| **Status** | TESTED ISOLATED |
| **Problem Solved** | Future: standalone logistics vertical |
| **Input** | Same as core logistics |
| **Output** | Same as core logistics |
| **Contract** | Parallel implementations |
| **Consumer** | None |
| **Integration Seam** | Future: standalone package |
| **Tests** | `tests/unit/test_case_logistics_integration.py` (4 tests) |
| **Value** | LOW — duplicates core logistics |
| **Risk** | LOW |
| **Decision** | TESTED ISOLATED — reference implementation |

---

## V3 Integration Decisions

### INTEGRATED (Core path changes)

| # | Capability | Change | Justification |
|---|-----------|--------|---------------|
| 1 | Real Estate Domain | Register in `composition.py` (2 lines) | Proves domain plugin architecture is real |

### EXTENSION (API/UI changes, no core path)

| # | Capability | Change | Justification |
|---|-----------|--------|---------------|
| 2 | USGS Adapter | New `/api/v1/seismic/events` endpoint | Real data demo, adapter pattern |
| 3 | Rate Limiter | Middleware in API | Production-readiness pattern |
| 4 | Health Enhancement | Richer `/health` response | Operational visibility |
| 5 | Correlation IDs | Add field to `AuditEvent` | Observability |

### TESTED ISOLATED (No wiring)

| # | Capability | Reason |
|---|-----------|--------|
| 6 | Governance | RBAC is future scope |
| 7 | Specialist Models | Keyword stubs, not real ML |
| 8 | Hybrid Engine | Duplicates core |
| 9 | ML Adaptation | Scaffolding only |
| 10 | Logistics Intelligence | Deep domain, complex wiring |
| 11 | `case_logistics` | Duplicates core |

### DEFERRED

| # | Capability | Reason |
|---|-----------|--------|
| 12 | Hybrid Decision Engine | Architecturally redundant |

---

## Implementation Plan

### Stage 1: Real Estate Registration
- Register `RealEstatePolicy` + `RealEstateAutomationPolicy` in `composition.py`
- Add `real_estate` automation policy to `_AUTOMATION_POLICIES`
- Verify domain appears in `/domains` endpoint

### Stage 2: USGS API Endpoint
- Add `/api/v1/seismic/events` endpoint in `app.py`
- Import `USGSClient` from `usgs_adapter`
- Return `list[SeismicEvent]` as JSON
- Add `/api/v1/seismic/health` for USGS API health check

### Stage 3: Rate Limiter
- Add `RateLimiter` to `app.py` as middleware
- Configurable via `CASE_RATE_LIMIT` env var
- Return 429 on rate limit exceeded
- Exempt health/docs endpoints

### Stage 4: Health Enhancement
- Enhance `/health` to include provider info, domain count, circuit breaker state
- Add component-level health checks

### Stage 5: Correlation IDs
- Add `correlation_id: str = ""` to `AuditEvent` contract
- Generate correlation ID in API layer
- Propagate to all audit events for a request

### Stage 6: Tests + Quality Gates
- Write tests for new integrations
- Run `pytest`, `ruff check`, `mypy`
- Ensure all existing tests still pass

### Stage 7: Documentation + V4 Proposal
- Update `ARCHITECTURE.md` with new capabilities
- Update `ROADMAP.md` with V3 status
- Create `V4_PROPOSAL.md`

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Core stability | No changes to TriageEngine, ReliabilityPipeline, AutomationEvaluator |
| Breaking changes | All new fields are additive with defaults |
| External dependency (USGS) | Graceful degradation — returns empty list on error |
| Rate limiting | Configurable, exempt health endpoints |
| Auth compatibility | Rate limiter sits alongside existing auth middleware |

---

## Quality Gates

After all V3 changes:

```bash
pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py
ruff check src tests
mypy src --ignore-missing-imports
```

Expected: 0 failures, 0 ruff errors, 0 mypy errors.

---

## V4 Proposal (Preview)

At the end of V3, create `docs/V4_PROPOSAL.md` covering:

1. **Logistics Intelligence Integration** — if clear value case emerges
2. **Governance RBAC** — if multi-user deployment needed
3. **Evaluation Runner API** — automated evaluation endpoints
4. **Observability Stack** — structured logging, metrics export
5. **WebSocket Support** — real-time case updates
6. **Multi-tenancy** — if deployment scenario requires it
