# CASE Development Status

> Detailed technical snapshot. Last verified: 2026-09-14.
> Source of truth for current implementation state.

---

## 1. Project Identity

**CASE** — AI Decision Platform
- Domain-agnostic
- Provider-agnostic
- Foundation v0.3 FROZEN
- Blueprint v1.1 FROZEN
- Portfolio-grade research/engineering project

---

## 2. Repository Status

| Field | Value |
|-------|-------|
| Path | `C:\Users\JUAN\Desktop\Proyectos\CASE` |
| Branch | `master` |
| HEAD | `ecd85b9` |
| Commits | 18 |
| Remote | NONE |
| Working tree | Clean |

---

## 3. Verified Quality

| Check | Result |
|-------|--------|
| pytest | 526 passed, 7 skipped, 0 failures |
| ruff | 0 errors |
| mypy | 0 errors (82 source files) |
| Integration tests | 11 pass, 7 skipped (Ollama) |

---

## 4. Architecture — Actual State

### 4.1 Connected Pipeline (Running System)

```
Streamlit (display only)
   ↓
FastAPI (HTTP adapter, 11 endpoints)
   ↓
composition.py (dependency wiring)
   ↓
TriageEngine (application layer orchestrator)
   ↓
DomainRegistry → DomainPolicy (3 registered domains)
   ↓
PromptBuilder → LLMProvider (via port)
   ↓
ReliabilityPipeline (parse → schema → semantic → domain → retry → repair)
   ↓
AutomationEvaluator (risk assessment → AUTO_APPROVE / HUMAN_REVIEW / ESCALATE)
   ↓
DecisionRepositoryPort (persistence)
   ↓
AuditPort (audit trail)
```

### 4.2 Isolated Modules (Not Connected to Pipeline)

These modules exist as standalone implementations. They are tested but NOT wired into the running system.

| Module | Location | Purpose |
|--------|----------|---------|
| Logistics Intelligence | domain/logistics_*.py (8 files) | Shipment classification, routing, carrier matching |
| ML Adaptation | ml/*.py (7 files) | Training abstractions, dataset pipeline, LoRA config |
| Specialist Models | ml/specialist_*.py (2 files) | Keyword-based classification/risk/routing specialists |
| Hybrid Decision Engine | hybrid/decision_engine.py | Multi-source decision combination |
| Real Estate Domain | domain/real_estate_policy.py | Domain policy (NOT registered) |
| Governance | governance/__init__.py | Security, compliance, access control |
| Production | production/__init__.py | Circuit breaker, rate limiter, health checks |

---

## 5. Core Components — Connected

### 5.1 Contracts (`src/case_core/contracts/`)

| File | Models | Status |
|------|--------|--------|
| `operational_case.py` | UrgencyLevel, OperationalCase | CONNECTED |
| `decision.py` | AIProposal, HumanOverride, TriageDecision | CONNECTED |
| `lifecycle.py` | ProcessingLifecycle (20 states), DecisionLifecycle (8 states) | CONNECTED |
| `evidence.py` | EvidenceType, EvidenceItem | CONNECTED |
| `error.py` | ErrorCategory, CASEError | CONNECTED |
| `audit.py` | AuditEvent | CONNECTED |
| `llm.py` | DecodingParameters, LLMRequest, LLMResponse | CONNECTED |
| `automation.py` | AutomationDecision, RiskLevel, RiskAssessment | CONNECTED |
| `telemetry.py` | TokenUsage, OperationalTelemetry, LLMTelemetry | DEFINED (unused) |

### 5.2 Ports (`src/case_core/ports/`)

| Port | Interface | Status |
|------|-----------|--------|
| `LLMProvider` | complete(), health_check(), name, model | CONNECTED |
| `DomainPolicy` | validate_evidence(), classify_urgency(), get_domain_context(), domain_name | CONNECTED |
| `AuditPort` | log_event(), get_events_by_case() | CONNECTED |
| `RepositoryPort` | save_case(), get_case(), list_cases() | CONNECTED |
| `DecisionRepositoryPort` | save_decision(), get_decision(), list_pending_review(), update_lifecycle() | CONNECTED |
| `AutomationPolicy` | assess_risk(), get_risk_factors(), get_automation_rules(), domain_name | CONNECTED |

### 5.3 Domain System

| Component | Status | Evidence |
|-----------|--------|----------|
| DomainRegistry | CONNECTED | register(), get(), list_domains(), validate_domain() |
| UrbanPolicy | CONNECTED | validate_evidence(), classify_urgency(), get_domain_context() |
| LogisticsPolicy | CONNECTED | validate_evidence(), classify_urgency(), get_domain_context(), classify_incident_type(), get_recommended_actions() |
| InfrastructurePolicy | CONNECTED | validate_evidence(), classify_urgency(), get_domain_context() |
| LogisticsAutomationPolicy | CONNECTED | assess_risk(), _requires_hitl(), _decide_automation(), 5 departments |
| DefaultAutomationPolicy | CONNECTED | Conservative generic policy for Urban/Infrastructure |
| RealEstatePolicy | ISOLATED | Implemented but NOT registered in DomainRegistry |

---

## 6. Application Layer

### 6.1 Composition (`src/case_core/composition.py`)

| Aspect | Detail |
|--------|--------|
| File | `src/case_core/composition.py` (63 lines) |
| Function | `create_app_dependencies() -> AppDependencies` |
| Returns | `AppDependencies` dataclass: engine, registry, audit_adapter, decision_repo |
| Registered Domains | UrbanPolicy, LogisticsPolicy, InfrastructurePolicy |
| Default Provider | MockProvider |
| Automation Policies | LogisticsAutomationPolicy (logistics), DefaultAutomationPolicy (urban, infrastructure) |

### 6.2 TriageEngine (`src/case_core/application/engine.py`)

| Aspect | Detail |
|--------|--------|
| File | `src/case_core/application/engine.py` (179 lines) |
| Class | `TriageEngine` |
| Result type | `TriageResult` (dataclass: decision, error, processing_lifecycle) |
| Entry point | `async execute(case: OperationalCase) -> TriageResult` |
| Dependencies | DomainRegistry, LLMProvider (port), AuditPort (port), DecisionRepositoryPort (port), automation_policy_fn (callable) |
| Domain-agnostic | VERIFIED — no `if domain ==` checks |
| Provider-agnostic | VERIFIED — accepts LLMProvider port |

---

## 7. Providers

| Provider | File | Tests | Status |
|----------|------|-------|--------|
| MockProvider | `providers/mock.py` | 30 | CONNECTED (default) |
| OllamaProvider | `providers/ollama.py` | 13 + 5 integration | CONNECTED (via swap) |
| CloudProvider | `providers/cloud.py` | 28 | CONNECTED (via swap) |

---

## 8. Reliability

**Single pipeline:** `src/case_core/reliability/pipeline.py`

| Stage | Status |
|-------|--------|
| JSON parsing | CONNECTED |
| Schema validation | CONNECTED |
| Semantic validation | CONNECTED |
| Domain validation | CONNECTED |
| Retry with backoff | CONNECTED |
| Terminal failure | CONNECTED |
| Automation assessment | CONNECTED |

---

## 9. API

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | CONNECTED |
| `/domains` | GET | CONNECTED |
| `/api/v1/triage` | POST | CONNECTED |
| `/api/v1/audit/{case_id}` | GET | CONNECTED |
| `/api/v1/hitl/pending` | GET | CONNECTED |
| `/api/v1/hitl/{decision_id}` | GET | CONNECTED |
| `/api/v1/hitl/{decision_id}/under-review` | POST | CONNECTED |
| `/api/v1/hitl/{decision_id}/approve` | POST | CONNECTED |
| `/api/v1/hitl/{decision_id}/reject` | POST | CONNECTED |
| `/api/v1/hitl/{decision_id}/escalate` | POST | CONNECTED |
| `/api/v1/hitl/{decision_id}/modify` | POST | CONNECTED |

---

## 10. Testing

### 10.1 Test Summary

| Suite | Tests | Status | Type |
|-------|-------|--------|------|
| test_behavioral.py | 79 | PASS | behavioral |
| test_bias_evaluation.py | 14 | PASS | bias |
| test_cloud_provider.py | 28 | PASS | contract |
| test_contracts.py | 23 | PASS | contract |
| test_domain.py | 38 | PASS | domain |
| test_evaluation.py | 15 | PASS | evaluation |
| test_governance.py | 28 | PASS | unit (isolated) |
| test_hybrid_decision.py | 18 | PASS | unit (isolated) |
| test_ml_adaptation.py | 26 | PASS | unit (isolated) |
| test_mock_provider.py | 30 | PASS | contract |
| test_ollama_provider.py | 13 | PASS | contract |
| test_ports.py | 8 | PASS | contract |
| test_production.py | 28 | PASS | unit (isolated) |
| test_prompt_builder.py | 17 | PASS | unit |
| test_real_estate_domain.py | 28 | PASS | unit (isolated) |
| test_regression.py | 15 | PASS | regression |
| test_reliability.py | 26 | PASS | unit |
| test_security.py | 31 | PASS | security |
| test_specialist_models.py | 21 | PASS | unit (isolated) |
| test_sqlite.py | 10 | PASS | persistence |
| test_streamlit_boundary.py | 2 | PASS | boundary |
| test_triage_engine.py | 25 | PASS | unit |
| test_api.py | 11 | PASS | integration |
| test_ollama_integration.py | 7 | SKIP | integration |

**Total: 526 passed, 7 skipped, 0 failures**

### 10.2 Test Classification

| Category | Suites | Description |
|----------|--------|-------------|
| **Unit** | test_domain, test_triage_engine, test_prompt_builder, test_reliability | Core pipeline tests |
| **Contract** | test_contracts, test_ports, test_mock_provider, test_ollama_provider, test_cloud_provider | Interface/schema validation |
| **Integration** | test_api, test_ollama_integration | End-to-end API tests |
| **Behavioral** | test_behavioral | 30 behavioral scenarios (BS001-BS030) |
| **Security** | test_security | 31 tests, 10 attack scenarios |
| **Bias** | test_bias_evaluation | Counterfactual pair analysis |
| **Regression** | test_regression | Normal, edge, failure, injection cases |
| **Persistence** | test_sqlite | SQLite adapter tests |
| **Boundary** | test_streamlit_boundary | Streamlit integration boundary |
| **Isolated** | test_governance, test_hybrid_decision, test_ml_adaptation, test_production, test_real_estate_domain, test_specialist_models | Tests for isolated modules |

---

## 11. Known Technical Debt

1. **Isolated modules not wired** — Phase 2-8 modules exist but aren't connected to pipeline
2. **Real Estate not registered** — real_estate_policy.py implemented but not in DomainRegistry
3. **Urban/Infrastructure missing routing** — No `classify_incident_type()` method
4. **Bias pairs logistics-only** — Zero pairs for Urban or Infrastructure
5. **OperationalTelemetry/LLMTelemetry unused** — Defined but not used in pipeline
6. **No CHANGELOG for phases 2-8** — Only v0.1.0 documented
7. **No LICENSE file** — License TBD
8. **No ARCHITECTURE.md** — Missing technical architecture doc
9. **No DECISION_LOG.md** — Missing decision record

---

## 12. Known Limitations

- MockProvider primary evidence source (not real LLMs)
- Offline evaluation (15 cases, CPU-only)
- Security/bias tested only with MockProvider
- No production deployment
- No authentication/authorization
- No rate limiting
- No monitoring/observability beyond audit trail
- No multi-tenant support
- No streaming responses
- Urban/Infrastructure use generic DefaultAutomationPolicy
- No bias pairs for Urban or Infrastructure
- SQLite only

---

## 13. Completed Decisions

| Decision | Date | Status |
|----------|------|--------|
| Foundation v0.3 FROZEN | 2026-09 | COMPLETED |
| Blueprint v1.1 FROZEN | 2026-09 | COMPLETED |
| llama3.2 as primary model | 2026-09 | COMPLETED |
| TriageEngine as application orchestrator | 2026-09-11 | COMMITTED |
| API delegates to TriageEngine | 2026-09-11 | COMMITTED |
| Composition Root extraction | 2026-09-11 | COMMITTED |
| Risk-based automation wired | 2026-09-11 | COMMITTED |
| Phase 1 (CASE v1) consolidated | 2026-09-12 | COMMITTED |
| Autonomous execution protocol adopted | 2026-09-12 | COMMITTED |
| Phase 2-8 implemented (isolated) | 2026-09-14 | COMMITTED |
| Root benchmark files removed | 2026-09-14 | COMMITTED |

---

## 14. Deferred Work

- Wire isolated modules to pipeline (requires justification per I10)
- Register RealEstatePolicy in DomainRegistry
- Urban/Infrastructure routing
- Urban/Infrastructure domain-specific automation
- Bias pairs for Urban and Infrastructure
- Integration tests for isolated modules
- ARCHITECTURE.md
- DECISION_LOG.md
- LICENSE
- API documentation (OpenAPI)
- Contributing guide
