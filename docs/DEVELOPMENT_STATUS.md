# CASE Development Status

> Detailed technical snapshot of the project. Updated 2026-09-11.
> Source of truth for current implementation state.

---

## 1. Project Identity

**CASE** — AI Decision Platform
- Domain-agnostic
- Provider-agnostic
- Foundation v0.3 FROZEN
- Blueprint v1.1 FROZEN

---

## 2. Repository Status

| Field | Value |
|-------|-------|
| Path | `C:\Users\JUAN\Desktop\Proyectos\CASE` |
| Branch | `master` |
| HEAD | `9c2a9af` |
| Commits | 3 (`c26dc66`, `65b3832`, `9c2a9af`) |
| Remote | NONE |
| Working tree | 2 files modified + 1 new (Composition Root extraction, uncommitted) |
| Source files | 57 Python files in src/ |
| Test files | 19 Python files in tests/ |

**Pending changes (uncommitted):**
- `src/case_api/api/v1/app.py` — Modified (composition delegated to composition.py)
- `src/case_core/composition.py` — New (46 lines, AppDependencies + create_app_dependencies)

---

## 3. Architecture

```
Streamlit (display only)
   ↓
FastAPI (HTTP adapter)
   ↓
composition.py (dependency wiring: domains, provider, persistence, engine)
   ↓
TriageEngine (application layer orchestrator)
   ↓
DomainRegistry → DomainPolicy (domain resolution)
   ↓
PromptBuilder → LLMProvider (via port)
   ↓
ReliabilityPipeline (parse → schema → semantic → domain → retry → repair)
   ↓
AutomationEvaluator (risk assessment, lifecycle decision)
   ↓
DecisionRepositoryPort (persistence)
   ↓
AuditPort (audit trail)
```

**Verified:** API triage endpoint contains zero references to ReliabilityPipeline, PromptBuilder, or provider internals. All orchestration delegated to `engine.execute(case)`. Composition wiring extracted to `composition.py`.

---

## 4. Core Components

### 4.1 Contracts (`src/case_core/contracts/`)

| File | Models | Status |
|------|--------|--------|
| `operational_case.py` | UrgencyLevel, OperationalCase | COMPLETED |
| `decision.py` | AIProposal, HumanOverride, TriageDecision | COMPLETED |
| `lifecycle.py` | ProcessingLifecycle (20 states), DecisionLifecycle (8 states) | COMPLETED |
| `evidence.py` | EvidenceType, EvidenceItem | COMPLETED |
| `error.py` | ErrorCategory, CASEError | COMPLETED |
| `audit.py` | AuditEvent | COMPLETED |
| `llm.py` | DecodingParameters, LLMRequest, LLMResponse | COMPLETED |
| `automation.py` | AutomationDecision, RiskLevel, RiskAssessment | COMPLETED |
| `telemetry.py` | TokenUsage, OperationalTelemetry, LLMTelemetry | COMPLETED |

**Note:** OperationalTelemetry and LLMTelemetry are defined but NOT used in any pipeline.

### 4.2 Ports (`src/case_core/ports/`)

| Port | Interface | Status |
|------|-----------|--------|
| `LLMProvider` | complete(), health_check(), name, model | COMPLETED |
| `DomainPolicy` | validate_evidence(), classify_urgency(), get_domain_context(), domain_name | COMPLETED |
| `AuditPort` | log_event(), get_events_by_case() | COMPLETED |
| `RepositoryPort` | save_case(), get_case(), list_cases() | COMPLETED |
| `DecisionRepositoryPort` | save_decision(), get_decision(), list_pending_review(), update_lifecycle() | COMPLETED |
| `AutomationPolicy` | assess_risk(), get_risk_factors(), get_automation_rules(), domain_name | COMPLETED |

### 4.3 Domain System

| Component | Status | Evidence |
|-----------|--------|----------|
| DomainRegistry | COMPLETED | register(), get(), list_domains(), validate_domain() |
| UrbanPolicy | PARTIAL | validate_evidence(), classify_urgency(), get_domain_context() — NO routing, NO automation |
| LogisticsPolicy | COMPLETED | validate_evidence(), classify_urgency(), get_domain_context(), classify_incident_type(), get_recommended_actions() |
| InfrastructurePolicy | PARTIAL | validate_evidence(), classify_urgency(), get_domain_context() — NO routing, NO automation |
| LogisticsAutomationPolicy | COMPLETED | assess_risk(), _requires_hitl(), _decide_automation(), 5 departments |

---

## 5. Application Layer

### 5.1 Composition (`src/case_core/composition.py`)

| Aspect | Detail |
|--------|--------|
| File | `src/case_core/composition.py` (46 lines) |
| Function | `create_app_dependencies() -> AppDependencies` |
| Returns | `AppDependencies` dataclass: engine, registry, audit_adapter, decision_repo |
| Responsibilities | Domain registration, provider creation, persistence creation, engine assembly |
| Called by | `app.py` at module load |

### 5.2 TriageEngine (`src/case_core/application/engine.py`)

| Aspect | Detail |
|--------|--------|
| File | `src/case_core/application/engine.py` (175 lines) |
| Class | `TriageEngine` |
| Result type | `TriageResult` (dataclass: decision, error, processing_lifecycle) |
| Entry point | `async execute(case: OperationalCase) -> TriageResult` |
| Dependencies | DomainRegistry, LLMProvider (port), AuditPort (port), DecisionRepositoryPort (port) |
| Domain-agnostic | VERIFIED — AST inspection confirms zero `if domain ==` checks |
| Provider-agnostic | VERIFIED — accepts LLMProvider port, not concrete providers |
| Tests | 15 tests in `tests/unit/test_triage_engine.py` |

**Orchestration flow:**
1. Emit CASE_RECEIVED audit event
2. Resolve domain via DomainRegistry
3. Build prompt via PromptBuilder
4. Invoke LLM via provider port
5. Run ReliabilityPipeline (validation + retry + automation)
6. Build TriageDecision with AIProposal
7. Persist via DecisionRepositoryPort
8. Return TriageResult

---

## 6. Providers

| Provider | File | Tests | Status |
|----------|------|-------|--------|
| MockProvider | `providers/mock.py` | 30 | COMPLETED |
| OllamaProvider | `providers/ollama.py` | 13 + 5 integration | COMPLETED |
| CloudProvider | `providers/cloud.py` | 28 | COMPLETED |

All providers implement `LLMProvider` port. Provider-agnosticism verified.

---

## 7. Reliability

**Single pipeline:** `src/case_core/reliability/pipeline.py` (406 lines)

| Stage | Status |
|-------|--------|
| JSON parsing | COMPLETED |
| Schema validation (5 required fields, enum values, confidence range) | COMPLETED |
| Semantic validation (reason length, evidence_summary length) | COMPLETED |
| Domain validation (policy-specific evidence requirements) | COMPLETED |
| Retry with backoff (MAX_VALIDATION_RETRIES=3) | COMPLETED |
| Transient retry (MAX_TRANSIENT_RETRIES=2) | COMPLETED |
| Terminal failure (ProcessingLifecycle.TERMINAL_FAILURE) | COMPLETED |
| Audit events at each stage | COMPLETED |

**TriageEngine reuses pipeline:** VERIFIED. Engine creates `ReliabilityPipeline` and calls `pipeline.run()`. No duplication.

---

## 8. Validation

Validation lives in `ReliabilityPipeline`:
- `parse()` — JSON parsing
- `schema_validate()` — field presence, enum values, confidence range
- `semantic_validate()` — reason length >= 10, evidence_summary length >= 5
- `domain_validate()` — policy-specific evidence requirements
- `validate_all()` — chains all four

---

## 9. HITL

| Aspect | Detail |
|--------|--------|
| Lifecycle states | AI_PROPOSED → UNDER_REVIEW → APPROVED/MODIFIED/REJECTED/ESCALATED |
| API endpoints | 6: under-review, approve, reject, escalate, modify, pending |
| Persistence | SQLiteDecisionRepository with lifecycle tracking |
| Audit | HITL_UNDER_REVIEW, HITL_APPROVED, HITL_REJECTED, HITL_ESCALATED, HITL_MODIFIED |
| Guardrails | Transition validation (e.g., cannot approve from REJECTED) |
| Tests | TestBS013-TestBS016, TestBS026 (full lifecycle) |

**TriageEngine HITL compatibility:** VERIFIED. Decisions produced with `DecisionLifecycle.AI_PROPOSED` and `AIProposal` — compatible with existing HITL endpoints.

---

## 10. Domain Packs

### 10.1 Urban Operations

| Capability | Status |
|------------|--------|
| Domain Policy | COMPLETED |
| Evidence validation | COMPLETED (requires 1 text evidence) |
| Urgency classification | COMPLETED (keyword-based) |
| Routing (classify_incident_type) | NOT IMPLEMENTED |
| Automation | NOT IMPLEMENTED |
| Bias pairs | 0 |

### 10.2 Logistics

| Capability | Status |
|------------|--------|
| Domain Policy | COMPLETED |
| Evidence validation | COMPLETED (requires text or metric) |
| Urgency classification | COMPLETED (keyword-based, 5 levels) |
| Routing (classify_incident_type) | COMPLETED (6 incident types) |
| Recommended actions | COMPLETED (per incident type) |
| Automation | COMPLETED (LogisticsAutomationPolicy, 5 departments) |
| Bias pairs | 10 pairs |

### 10.3 Infrastructure

| Capability | Status |
|------------|--------|
| Domain Policy | COMPLETED |
| Evidence validation | COMPLETED (requires non-empty) |
| Urgency classification | COMPLETED (keyword-based) |
| Routing (classify_incident_type) | NOT IMPLEMENTED |
| Automation | NOT IMPLEMENTED |
| Bias pairs | 0 |

---

## 11. Risk-Based Automation

| Aspect | Detail |
|--------|--------|
| AutomationPolicy port | COMPLETED |
| AutomationEvaluator | COMPLETED |
| LogisticsAutomationPolicy | COMPLETED (risk matrix, 5 departments, HITL rules) |
| Pipeline integration | COMPLETED (assess_automation() in pipeline.py) |
| Effective urgency | COMPLETED (max(LLM, case) prevents downgrade) |
| Audit events | AUTOMATION_ASSESSED, AUTO_APPROVED, AUTO_ESCALATED, AUTO_HUMAN_REVIEW |
| Security tests | 3 anti-manipulation tests |
| Tests | 12 tests (TestBS029) + 3 security |

**LLM cannot decide automation:** VERIFIED. Automation is assessed by AutomationEvaluator after pipeline validation, not by LLM output.

---

## 12. Security

| Aspect | Detail |
|--------|--------|
| Prompt constraints | TIER3_DEVELOPER (UNTRUSTED instructions) |
| Schema validation | Required fields, enums, confidence range |
| Semantic validation | Reason length, evidence_summary length |
| Domain validation | Policy-specific evidence requirements |
| Effective urgency | max(LLM, case) — prevents downgrade |
| Audit trail | All errors categorized and logged |
| Tests | 28 tests (TestPromptInjectionDefense, TestBS028, TestSecurityPipeline, TestLogisticsDomainSecurity) |
| Scenarios | 10 attack scenarios (injection, impersonation, bypass, manipulation) |

---

## 13. Bias Evaluation

| Aspect | Detail |
|--------|--------|
| Evaluator class | BiasEvaluator (load_pairs, evaluate_pair, compute_results) |
| Standalone functions | 8 metrics (pair consistency, decision invariance, etc.) |
| Bias pairs | 10 pairs, ALL in logistics domain |
| Tests | 8 behavioral (TestBS030) + 8 unit (test_bias_evaluation.py) |
| Documentation | BENCHMARK_BIAS_V0.1.md (44 lines) |

**Known bug:** `routing_invariance_rate` in `compute_results()` uses `decision_consistent / total` instead of a routing-specific check. It is a duplicate of `decision_invariance_rate`.

**Coverage gap:** Zero bias pairs for Urban or Infrastructure domains.

---

## 14. Evaluation Framework

| Component | Status |
|-----------|--------|
| EvaluationRunner | COMPLETED (single + dataset) |
| Metrics calculator | COMPLETED (decision accuracy, urgency accuracy, confidence, timing, error rate, precision/recall) |
| ReportGenerator | COMPLETED (JSON output) |
| Dataset loader | COMPLETED |
| Scenarios | normal_cases, edge_cases, failure_cases, injection_cases, bias_pairs |

---

## 15. Model Evaluation

| Model | Accuracy | Latency | Status |
|-------|----------|---------|--------|
| llama3.2 | 66.67% | ~14.6s | Selected — primary |
| qwen3:8b | 73.33% | ~131s | Alternative |
| phi4-mini | 60.00% | ~19.6s | Discarded |
| gemma3:4b | 60.00% | ~40.8s | Discarded |
| qwen3:4b | — | >120s | Failed (timeout) |
| deepseek-r1:8b | — | >500s | Aborted |

**Caveats:** Offline benchmark, 15 cases, CPU-only, MockProvider for evaluation. Not production performance.

---

## 16. Persistence

| Adapter | File | Status |
|---------|------|--------|
| SQLiteRepository | `sqlite_adapter.py` | COMPLETED |
| SQLiteAuditAdapter | `sqlite_audit.py` | COMPLETED |
| SQLiteDecisionRepository | `sqlite_decision_repository.py` | COMPLETED |

---

## 17. API

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | COMPLETED |
| `/domains` | GET | COMPLETED |
| `/api/v1/triage` | POST | COMPLETED (delegates to TriageEngine) |
| `/api/v1/audit/{case_id}` | GET | COMPLETED |
| `/api/v1/hitl/pending` | GET | COMPLETED |
| `/api/v1/hitl/{decision_id}` | GET | COMPLETED |
| `/api/v1/hitl/{decision_id}/under-review` | POST | COMPLETED |
| `/api/v1/hitl/{decision_id}/approve` | POST | COMPLETED |
| `/api/v1/hitl/{decision_id}/reject` | POST | COMPLETED |
| `/api/v1/hitl/{decision_id}/escalate` | POST | COMPLETED |
| `/api/v1/hitl/{decision_id}/modify` | POST | COMPLETED |

---

## 18. UI

**Streamlit app** (`streamlit_app/`):
- Decision Center (triage form + results)
- System Status
- HITL display (pending review list)

Display only. No auth. No write operations.

---

## 19. Audit

| Aspect | Detail |
|--------|--------|
| AuditPort | COMPLETED |
| SQLiteAuditAdapter | COMPLETED |
| Events | CASE_RECEIVED, AI_GENERATED, AUTOMATION_ASSESSED, FINAL_DECISION, AUTO_APPROVED, AUTO_ESCALATED, AUTO_HUMAN_REVIEW, HITL_* |
| TriageEngine emits | CASE_RECEIVED |
| Pipeline emits | AI_GENERATED, AUTOMATION_ASSESSED, FINAL_DECISION, AUTO_* |
| API HITL emits | HITL_UNDER_REVIEW, HITL_APPROVED, HITL_REJECTED, HITL_ESCALATED, HITL_MODIFIED |

---

## 20. Tests

```
384 collected → 377 passed, 7 skipped, 0 failed
```

| Suite | Tests | Status |
|-------|-------|--------|
| test_api.py (integration) | 11 | PASS |
| test_ollama_integration.py | 7 | SKIPPED (no Ollama) |
| test_behavioral.py | 42 | PASS |
| test_bias_evaluation.py | 8 | PASS |
| test_cloud_provider.py | 28 | PASS |
| test_contracts.py | 23 | PASS |
| test_domain.py | 38 | PASS |
| test_evaluation.py | 17 | PASS |
| test_mock_provider.py | 30 | PASS |
| test_ollama_provider.py | 13 | PASS |
| test_ports.py | 8 | PASS |
| test_prompt_builder.py | 17 | PASS |
| test_regression.py | 15 | PASS |
| test_reliability.py | 28 | PASS |
| test_security.py | 28 | PASS |
| test_sqlite.py | 10 | PASS |
| test_streamlit_boundary.py | 2 | PASS |
| test_streamlit_client.py | 17 | PASS |
| test_triage_engine.py | 15 | PASS |

---

## 21. Ruff

```
65 errors (58 fixable, 7 hidden with --unsafe-fixes)
```

All pre-existing. No new errors introduced by TriageEngine implementation. Dominant issues: import sorting (I001), missing newlines (W292), unused imports (F401).

---

## 22. Mypy

```
22 errors in 11 files (checked 57 source files)
```

All pre-existing. No new errors introduced. Dominant issue: missing type arguments for generic `dict` (type-arg). Configuration: `strict = true`, `python_version = 3.11`, `disallow_untyped_defs = true`.

---

## 23. Known Technical Debt

1. **routing_invariance_rate bug** — `compute_results()` in bias.py uses `decision_consistent / total` instead of routing-specific check
2. **Urban/Infrastructure missing routing** — No `classify_incident_type()` method
3. **Urban/Infrastructure missing automation** — No AutomationPolicy implementations
4. **Bias pairs logistics-only** — Zero pairs for Urban or Infrastructure
5. ~~**Composition wiring in app.py**~~ — RESOLVED. Extracted to `composition.py`.
6. **OperationalTelemetry/LLMTelemetry unused** — Defined in contracts but not consumed
7. **pyproject.toml includes sqlalchemy** — Dependency listed but not used (SQLite uses sqlite3 directly)
8. **tests/behavioral/ and tests/evaluation/ empty** — Directories exist but contain no files
9. **Mypy dict type-arg errors** — 14 of 22 errors are missing dict type arguments
10. **Ruff import sorting** — 58 fixable import ordering issues across test files

---

## 24. Known Limitations

- MockProvider only for most tests (not real LLMs)
- Offline evaluation (15 cases, CPU-only)
- Security evaluation only with MockProvider (not tested against real adversarial LLMs)
- Bias evaluation only with MockProvider
- No production deployment
- No authentication/authorization
- No rate limiting
- No monitoring/observability beyond audit trail
- No multi-tenant support
- No streaming responses

---

## 25. Current Risks

1. **Working tree dirty** — TriageEngine implementation uncommitted, risk of loss
2. **Composition coupling** — API layer acts as both HTTP adapter and composition root
3. **Bias evaluation incomplete** — routing_invariance_rate bug, logistics-only coverage
4. **No real LLM testing** — Security and bias evaluations only with MockProvider
5. **Documentation gaps** — No CHANGELOG, no LICENSE, no API documentation

---

## 26. Completed Decisions

| Decision | Date | Status |
|----------|------|--------|
| Foundation v0.3 FROZEN | 2026-09 | COMPLETED |
| Blueprint v1.1 FROZEN | 2026-09 | COMPLETED |
| llama3.2 as primary model | 2026-09 | COMPLETED |
| TriageEngine as application orchestrator | 2026-09-11 | COMPLETED |
| API delegates to TriageEngine | 2026-09-11 | COMPLETED |
| Composition Root extraction | 2026-09-11 | COMPLETED (uncommitted) |

---

## 27. Open Decisions

| Decision | Status |
|----------|--------|
| Fix routing_invariance_rate | NEXT |
| Urban/Infrastructure Automation | DEFERRED |
| Urban/Infrastructure Routing | DEFERRED |
| Final evaluation | DEFERRED |

---

## 28. Deferred Work

- Urban/Infrastructure Automation
- Urban/Infrastructure Routing
- Fix routing_invariance_rate bug
- Bias pairs for Urban and Infrastructure
- Final evaluation
- Quality hardening
- CHANGELOG
- LICENSE
- API documentation (OpenAPI)
- Contributing guide
