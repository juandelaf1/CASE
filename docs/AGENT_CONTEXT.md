# CASE Agent Context

READ THIS FILE BEFORE MODIFYING CASE.

> Last verified: 2026-09-14 by autonomous agent. All claims verified against actual repository state.

---

## Project Identity

CASE (Case Assessment and Structured Evaluation) is a domain-agnostic, provider-agnostic AI Decision Platform. It transforms unstructured operational cases into structured, validated, evidence-backed decisions with human oversight.

**Core architecture:** Contracts → Ports → Domain → Providers → Reliability → Application → API → UI

**Frozen specs:** Foundation v0.3, Blueprint v1.1. Do not modify without explicit decision.

**Project type:** Portfolio-grade research/engineering project. Production-oriented architecture. Not a production system.

---

## Current Repository

| Field | Value |
|-------|-------|
| Path | `C:\Users\JUAN\Desktop\Proyectos\CASE` |
| Branch | `master` |
| HEAD | `ecd85b9` |
| Commits | 18 |
| Remote | NONE |
| Working tree | Clean |
| Python | 3.13.12 via `C:\Users\JUAN\miniconda3\python.exe` |
| Platform | Windows (PowerShell) |

---

## Verified Quality Status

| Check | Result |
|-------|--------|
| pytest | 526 passed, 7 skipped, 0 failures |
| ruff | 0 errors |
| mypy | 0 errors (82 source files) |
| Integration tests | 11 pass, 7 skipped (Ollama) |

---

## Current Project State

### What Is ACTUALLY Connected to the Pipeline

These components are wired into the running system via `composition.py` and `TriageEngine`:

| Component | Status | Evidence |
|-----------|--------|----------|
| Contracts (9 files, Pydantic v2) | CONNECTED | Used by all layers |
| Ports (6 ABC interfaces) | CONNECTED | Used by engine, providers, persistence |
| DomainRegistry | CONNECTED | 3 domains registered: urban_operations, logistics, infrastructure |
| TriageEngine | CONNECTED | Application-layer orchestrator |
| ReliabilityPipeline | CONNECTED | Used by TriageEngine |
| AutomationEvaluator | CONNECTED | Used by pipeline |
| PromptBuilder | CONNECTED | Used by TriageEngine |
| MockProvider | CONNECTED | Default provider in composition.py |
| OllamaProvider | CONNECTED | Available via provider swap |
| CloudProvider | CONNECTED | Available via provider swap |
| SQLite persistence | CONNECTED | Decision repo, audit adapter |
| FastAPI API | CONNECTED | 11 endpoints, delegates to TriageEngine |
| Streamlit UI | CONNECTED | Display only, reads from API |

### What Is ISOLATED (Not Connected to Pipeline)

These modules exist as standalone implementations. They are tested in isolation but are NOT called by TriageEngine or wired into the running system.

| Module | Files | Status | Notes |
|--------|-------|--------|-------|
| **Logistics Intelligence** | logistics_classification.py, logistics_route_recommendation.py, logistics_carrier_matching.py, logistics_joint_recommendation.py, logistics_risk_automation.py, logistics_evaluation.py, logistics_contracts.py, logistics_understanding.py | ISOLATED | Standalone implementations, not imported by pipeline |
| **ML Adaptation** | ml/training_abstraction.py, ml/dataset_contracts.py, ml/dataset_pipeline.py, ml/lora_config.py, ml/adapters.py, ml/evaluation.py, ml/evaluation_dataset.py | ISOLATED | Abstract interfaces and mock implementations |
| **Specialist Models** | ml/specialist_models.py, ml/specialist_contracts.py | ISOLATED | Keyword-based specialists, not wired to pipeline |
| **Hybrid Decision Engine** | hybrid/decision_engine.py | ISOLATED | Standalone engine, not used by TriageEngine |
| **Real Estate Domain** | domain/real_estate_policy.py | ISOLATED | NOT registered in DomainRegistry |
| **Governance** | governance/__init__.py | ISOLATED | SecurityManager, ComplianceManager — standalone |
| **Production** | production/__init__.py | ISOLATED | CircuitBreaker, RateLimiter — standalone |

**Important:** These isolated modules are valid implementations that demonstrate the architecture's extensibility. They are NOT broken or incomplete — they simply haven't been wired into the main pipeline. Wiring them would require explicit architectural decisions and justification.

### Domain Packs — Actual Status

| Domain | Registered | Policy | Routing | Automation | Bias Pairs |
|--------|------------|--------|---------|------------|------------|
| **Logistics** | YES | Full | 6 incident types | LogisticsAutomationPolicy | 10 pairs |
| **Urban Operations** | YES | Partial | None (keyword urgency only) | DefaultAutomationPolicy | 0 |
| **Infrastructure** | YES | Partial | None (keyword urgency only) | DefaultAutomationPolicy | 0 |
| **Real Estate** | NO | Implemented | Implemented | Implemented | 0 |

---

## COMPLETED (Connected & Working)

- Contracts (9 files, Pydantic v2)
- Ports (6 interfaces)
- DomainRegistry (3 registered domains)
- ReliabilityPipeline (parse, schema, semantic, domain, retry, repair)
- PromptBuilder (TIER1 + TIER3 security)
- TriageEngine (application layer orchestrator, 179 lines)
- Composition Root (composition.py — dependency wiring)
- MockProvider (30 tests)
- OllamaProvider (13 tests + 5 integration)
- CloudProvider (28 tests)
- Evaluation Framework (runner, metrics, reports)
- Streamlit UI (Decision Center, Status, HITL display)
- HITL Lifecycle (6 API endpoints, lifecycle states, audit)
- Security Evaluation (31 tests, 10 attack scenarios)
- Risk-Based Automation (12 tests + 3 security)
- Bias Evaluation (23 tests, routing_invariance fixed)
- API (delegates to TriageEngine)
- Persistence (SQLite adapters)
- Audit (AuditPort, event trail)

## IMPLEMENTED (Isolated — Not Wired)

- Logistics Intelligence (8 modules, standalone)
- ML Adaptation (7 modules, abstract interfaces)
- Specialist Models (2 modules, keyword-based)
- Hybrid Decision Engine (1 module, standalone)
- Real Estate Domain Pack (1 module, not registered)
- Governance Framework (1 module, standalone)
- Production Readiness (1 module, standalone)

---

## CURRENT PRIORITY

**POST-V1.0 — Integration Selection & Hardening.** Audit complete. First integration: ShipmentUnderstanding (v1.0.1).

---

## NEXT PRIORITY

**v1.0.1 — ShipmentUnderstanding Integration.** Wire ShipmentUnderstanding to composition.py for logistics domain pre-processing.
- New domain packs (with justification)

---

## FROZEN INVARIANTS

| ID | Principle | Status |
|----|-----------|--------|
| I01 | Domain-agnostic core | VERIFIED |
| I02 | Provider-agnostic via ports | VERIFIED |
| I03 | Raw LLM output never trusted | VERIFIED |
| I04 | Critical boundaries type-safe | VERIFIED |
| I05 | Failures explicit | VERIFIED |
| I06 | Human oversight (HITL) | VERIFIED |
| I07 | Quality claims require evidence | VERIFIED |
| I08 | Benchmarks cannot be fabricated | VERIFIED |
| I09 | Minimize sensitive data | VERIFIED |
| I10 | Complexity requires justification | VERIFIED |
| I11 | Public contracts cannot change silently | VERIFIED |
| I12 | Domain logic cannot leak into Core | VERIFIED |
| I13 | Provider-specific logic behind interfaces | VERIFIED |
| I14 | Production claims require evidence | VERIFIED |
| I15 | Limitations documented | VERIFIED |

---

## KNOWN LIMITATIONS

- MockProvider primary evidence source (not real LLMs)
- Offline evaluation (15 cases, CPU-only)
- Security/bias tested only with MockProvider
- No production deployment
- No authentication/authorization
- No rate limiting (in production sense)
- No monitoring/observability beyond audit trail
- No multi-tenant support
- No streaming responses
- Urban/Infrastructure use generic DefaultAutomationPolicy
- No bias pairs for Urban or Infrastructure domains
- Isolated modules not wired to pipeline
- SQLite only (no concurrent production use)

---

## DO NOT TOUCH

- `src/case_core/contracts/` — Frozen foundation
- `src/case_core/ports/` — Frozen interfaces
- `src/case_core/application/engine.py` — Core orchestrator
- `src/case_core/reliability/pipeline.py` — Core validation
- `src/case_core/prompts/builder.py` — Frozen prompts
- Frozen specs (Foundation v0.3, Blueprint v1.1)

---

## DO NOT REINTRODUCE

- Benchmark scripts in root directory
- Model download/evaluation scripts
- Unjustified dependencies
- Domain logic in core
- Provider-specific code in ports
- `Any`/`dict` at critical boundaries without justification

---

## NEXT RECOMMENDED ACTION

1. Integrate ShipmentUnderstanding (v1.0.1)
2. Register RealEstatePolicy (v1.0.2)
3. Architecture review after integrations

---

## QUALITY GATES

After any code change:

```powershell
python -m pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py
python -m ruff check src tests
python -m mypy src --ignore-missing-imports
```

Expected:
- 0 pytest failures
- 0 ruff errors
- 0 mypy errors

---

## UPDATE PROTOCOL

This file must be updated when:
- A milestone is completed
- The current priority changes
- A new phase begins
- A significant architectural decision is made
- The working tree state changes materially
