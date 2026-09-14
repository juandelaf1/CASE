# CASE Architecture

> Technical architecture documentation. Last verified: 2026-09-14.

---

## Overview

CASE is a layered AI decision platform with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                      UI Layer                           │
│              Streamlit (display only)                   │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────┐
│                     API Layer                           │
│           FastAPI (HTTP adapter, 11 endpoints)          │
│           Delegates to TriageEngine                     │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                  Application Layer                      │
│     composition.py (dependency wiring)                  │
│     TriageEngine (orchestrator, 179 lines)              │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    Domain Layer                         │
│     DomainRegistry (3 registered domains)               │
│     DomainPolicy (validation, urgency, context)         │
│     AutomationPolicy (risk assessment)                  │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Ports Layer                           │
│     LLMProvider, DomainPolicy, AuditPort,              │
│     RepositoryPort, DecisionRepositoryPort,            │
│     AutomationPolicy                                   │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                 Infrastructure Layer                    │
│     Providers (Mock, Ollama, Cloud)                    │
│     Persistence (SQLite adapters)                      │
│     ReliabilityPipeline (validation chain)             │
└─────────────────────────────────────────────────────────┘
```

---

## Layers

### 1. Contracts Layer (`src/case_core/contracts/`)

**Purpose:** Type-safe data models for all domain objects.

**Dependencies:** Pydantic v2 only.

**Key Models:**
- `OperationalCase` — Input case with report text, domain, urgency
- `TriageDecision` — Output decision with action, reason, urgency, confidence
- `AIProposal` — Original LLM proposal (preserved for audit)
- `EvidenceItem` — Evidence with type, content, source, confidence
- `AuditEvent` — Audit trail event
- `RiskAssessment` — Risk evaluation result

**Rule:** No business logic in contracts. Pure data models with validation.

---

### 2. Ports Layer (`src/case_core/ports/`)

**Purpose:** ABC interfaces for all external dependencies.

**Dependencies:** None (abstract only).

**Ports:**
| Port | Responsibility |
|------|----------------|
| `LLMProvider` | Complete a prompt, health check |
| `DomainPolicy` | Validate evidence, classify urgency, get context |
| `AuditPort` | Log events, query by case |
| `RepositoryPort` | Save/get/list cases |
| `DecisionRepositoryPort` | Save/get/list decisions, lifecycle updates |
| `AutomationPolicy` | Assess risk, get rules |

**Rule:** Core depends only on ports, never on concrete implementations.

---

### 3. Domain Layer (`src/case_core/domain/`)

**Purpose:** Domain-specific logic and registry.

**Components:**
- `DomainRegistry` — Maps domain names to policies
- `DomainPolicy` implementations — Per-domain validation and classification
- `AutomationPolicy` implementations — Per-domain risk assessment

**Registered Domains:**
| Domain | Policy | Automation |
|--------|--------|------------|
| `logistics` | LogisticsPolicy | LogisticsAutomationPolicy |
| `urban_operations` | UrbanPolicy | DefaultAutomationPolicy |
| `infrastructure` | InfrastructurePolicy | DefaultAutomationPolicy |

**Rule:** Domain logic cannot leak into core. Core is domain-agnostic.

---

### 4. Providers Layer (`src/case_core/providers/`)

**Purpose:** Concrete LLM provider implementations.

**Implementations:**
| Provider | Type | Use Case |
|----------|------|----------|
| `MockProvider` | Deterministic | Testing, demo, evaluation |
| `OllamaProvider` | Local LLM | Development, offline |
| `CloudProvider` | API-based | Production |

**Rule:** Provider-specific logic stays behind the LLMProvider port.

---

### 5. Reliability Layer (`src/case_core/reliability/`)

**Purpose:** Validation pipeline and automation assessment.

**Components:**
- `ReliabilityPipeline` — Multi-stage validation
- `AutomationEvaluator` — Risk-based automation decisions

**Pipeline Stages:**
1. JSON parsing
2. Schema validation (required fields, enums, confidence range)
3. Semantic validation (reason length, evidence quality)
4. Domain validation (policy-specific requirements)
5. Retry with backoff (transient + validation failures)
6. Terminal failure handling

**Rule:** Never trust raw LLM output. Always validate through pipeline.

---

### 6. Application Layer (`src/case_core/application/`)

**Purpose:** Orchestrate the full triage flow.

**Component:** `TriageEngine`

**Flow:**
1. Receive case
2. Resolve domain via DomainRegistry
3. Build prompt via PromptBuilder
4. Invoke LLM via provider port
5. Validate via ReliabilityPipeline
6. Assess automation via AutomationEvaluator
7. Construct decision
8. Persist via DecisionRepositoryPort
9. Log via AuditPort

**Rule:** No domain-specific logic in engine. No provider-specific logic.

---

### 7. API Layer (`src/case_api/`)

**Purpose:** HTTP interface.

**Endpoints:** 11 endpoints (health, domains, triage, audit, HITL lifecycle)

**Rule:** API delegates to TriageEngine. No business logic in API layer.

---

### 8. Persistence Layer (`src/case_infra/`)

**Purpose:** SQLite adapters for storage.

**Adapters:**
- `SQLiteRepository` — Case storage
- `SQLiteAuditAdapter` — Audit event storage
- `SQLiteDecisionRepository` — Decision storage with lifecycle

---

## Cross-Cutting Concerns

### HITL (Human-in-the-Loop)

- Decision lifecycle: AI_PROPOSED → UNDER_REVIEW → APPROVED/MODIFIED/REJECTED/ESCALATED
- 6 API endpoints for lifecycle management
- Transition validation (cannot approve from REJECTED)
- Full audit trail

### Security

- TIER3_DEVELOPER prompt constraints
- Schema validation blocks manipulation
- Effective urgency prevents downgrade
- 31 security tests, 10 attack scenarios

### Bias Evaluation

- Counterfactual pair analysis
- 10 bias pairs (logistics domain)
- Metrics: pair consistency, decision invariance, routing invariance

---

## Architectural Anti-Patterns

The following are NOT allowed:

1. **Domain logic in core** — No `if domain == "logistics"` in engine/pipeline
2. **Provider logic in ports** — No `import ollama` in ports layer
3. **Business logic in API** — No decision-making in FastAPI endpoints
4. **Raw LLM output trusted** — Always validate through pipeline
5. **Bypass of HITL** — Critical decisions must go through lifecycle
6. **`Any`/`dict` at boundaries** — Use typed models at critical interfaces
7. **Circular dependencies** — Layers depend downward only
8. **Infrastructure in domain** — No database calls in domain logic

---

## Isolated Modules

The following modules exist but are NOT connected to the running pipeline:

| Module | Location | Purpose |
|--------|----------|---------|
| Logistics Intelligence | domain/logistics_*.py | Shipment classification, routing |
| ML Adaptation | ml/*.py | Training abstractions |
| Specialist Models | ml/specialist_*.py | Keyword-based specialists |
| Hybrid Decision Engine | hybrid/decision_engine.py | Multi-source decisions |
| Real Estate Domain | domain/real_estate_policy.py | Domain policy |
| Governance | governance/__init__.py | Security, compliance |
| Production | production/__init__.py | Circuit breaker, rate limiter |

These are valid implementations that demonstrate extensibility. Wiring them requires explicit decision.
