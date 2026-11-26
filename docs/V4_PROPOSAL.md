# V4 Proposal — CASE Platform Evolution

**Date:** 2026-09-28  
**Baseline:** V3 Ecosystem Integration (779 tests, 5 domains, rate limiting, USGS adapter)

---

## Current State (V3)

### Connected Ecosystem
- **Core:** TriageEngine + ReliabilityPipeline + AutomationEvaluator
- **5 Domains:** urban_operations, logistics, infrastructure, seismic_risk, real_estate
- **4 Providers:** Mock, Groq, Ollama, Cloud — all wrapped in CircuitBreakerProvider
- **API:** 15 endpoints (13 original + 2 seismic)
- **Auth:** Constant-time API key authentication
- **Rate Limiting:** Per-IP sliding window (configurable)
- **Persistence:** SQLite with append-only audit
- **Health:** Rich health endpoint with domain/provider info
- **Observability:** Correlation IDs in audit events
- **UI:** 9-page Streamlit interface

### Tested Isolated (Available for Future)
- Governance Framework (RBAC, compliance)
- Specialist Models (keyword-based)
- Hybrid Decision Engine
- ML Adaptation Framework
- Logistics Intelligence (10 modules)
- `case_logistics` standalone package

---

## V4 Proposals

### P1: Governance RBAC Integration (Priority: Medium)

**What:** Wire `GovernanceFramework` into API middleware for role-based access control.

**Why:** Currently any valid API key can access all endpoints. RBAC enables:
- Viewer: read-only access to cases
- Analyst: create/update cases
- Manager: approve/reject decisions
- Admin: full access + configuration
- Auditor: read + audit trail access

**How:**
1. Add `role` field to API key format (or separate header)
2. Create `RBACMiddleware` that checks `GovernanceFramework.check_access()`
3. Protect HITL endpoints (approve/reject/modify) with MANAGER+ role
4. Protect configuration endpoints with ADMIN role
5. Audit all access attempts via `GovernanceFramework.audit_data_access()`

**Risk:** MEDIUM — changes auth behavior, requires migration strategy
**Effort:** 2-3 days

---

### P2: Evaluation Runner API (Priority: Medium)

**What:** Expose `EvaluationRunner` via API for automated evaluation runs.

**Why:** Currently evaluation is manual via Streamlit. API enables:
- CI/CD integration for regression testing
- Automated benchmark runs
- Programmatic evaluation workflows

**How:**
1. Create `/api/v1/evaluation/run` endpoint
2. Accept dataset configuration (domain, provider, sample size)
3. Return `EvaluationResult` with metrics
4. Store results in SQLite for comparison
5. Add `/api/v1/evaluation/history` for past results

**Risk:** LOW — standalone module, no core changes
**Effort:** 1-2 days

---

### P3: Structured Logging + Metrics Export (Priority: Low)

**What:** Replace print-based logging with structured JSON logging + metrics export.

**Why:** Production systems need:
- Correlated logs across services
- Metrics export to Prometheus/Grafana
- Structured audit trail for compliance

**How:**
1. Add `structlog` or `python-json-logger`
2. Configure JSON log format with correlation_id
3. Add `/api/v1/metrics` endpoint (Prometheus format)
4. Wire `PerformanceMonitor` to record real metrics
5. Add log level configuration via `CASE_LOG_LEVEL` env var

**Risk:** LOW — additive, no core changes
**Effort:** 1-2 days

---

### P4: WebSocket Real-time Updates (Priority: Low)

**What:** Add WebSocket endpoint for real-time case updates.

**Why:** Streamlit polls for updates. WebSocket enables:
- Real-time decision notifications
- Live HITL status updates
- Push-based dashboard updates

**How:**
1. Add `/ws/cases/{case_id}` endpoint
2. Publish events on decision lifecycle changes
3. Streamlit subscribes to updates
4. Add connection management and heartbeat

**Risk:** LOW — new endpoint, no core changes
**Effort:** 2-3 days

---

### P5: Multi-tenancy (Priority: Low)

**What:** Add tenant isolation for multi-organization deployments.

**Why:** Current system is single-tenant. Multi-tenancy enables:
- Organization-level data isolation
- Per-tenant configuration
- Usage tracking per organization

**How:**
1. Add `tenant_id` to all contracts
2. Filter queries by tenant_id
3. Add tenant configuration in API
4. Isolate audit trails per tenant

**Risk:** MEDIUM — contract changes, migration needed
**Effort:** 3-5 days

---

### P6: Logistics Intelligence Integration (Priority: Low)

**What:** Wire logistics intelligence modules as enrichment signals.

**Why:** Currently logistics decisions use generic LLM reasoning. Enrichment adds:
- Deterministic shipment classification
- Carrier matching recommendations
- Route optimization signals

**How:**
1. Create `LogisticsEnrichment` class that wraps the 10 modules
2. Add enrichment step in `TriageEngine` for logistics domain
3. Feed enrichment signals into `ReliabilityPipeline` as evidence
4. Add enrichment metadata to `TriageDecision`

**Risk:** MEDIUM — complex wiring, many modules
**Effort:** 3-5 days

---

## Recommended V4 Scope

### Minimum Viable V4
- **P1:** Governance RBAC (demonstrates production thinking)
- **P2:** Evaluation Runner API (enables automated testing)

### Full V4
- P1 + P2 + P3 + P4

### Deferred to V5
- P5 (Multi-tenancy)
- P6 (Logistics Intelligence)

---

## Success Criteria

| Metric | V3 | V4 Target |
|--------|-----|-----------|
| Tests | 779 | 800+ |
| Domains | 5 | 5 (no new) |
| API Endpoints | 15 | 17+ |
| Auth | API key | API key + RBAC |
| Evaluation | Manual | API-driven |
| Logging | Print | Structured JSON |
| Real-time | Polling | WebSocket |

---

## Anti-patterns to Avoid

1. **No core rewrites** — extend, don't replace
2. **No new dependencies without justification** — I10 applies
3. **No breaking changes** — additive fields only
4. **No fake integrations** — every connection must be tested
5. **No scope creep** — V4 is RBAC + Evaluation, not everything

---

## Timeline

| Week | Focus |
|------|-------|
| 1 | P1: Governance RBAC |
| 2 | P2: Evaluation Runner API |
| 3 | P3: Structured Logging |
| 4 | P4: WebSocket + Polish |

**Total:** 4 weeks for full V4, 2 weeks for minimum viable V4.
