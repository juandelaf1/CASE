# CASE Roadmap

> Strategic and technical roadmap. Last verified: 2026-09-14.
> Source of truth for planning, priorities, and phases.

---

## Vision

CASE is a domain-agnostic, provider-agnostic AI Decision Platform that transforms unstructured operational cases into structured, validated, evidence-backed decisions with human oversight.

**What CASE is:** An orchestration layer that takes an operational case, routes it through domain-specific validation, invokes an LLM for decision generation, validates the output, assesses automation risk, and produces an auditable decision.

**What CASE is NOT:** Not a fine-tuned model, not a RAG system, not an agent framework, not a real-time production system.

**Project type:** Portfolio-grade research/engineering project. Production-oriented architecture.

---

## Architectural Principles (Frozen Invariants)

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
| Foundation | v0.3 | FROZEN | Contracts, ports, domain system, pipeline, prompts are locked. |
| Blueprint | v1.1 | FROZEN | Architecture, domain packs, security, automation, bias are locked. |

---

## Current Architecture — Connected Pipeline

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

---

## Development Phases

### PHASE 1 — CASE v1 [COMPLETED & CONNECTED]

CASE v1 consolidates the Foundation, Providers/Evaluation/UI, Governance, and Final CASE v1 workstreams into one completed release. **This is the only fully connected, end-to-end working system.**

| Component | Status | Evidence |
|-----------|--------|----------|
| Contracts (Pydantic v2) | CONNECTED | 9 contract files |
| Ports (ABC interfaces) | CONNECTED | 6 ports |
| DomainRegistry | CONNECTED | 3 domains registered |
| ReliabilityPipeline | CONNECTED | Full validation chain |
| PromptBuilder | CONNECTED | TIER1_SYSTEM + TIER3_DEVELOPER security |
| TriageEngine | CONNECTED | Application layer orchestrator |
| Composition Root | CONNECTED | `composition.py` |
| MockProvider | CONNECTED | Default provider, 30 tests |
| OllamaProvider | CONNECTED | Local LLM, 13 tests + 5 integration |
| CloudProvider | CONNECTED | API-based, 28 tests |
| Evaluation Runner | CONNECTED | Single + dataset execution |
| Streamlit UI | CONNECTED | Decision Center, Status, HITL |
| HITL Lifecycle | CONNECTED | 6 API endpoints |
| Security Evaluation | CONNECTED | 31 tests, 10 attack scenarios |
| Risk-Based Automation | CONNECTED | AutomationEvaluator, risk matrix |
| Bias Evaluation | CONNECTED | 23 tests, routing_invariance fixed |
| Persistence | CONNECTED | SQLite adapters |
| Audit | CONNECTED | AuditPort + events |
| API | CONNECTED | Delegates to TriageEngine |

**Test results:** 393 tests passing (Phase 1 scope)

---

### PHASE 2 — Logistics Intelligence [IMPLEMENTED, ISOLATED]

**Objective:** Deepen logistics domain intelligence with shipment-level optimization, classification, and routing capabilities.

**Status:** Modules implemented and tested in isolation. NOT wired into TriageEngine pipeline.

| Component | Status | Evidence |
|-----------|--------|----------|
| Shipment classification | ISOLATED | logistics_classification.py |
| Route recommendation | ISOLATED | logistics_route_recommendation.py |
| Carrier matching | ISOLATED | logistics_carrier_matching.py |
| Joint recommendation | ISOLATED | logistics_joint_recommendation.py |
| Risk/Automation | ISOLATED | logistics_risk_automation.py |
| Evaluation | ISOLATED | logistics_evaluation.py |
| Contracts | ISOLATED | logistics_contracts.py |
| Understanding | ISOLATED | logistics_understanding.py |

**Tests:** 26 tests in test_ml_adaptation.py (isolated)

---

### PHASE 3 — ML Adaptation [IMPLEMENTED, ISOLATED]

**Objective:** Adapt CASE for domain-specific ML with fine-tuning and multi-domain learning.

**Status:** Abstract interfaces and mock implementations. NOT connected to any model or training pipeline.

| Component | Status | Evidence |
|-----------|--------|----------|
| Training abstraction | ISOLATED | ml/training_abstraction.py |
| Dataset contracts | ISOLATED | ml/dataset_contracts.py |
| Dataset pipeline | ISOLATED | ml/dataset_pipeline.py |
| LoRA/QLoRA config | ISOLATED | ml/lora_config.py |
| Adapters (mock) | ISOLATED | ml/adapters.py |
| Evaluation | ISOLATED | ml/evaluation.py |
| Evaluation dataset | ISOLATED | ml/evaluation_dataset.py |

**Tests:** 26 tests in test_ml_adaptation.py (isolated)

---

### PHASE 4 — Specialist Models [IMPLEMENTED, ISOLATED]

**Objective:** Build specialist models for specific domains.

**Status:** Keyword-based implementations. NOT integrated with LLM pipeline or decision engine.

| Component | Status | Evidence |
|-----------|--------|----------|
| Specialist interfaces | ISOLATED | ml/specialist_contracts.py |
| Classification specialist | ISOLATED | ml/specialist_models.py |
| Risk specialist | ISOLATED | ml/specialist_models.py |
| Routing specialist | ISOLATED | ml/specialist_models.py |
| Ensemble specialist | ISOLATED | ml/specialist_models.py |
| Registry | ISOLATED | ml/specialist_contracts.py |

**Tests:** 21 tests in test_specialist_models.py (isolated)

---

### PHASE 5 — Hybrid Decision Intelligence [IMPLEMENTED, ISOLATED]

**Objective:** Combine LLM + specialist models + rules + evidence + decision engine + HITL + audit.

**Status:** Standalone engine. NOT used by TriageEngine or wired into pipeline.

| Component | Status | Evidence |
|-----------|--------|----------|
| Decision Engine | ISOLATED | hybrid/decision_engine.py |
| Decision reconciliation | ISOLATED | Multi-source combination |
| HITL routing | ISOLATED | Automatic HITL triggers |
| Rules engine | ISOLATED | Priority-based rules |
| Evidence validation | ISOLATED | Sufficiency checking |
| Risk integration | ISOLATED | Risk assessment integration |
| Explanation | ISOLATED | Structured explanations |

**Tests:** 18 tests in test_hybrid_decision.py (isolated)

---

### PHASE 6 — Additional Domain Packs [IMPLEMENTED, ISOLATED]

**Objective:** Extend CASE to new domains.

**Status:** Real Estate domain implemented. NOT registered in DomainRegistry. Finance domain does NOT exist (despite previous claims).

| Component | Status | Evidence |
|-----------|--------|----------|
| Real Estate policy | ISOLATED | domain/real_estate_policy.py |
| Real Estate automation | ISOLATED | domain/real_estate_policy.py |
| Finance domain | NOT IMPLEMENTED | No finance_policy.py exists |

**Tests:** 28 tests in test_real_estate_domain.py (isolated)

---

### PHASE 7 — Advanced Governance/Security [IMPLEMENTED, ISOLATED]

**Objective:** Enhance governance, security, and compliance capabilities.

**Status:** Standalone modules. NOT connected to API, pipeline, or any other component.

| Component | Status | Evidence |
|-----------|--------|----------|
| Security Manager | ISOLATED | governance/__init__.py |
| Compliance Manager | ISOLATED | governance/__init__.py |
| Governance Framework | ISOLATED | governance/__init__.py |
| Access Control (RBAC) | ISOLATED | governance/__init__.py |
| Audit Trail | ISOLATED | governance/__init__.py |

**Tests:** 28 tests in test_governance.py (isolated)

---

### PHASE 8 — Production/Scale Readiness [IMPLEMENTED, ISOLATED]

**Objective:** Prepare CASE for production deployment.

**Status:** Standalone utilities. NOT connected to any deployment or monitoring infrastructure.

| Component | Status | Evidence |
|-----------|--------|----------|
| Circuit Breaker | ISOLATED | production/__init__.py |
| Rate Limiter | ISOLATED | production/__init__.py |
| Load Balancer | ISOLATED | production/__init__.py |
| Performance Monitor | ISOLATED | production/__init__.py |
| Health Checker | ISOLATED | production/__init__.py |
| Deployment Config | ISOLATED | production/__init__.py |

**Tests:** 28 tests in test_production.py (isolated)

---

## Phase Summary

| Phase | Name | Connected | Tests | Status |
|-------|------|-----------|-------|--------|
| Phase 1 | CASE v1 | YES | 393 | COMPLETED & CONNECTED |
| Phase 2 | Logistics Intelligence | NO | 26 | IMPLEMENTED, ISOLATED |
| Phase 3 | ML Adaptation | NO | 26 | IMPLEMENTED, ISOLATED |
| Phase 4 | Specialist Models | NO | 21 | IMPLEMENTED, ISOLATED |
| Phase 5 | Hybrid Decision Intelligence | NO | 18 | IMPLEMENTED, ISOLATED |
| Phase 6 | Additional Domain Packs | NO | 28 | IMPLEMENTED, ISOLATED |
| Phase 7 | Advanced Governance/Security | NO | 28 | IMPLEMENTED, ISOLATED |
| Phase 8 | Production/Scale Readiness | NO | 28 | IMPLEMENTED, ISOLATED |
| **Total** | | | **568** | |

**Note:** Total includes duplicate counting across isolated test suites. Actual unique tests: 526.

---

## Current Priority

**POST-V1.0 — Public Deployment & Integration Selection.** Deploy public demo, then systematically evaluate isolated capabilities for integration.

---

## Public Deployment Status

| Artifact | Status | URL |
|----------|--------|-----|
| GitHub Repository | PUBLIC | https://github.com/juandelaf1/CASE |
| Docker Hub Image | PUBLISHED | https://hub.docker.com/r/juandelaf/case |
| GitHub Release v1.0.0 | PUBLISHED | https://github.com/juandelaf1/CASE/releases/tag/v1.0.0 |
| Render Deployment | CONFIGURED | Requires manual Render account setup |

**Deployment Configuration:** `render.yaml` configured for Render free tier.
**Manual Steps Required:** Create Render account, connect repo, deploy service.

---

## POST-V1.0 — Integration Selection & Hardening

**Objective:** Convert progressively isolated capabilities into integrated capabilities when technical justification exists.

**Status:** Audit complete. See `docs/CAPABILITY_AUDIT.md` for full matrix.

### Integration Decisions

| Priority | Capability | Decision | Rationale |
|----------|-----------|----------|-----------|
| 1 | ShipmentUnderstanding | **INTEGRATE** | High value, low complexity, low risk |
| 2 | RealEstatePolicy | **INTEGRATE** | Low complexity, demonstrates domain-agnostic design |
| 3 | HybridDecisionEngine | **DEFER** | High value but high risk, needs architectural decision |
| 4-13 | All others | **KEEP ISOLATED** | Not critical for core pipeline |

### Milestones

| Milestone | Focus | Dependencies |
|-----------|-------|--------------|
| v1.0.1 | ShipmentUnderstanding integration | None |
| v1.0.2 | RealEstatePolicy registration | None |
| v1.1.0 | Architecture hardening | v1.0.1, v1.0.2 |
| v1.2.0 | Evaluation improvements | None |
| v2.0.0 | Hybrid Decision Engine integration | Architectural decision required |

### Rules

1. Each integration must preserve golden baseline (Phase 1)
2. Each integration must have tests before/after
3. Each integration must pass quality gates
4. No integration without documented justification (I10)
5. KEEP ISOLATED is a valid decision, not a failure

---

## Next Priority (Post-v1.0)

### Track A — Architecture Hardening
- [ ] Integrate ShipmentUnderstanding (v1.0.1)
- [ ] Register RealEstatePolicy (v1.0.2)
- [ ] Architecture review after integrations
- [ ] Update ARCHITECTURE.md

### Track B — Evaluation
- [ ] Expand bias pairs to Urban/Infrastructure
- [ ] Add real LLM testing (when available)
- [ ] Improve evaluation datasets

### Track C — Domain Expansion
- [ ] Urban/Infrastructure routing
- [ ] Urban/Infrastructure domain-specific automation
- [ ] New domain packs (with justification per I10)

### Track D — Production
- [ ] Authentication/authorization
- [ ] Rate limiting (real)
- [ ] Monitoring/observability
- [ ] Multi-tenant support

---

## Decision Rules

Before adding any of the following, there must be explicit technical justification (I10):

- Models
- Dependencies
- Infrastructure
- Frameworks
- Architectural changes

---

## Scope Boundaries

The following require explicit decision before implementation:

- Wiring isolated modules to pipeline
- New domain packs
- New infrastructure (Kubernetes, Docker, cloud deployment)
- New ML models or training pipelines
- Changes to frozen specs
