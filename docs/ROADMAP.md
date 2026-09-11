# CASE Roadmap

> Strategic and technical roadmap. Updated 2026-09-11.
> Source of truth for planning, priorities, and phases.

---

## Vision

CASE is a domain-agnostic, provider-agnostic AI Decision Platform that transforms unstructured operational cases into structured, validated, evidence-backed decisions with human oversight.

**What CASE is:** An orchestration layer that takes an operational case, routes it through domain-specific validation, invokes an LLM for decision generation, validates the output, assesses automation risk, and produces a auditable decision.

**What CASE is NOT:** Not a fine-tuned model, not a RAG system, not an agent framework, not a real-time production system.

---

## Architectural Principles

Verified invariants from Foundation v0.3 and Blueprint v1.1:

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

## Frozen Specifications

| Spec | Version | Status | Meaning |
|------|---------|--------|---------|
| Foundation | v0.3 | FROZEN | Contracts, ports, domain system, pipeline, prompts are locked. Changes require explicit review. |
| Blueprint | v1.1 | FROZEN | Architecture, domain packs, security, automation, bias are locked. Changes require explicit review. |

**What FROZEN means:** The specification documents are the source of truth. Code may be added to implement the spec, but the spec itself does not change without explicit decision. Bugs in code can be fixed; the spec is not "buggy" — it is the reference.

---

## Current Architecture

```
Streamlit (display only)
   ↓
FastAPI (HTTP adapter, composition root)
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

---

## Development Phases

### PHASE 0 — Foundation / Core [COMPLETED]

| Component | Status | Evidence |
|-----------|--------|----------|
| Contracts (Pydantic v2) | COMPLETED | 9 contract files, 362+ tests passing |
| Ports (ABC interfaces) | COMPLETED | 6 ports: LLMProvider, DomainPolicy, AuditPort, RepositoryPort, DecisionRepositoryPort, AutomationPolicy |
| DomainRegistry | COMPLETED | 3 domains registered |
| ReliabilityPipeline | COMPLETED | Parse, schema, semantic, domain validation, retry, repair, terminal failure |
| PromptBuilder | COMPLETED | TIER1_SYSTEM + TIER3_DEVELOPER security constraints |
| TriageEngine | COMPLETED (uncommitted) | Application layer orchestrator, 175 lines, 15 tests |

### PHASE 1 — Providers / Evaluation / UI [COMPLETED]

| Component | Status | Evidence |
|-----------|--------|----------|
| MockProvider | COMPLETED | 30 tests, 10 pre-defined responses |
| OllamaProvider | COMPLETED | 13 tests + 5 integration (skipped without Ollama) |
| CloudProvider | COMPLETED | 28 tests (mock HTTP) |
| Evaluation Runner | COMPLETED | Single + dataset execution |
| Evaluation Metrics | COMPLETED | Decision accuracy, urgency accuracy, confidence, timing, error rate |
| Evaluation Reports | COMPLETED | JSON report generation |
| Streamlit UI | COMPLETED | Decision Center, System Status, HITL display |

### PHASE 2 — Governance / Decision Control [COMPLETED]

| Component | Status | Evidence |
|-----------|--------|----------|
| Behavioral Evaluation | COMPLETED | 1351-line test suite, 42 tests |
| HITL Lifecycle | COMPLETED | 6 API endpoints, lifecycle states, audit trail |
| Logistics Domain Pack | COMPLETED | Policy, routing (6 incident types), automation, recommended actions |
| Security Evaluation | COMPLETED | 28 tests, 10 attack scenarios, defense-in-depth |
| Risk-Based Automation | COMPLETED | AutomationEvaluator, risk matrix, effective urgency, 12 tests |
| Bias Evaluation | PARTIALLY COMPLETED | 8 standalone functions, 10 pairs (logistics only), routing_invariance_rate bug present |

### PHASE 3 — Final CASE v1 [FUTURE]

| Component | Status |
|-----------|--------|
| Final evaluation (multi-model) | DEFERRED |
| Quality hardening | DEFERRED |
| Documentation consolidation | IN PROGRESS (this document) |
| Demo preparation | DEFERRED |
| Portfolio readiness | DEFERRED |

### PHASE 4 — Logistics Intelligence [FUTURE]

| Component | Status |
|-----------|--------|
| Shipment classification | NOT STARTED |
| Route recommendation | NOT STARTED |
| Carrier matching | NOT STARTED |
| Scoring | NOT STARTED |
| Optimization | NOT STARTED |
| Operational constraints | NOT STARTED |

### PHASE 5 — ML Adaptation [FUTURE]

| Component | Status |
|-----------|--------|
| CASE dataset | NOT STARTED |
| LoRA / QLoRA | NOT STARTED |
| Fine-tuning | NOT STARTED |
| Multi-domain adaptation | NOT STARTED |

### PHASE 6 — Specialist Models [FUTURE]

| Component | Status |
|-----------|--------|
| Small encoder / BERT-style models | NOT STARTED |
| Domain-specific classifiers | NOT STARTED |
| Hybrid decision architecture | NOT STARTED |

### PHASE 7 — Hybrid Decision Intelligence [FUTURE]

```
LLM + Specialist Models + Rules + Evidence + Decision Engine + HITL + Audit
```

NOT STARTED. Conceptual only.

---

## Sprint Structure

### Sprint 1 — CASE Decision Platform [COMPLETED]

**Objective:** Build the core decision platform with domain-agnostic architecture.

**Deliverables:** Contracts, ports, 3 domain packs, 3 providers, pipeline, prompts, API, Streamlit UI, persistence, 362+ tests.

### Sprint 2 — Logistics Intelligence [FUTURE]

**Objective:** Add logistics-specific intelligence capabilities.

**Deliverables:** Shipment classification, route recommendation, carrier matching. BLOCKED on Sprint 1 completion and portfolio decision.

### Sprint 3 — ML Adaptation [FUTURE]

**Objective:** Adapt CASE for domain-specific ML.

**Deliverables:** CASE dataset, LoRA fine-tuning, multi-domain adaptation.

### Sprint 4 — Specialist Models [FUTURE]

**Objective:** Build specialist models for specific domains.

**Deliverables:** BERT-style classifiers, hybrid architecture.

### Sprint 5 — Hybrid Decision Intelligence [FUTURE]

**Objective:** Combine LLM + specialist models + rules.

**Deliverables:** Full hybrid decision pipeline.

---

## Current Progress Matrix

| Capability | Status | Evidence | Remaining |
|------------|--------|----------|-----------|
| Core Contracts | COMPLETED | 9 files, 362+ tests | — |
| Ports | COMPLETED | 6 interfaces | — |
| Domain Registry | COMPLETED | 3 domains | — |
| Reliability Pipeline | COMPLETED | Full validation chain | — |
| TriageEngine | COMPLETED (uncommitted) | 175 lines, 15 tests | Commit pending |
| MockProvider | COMPLETED | 30 tests | — |
| OllamaProvider | COMPLETED | 13 tests + 5 integration | — |
| CloudProvider | COMPLETED | 28 tests | — |
| Evaluation Framework | COMPLETED | Runner, metrics, reports | — |
| Streamlit UI | COMPLETED | Decision Center + Status + HITL | — |
| HITL Lifecycle | COMPLETED | 6 endpoints, audit trail | — |
| Logistics Domain Pack | COMPLETED | Policy + routing + automation | — |
| Security Evaluation | COMPLETED | 28 tests, 10 scenarios | — |
| Risk-Based Automation | COMPLETED | 12 tests + 3 security | — |
| Bias Evaluation | PARTIAL | 8 functions, 10 pairs | routing_invariance_rate bug, logistics-only |
| Urban Policy | PARTIAL | Policy + validation only | No routing, no automation |
| Infrastructure Policy | PARTIAL | Policy + validation only | No routing, no automation |
| API | COMPLETED | Delegates to TriageEngine | Composition wiring in app.py |
| Persistence | COMPLETED | SQLite adapters | — |
| Audit | COMPLETED | AuditPort + events | — |
| Documentation | IN PROGRESS | This document | ROADMAP, AGENT_CONTEXT, DEV_STATUS |

---

## Decision Rules

Before adding any of the following, there must be explicit technical justification:

- Models
- Dependencies
- Infrastructure
- Frameworks
- Architectural changes

This maps to I10 (complexity requires justification).

---

## Scope Boundaries

The following must NOT be implemented within the current milestone without a new explicit decision:

- BERT / encoder models
- Fine-tuning / LoRA
- RAG (retrieval-augmented generation)
- Agent frameworks
- Ensembles
- New Domain Packs (Finance, Real Estate, etc.)
- New infrastructure (Kubernetes, Docker, cloud deployment)
- Speculative ML optimization
- Unjustified benchmarks

---

## Future Ideas

Marked explicitly as FUTURE. Not planned for immediate implementation:

- Finance Domain Pack
- Real Estate Domain Pack
- Logistics Intelligence (Sprint 2)
- LoRA / QLoRA fine-tuning
- BERT specialist models
- Hybrid decision architecture
- Multi-model ensembles
- Real-time production deployment
- Adaptive security (adversarial training)

---

## Current Priority

**Commit the TriageEngine implementation.** 4 files modified/created, all tests passing, working tree dirty.

## Next Priority

**Composition root extraction.** Move wiring (domain registration, provider creation, persistence creation) out of app.py into a dedicated startup module.

## Deferred

- Urban/Infrastructure Automation
- Urban/Infrastructure Routing
- Fix routing_invariance_rate bug in bias evaluation
- Bias pairs for Urban and Infrastructure domains
- Final evaluation
- Quality hardening
- Documentation consolidation
