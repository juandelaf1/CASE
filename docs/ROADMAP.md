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

### PHASE 1 — CASE v1 (COMPLETED)

CASE v1 consolidates the Foundation, Providers/Evaluation/UI, Governance, and Final CASE v1 workstreams into one completed release.

| Component | Status | Evidence |
|-----------|--------|----------|
| Contracts (Pydantic v2) | COMPLETED | 9 contract files, 362+ tests passing |
| Ports (ABC interfaces) | COMPLETED | 6 ports: LLMProvider, DomainPolicy, AuditPort, RepositoryPort, DecisionRepositoryPort, AutomationPolicy |
| DomainRegistry | COMPLETED | 3 domains registered |
| ReliabilityPipeline | COMPLETED | Parse, schema, semantic, domain validation, retry, repair, terminal failure |
| PromptBuilder | COMPLETED | TIER1_SYSTEM + TIER3_DEVELOPER security constraints |
| TriageEngine | COMPLETED | Application layer orchestrator, 175 lines, 25 tests |
| Composition Root | COMPLETED | `composition.py` — AppDependencies, create_app_dependencies |
| MockProvider | COMPLETED | 30 tests, 10 pre-defined responses |
| OllamaProvider | COMPLETED | 13 tests + 5 integration (skipped without Ollama) |
| CloudProvider | COMPLETED | 28 tests (mock HTTP) |
| Evaluation Runner / Metrics / Reports | COMPLETED | Single + dataset execution, JSON report generation |
| Streamlit UI | COMPLETED | Decision Center, System Status, HITL display |
| Behavioral Evaluation | COMPLETED | 1351-line test suite, 42 tests |
| HITL Lifecycle | COMPLETED | 6 API endpoints, lifecycle states, audit trail |
| Security Evaluation | COMPLETED | 28 tests, 10 attack scenarios, defense-in-depth |
| Risk-Based Automation | COMPLETED | AutomationEvaluator, risk matrix, effective urgency, 12 tests |
| Bias Evaluation | COMPLETED | 8 standalone functions, 14 unit tests, routing_invariance_rate fixed |
| Phase 4 Evaluation | COMPLETED | 393 passed, all areas evaluated |
| Quality hardening | COMPLETED | pytest 393 passed, 7 skipped; ruff 0 errors; mypy 0 errors |

---

### PHASE 2 — Logistics Intelligence [ACTIVE]

**Objective:** Deepen logistics domain intelligence with shipment-level optimization, classification, and routing capabilities.

| Component | Status | Evidence |
|-----------|--------|----------|
| Shipment classification | NOT STARTED | New capability in Phase 2 |
| Route recommendation | NOT STARTED | New capability in Phase 2 |
| Carrier matching | NOT STARTED | New capability in Phase 2 |
| Scoring | NOT STARTED | New capability in Phase 2 |
| Optimization | NOT STARTED | New capability in Phase 2 |
| Operational constraints | NOT STARTED | New capability in Phase 2 |

#### Sub-sections
- **Shipment Classification:** Classify shipments by type, weight class, destination, and handling requirements using the LogisticsPolicy domain pack.
- **Route Recommendation:** Recommend optimal routes based on cost, time, carrier availability, and operational constraints.
- **Carrier Matching:** Match shipments to carriers based on capacity, reliability, cost, and service level agreements.
- **Scoring:** Score shipments, routes, and carriers using weighted metrics and domain-specific criteria.
- **Optimization:** Optimize route and carrier selection under constraints (capacity, time windows, cost limits).
- **Operational Constraints:** Encode real-world logistics constraints such as delivery windows, vehicle capacity, and regulatory requirements.

---

### PHASE 3 — ML Adaptation [FUTURE]

**Objective:** Adapt CASE for domain-specific ML with fine-tuning and multi-domain learning.

| Component | Status | Evidence |
|-----------|--------|----------|
| CASE dataset | NOT STARTED | New capability in Phase 3 |
| LoRA / QLoRA | NOT STARTED | New capability in Phase 3 |
| Fine-tuning | NOT STARTED | New capability in Phase 3 |
| Multi-domain adaptation | NOT STARTED | New capability in Phase 3 |

#### Sub-sections
- **CASE dataset:** Curate and label a dataset of operational cases for training and evaluation.
- **LoRA / QLoRA:** Apply low-rank adaptation techniques for efficient fine-tuning of foundation models.
- **Fine-tuning:** Fine-tune models on CASE-specific data to improve domain accuracy.
- **Multi-domain adaptation:** Adapt models to multiple domains with shared representations and domain-specific layers.

---

### PHASE 4 — Specialist Models [FUTURE]

**Objective:** Build specialist models for specific domains and integrate them with the LLM pipeline.

| Component | Status | Evidence |
|-----------|--------|----------|
| Small encoder / BERT-style models | NOT STARTED | New capability in Phase 4 |
| Domain-specific classifiers | NOT STARTED | New capability in Phase 4 |
| Hybrid decision architecture | NOT STARTED | New capability in Phase 4 |

#### Sub-sections
- **Small encoder / BERT-style models:** Deploy lightweight encoders for classification and semantic tasks.
- **Domain-specific classifiers:** Train classifiers for specific domains (e.g., logistics, finance, real estate).
- **Hybrid decision architecture:** Combine LLM output with specialist model predictions for improved accuracy.

---

### PHASE 5 — Hybrid Decision Intelligence [FUTURE]

**Objective:** Combine LLM + specialist models + rules + evidence + decision engine + HITL + audit into a full hybrid decision pipeline.

```
LLM + Specialist Models + Rules + Evidence + Decision Engine + HITL + Audit
```

#### Sub-sections
- **LLM:** Generate initial decision proposals from unstructured cases.
- **Specialist Models:** Provide domain-specific predictions and classifications.
- **Rules:** Apply deterministic business rules and constraints.
- **Evidence:** Validate decisions against evidence and domain policies.
- **Decision Engine:** Reconcile LLM, specialist model, and rule outputs into a final decision.
- **HITL:** Human-in-the-loop review for high-risk or uncertain decisions.
- **Audit:** Maintain a full audit trail of all decision steps and inputs.

Status: NOT STARTED. Conceptual only.

---

### PHASE 6 — Additional Domain Packs [FUTURE]

**Objective:** Extend CASE to new domains beyond the current Urban, Logistics, and Infrastructure coverage.

#### Sub-sections
- **Finance Domain Pack:** Domain policies, evidence validation, urgency classification, and automation for financial cases.
- **Real Estate Domain Pack:** Domain policies, evidence validation, urgency classification, and automation for real estate cases.
- **New Domain Packs:** Additional domain packs (e.g., Healthcare, Legal, Insurance) as new opportunities arise.

#### Sub-sections
- **Domain Policy:** Validate evidence and classify urgency for the new domain.
- **Routing:** Classify incident types and route cases to the correct workflow.
- **Automation:** Apply domain-specific automation policies with risk-based decisions.
- **Recommended Actions:** Provide domain-specific recommended actions per incident type.
- **Bias Pairs:** Define and test bias pairs for each new domain to ensure invariance.

---

### PHASE 7 — Advanced Governance/Security [FUTURE]

**Objective:** Enhance governance, security, and compliance capabilities for production-grade CASE deployments.

#### Sub-sections
- **Adaptive Security:** Implement adaptive security measures including adversarial training and dynamic defenses.
- **Governance Framework:** Establish formal governance processes for model updates, policy changes, and audit reviews.
- **Compliance Controls:** Add compliance controls for regulatory requirements (e.g., GDPR, SOC 2, ISO 27001).
- **Access Control:** Implement granular access control and authorization for sensitive decision data.
- **Monitoring & Alerting:** Add monitoring, alerting, and anomaly detection for production environments.

---

### PHASE 8 — Production/Scale Readiness [FUTURE]

**Objective:** Prepare CASE for production deployment at scale with reliability, performance, and operational excellence.

#### Sub-sections
- **Production Deployment:** Deploy CASE to production infrastructure with proper configuration and monitoring.
- **Scale Readiness:** Ensure the system can handle production-scale traffic and data volumes.
- **Performance Optimization:** Optimize latency, throughput, and resource utilization for production workloads.
- **Reliability Engineering:** Implement reliability practices including SLOs, error budgets, and incident response.
- **Operational Excellence:** Establish operational processes for maintenance, updates, and continuous improvement.

Status: NOT STARTED. Conceptual only.

---

## Sprint Structure

### Sprint 1 — CASE Decision Platform [COMPLETED]

**Objective:** Build the core decision platform with domain-agnostic architecture.

**Deliverables:** Contracts, ports, 3 domain packs, 3 providers, pipeline, prompts, API, Streamlit UI, persistence, 362+ tests.

### Sprint 2 — Logistics Intelligence [ACTIVE]

**Objective:** Add logistics-specific intelligence capabilities including shipment classification, route recommendation, carrier matching, scoring, and optimization.

**Deliverables:** Shipment classification, route recommendation, carrier matching, scoring, optimization, operational constraints.

### Sprint 3 — ML Adaptation [FUTURE]

**Objective:** Adapt CASE for domain-specific ML with fine-tuning and multi-domain learning.

**Deliverables:** CASE dataset, LoRA fine-tuning, multi-domain adaptation.

### Sprint 4 — Specialist Models [FUTURE]

**Objective:** Build specialist models for specific domains.

**Deliverables:** BERT-style classifiers, hybrid architecture.

### Sprint 5 — Hybrid Decision Intelligence [FUTURE]

**Objective:** Combine LLM + specialist models + rules + evidence + decision engine + HITL + audit.

**Deliverables:** Full hybrid decision pipeline.

### Sprint 6 — Additional Domain Packs [FUTURE]

**Objective:** Extend CASE to new domains beyond the current Urban, Logistics, and Infrastructure coverage.

**Deliverables:** Finance Domain Pack, Real Estate Domain Pack, new domain packs.

### Sprint 7 — Advanced Governance/Security [FUTURE]

**Objective:** Enhance governance, security, and compliance capabilities.

**Deliverables:** Adaptive security, governance framework, compliance controls, access control, monitoring.

### Sprint 8 — Production/Scale Readiness [FUTURE]

**Objective:** Prepare CASE for production deployment at scale.

**Deliverables:** Production deployment, scale readiness, performance optimization, reliability engineering, operational excellence.

---

## Current Progress Matrix

| Capability | Status | Evidence | Remaining |
|------------|--------|----------|-----------|
| Core Contracts | COMPLETED | 9 files, 393+ tests | — |
| Ports | COMPLETED | 6 interfaces | — |
| Domain Registry | COMPLETED | 3 domains | — |
| Reliability Pipeline | COMPLETED | Full validation chain | — |
| TriageEngine | COMPLETED | 175 lines, 25 tests | — |
| MockProvider | COMPLETED | 17 tests | — |
| OllamaProvider | COMPLETED | 13 tests + 5 integration | — |
| CloudProvider | COMPLETED | 24 tests | — |
| Evaluation Framework | COMPLETED | Runner, metrics, reports | — |
| Streamlit UI | COMPLETED | Decision Center + Status + HITL | — |
| HITL Lifecycle | COMPLETED | 6 endpoints, audit trail | — |
| Logistics Domain Pack | COMPLETED | Policy + routing + automation | — |
| Security Evaluation | COMPLETED | 31 tests, 10 scenarios | — |
| Risk-Based Automation | COMPLETED | 12 tests + 3 security | — |
| Bias Evaluation | COMPLETED | 23 tests, routing_invariance fixed | Bias pairs logistics-only (FUTURE) |
| Urban Policy | PARTIAL | Policy + validation + DefaultAutomationPolicy | No routing (FUTURE) |
| Infrastructure Policy | PARTIAL | Policy + validation + DefaultAutomationPolicy | No routing (FUTURE) |
| API | COMPLETED | Delegates to TriageEngine | — |
| Composition Root | COMPLETED | `composition.py` extracts wiring | — |
| Persistence | COMPLETED | SQLite adapters | — |
| Audit | COMPLETED | AuditPort + events | — |
| Phase 1 Evaluation | COMPLETED | 393 passed, all areas evaluated | — |

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

**Phase 2 — Logistics Intelligence.** Current objective is deepening logistics domain intelligence with shipment classification, route recommendation, carrier matching, scoring, optimization, and operational constraints.

## Next Priority

**Phase 3 — ML Adaptation.** After Phase 2 Logistics Intelligence is complete, the next priority is ML Adaptation for domain-specific fine-tuning.

## Deferred

- Urban/Infrastructure Automation (FUTURE)
- Urban/Infrastructure Routing (FUTURE)
- Bias pairs for Urban and Infrastructure (FUTURE)
- Quality hardening
- Documentation consolidation

---

## Autonomous Execution Protocol

### Phase Numbering

| Phase | Name | Status |
|-------|------|--------|
| Phase 1 | CASE v1 | COMPLETED |
| Phase 2 | Logistics Intelligence | ACTIVE |
| Phase 3 | ML Adaptation | FUTURE |
| Phase 4 | Specialist Models | FUTURE |
| Phase 5 | Hybrid Decision Intelligence | FUTURE |
| Phase 6 | Additional Domain Packs | FUTURE |
| Phase 7 | Advanced Governance/Security | FUTURE |
| Phase 8 | Production/Scale Readiness | FUTURE |

### Quality Gates

Before advancing to the next phase, all quality gates must pass:
- `pytest` 0 failures
- `ruff` 0 errors
- `mypy` 0 errors
- Integration tests all pass
- No regressions in existing capabilities

### Exit Criteria

Each phase must meet its exit criteria before the next phase begins:
- **Phase 2 exit:** All logistics intelligence components implemented, tested, and evaluated
- **Phase 3 exit:** ML adaptation pipeline operational with fine-tuned models
- **Phase 4 exit:** Specialist models deployed and integrated with the LLM pipeline
- **Phase 5 exit:** Full hybrid decision pipeline operational end-to-end
- **Phase 6 exit:** New domain packs implemented with bias evaluation coverage
- **Phase 7 exit:** Governance and security capabilities production-ready
- **Phase 8 exit:** Production deployment successful with scale validation

### Change-Control Rules

Before adding any of the following, there must be explicit technical justification:
- Models
- Dependencies
- Infrastructure
- Frameworks
- Architectural changes

This maps to I10 (complexity requires justification).

### Scope Boundaries

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
