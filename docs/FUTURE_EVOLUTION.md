# CASE — FUTURE EVOLUTION REGISTER

> This document is mandatory reading for any agent working on CASE before introducing new technology, training a model, migrating a database, adding a provider, connecting another project, creating a new domain pack, or introducing agentic capabilities.

---

## 1. Purpose

CASE v1.0 has a stable core. The following technologies and capabilities are part of the strategic roadmap but MUST NOT be implemented proactively. They MUST be introduced only when:

- Real problem exists
- Adequate data available
- Baseline established
- Metric defined
- Architectural justification documented
- Cost/benefit reasonable
- Value evidence demonstrated

---

## 2. External Project Integration

**Goal:** Allow CASE to consume capabilities/data from other portfolio projects without direct coupling.

**Mandatory pattern:**

```
External Project → Adapter → CASE Contract → Application → CASE Core → Validation → Risk → HITL / Automation → Audit
```

Before implementing any integration:

1. Portfolio Discovery
2. Identify dataset/capability
3. Verify license
4. Verify utility
5. Define adapter
6. Define CASE contract
7. Define metrics
8. Define failure/fallback
9. Document integration

---

## 3. Real Data Strategy

**Priority:**

1. Existing portfolio data
2. Public/open data
3. Synthetic controlled evaluation
4. Private/company data ONLY with authorization

**Never introduce to GitHub:** private data, PII, secrets, credentials, proprietary datasets without authorization.

Every data source must document: SOURCE, LICENSE, PROVENANCE, VERSION, TRANSFORMATIONS, LIMITATIONS.

---

## 4. Specialist Models

Specialist Models are a planned CASE evolution. DO NOT create a model per module. Create a model ONLY for a concrete task where evidence shows specialization adds value.

**Candidates:** shipment classification, risk classification, delay classification, anomaly detection, carrier suitability.

**Architecture:**

```
Specialist Model → Specialist Signal → CASE Validation → Risk → Decision → HITL / Automation → Audit
```

The Specialist Model has NO final authority.

Before training or integrating: TASK, DATASET, BASELINE, METRIC, ERROR PROFILE, EXPECTED BENEFIT, INTEGRATION COST, FAILURE MODE, FALLBACK.

If no justification exists: `SPECIALIST MODEL — NOT JUSTIFIED` (valid decision).

---

## 5. ML Adaptation / LoRA / QLoRA

LoRA/QLoRA is a future capability. MUST live OUTSIDE CASE Core.

**Architecture:**

```
Dataset → Baseline Model → Evaluation → Specialization Hypothesis → LoRA / QLoRA → Adapter → CASE → Validation / Risk / HITL
```

Do NOT implement LoRA without: real task, sufficient dataset, baseline, evaluation, reproducibility.

Compare: Base Model vs Adapted Model. Measure: quality, latency, token usage, cost, consistency, bias/invariance, structured output reliability.

---

## 6. Hybrid Decision Intelligence

**Future evolution:**

```
Input → Understanding → Specialist Model → LLM → Deterministic Rules → Evidence → Risk → Decision Engine → HITL / Automation → Audit
```

Do NOT assume all components must always execute. The goal is combining signals, not accumulating models.

The Decision Engine must resolve: conflicting signals, domain policy, risk, evidence, human overrides, explainability.

NEVER permit: LLM → direct final operational decision.

---

## 7. PostgreSQL

PostgreSQL is a possible future evolution. SQLite remains valid for: local development, tests, demos, lightweight deployments.

Evaluate PostgreSQL when real need exists for: concurrency, deployed persistent workload, relational querying, JSONB, durable production-oriented storage, geospatial capabilities.

Before migrating: create `docs/DATABASE_MIGRATION_PROPOSAL.md`. Compare SQLite vs PostgreSQL. Include problem, alternatives, cost, benefits, risks, migration strategy, rollback strategy.

Do NOT migrate for enterprise appearance. Maintain repository/adapter abstraction.

---

## 8. PostGIS

PostGIS is a future capability conditioned on real geospatial need (coordinates, zones, depots, routes, nearby incidents, infrastructure, geographic constraints).

Do NOT use an LLM to infer geographic data that can be obtained deterministically.

Do NOT install PostGIS without a use case.

---

## 9. Agentic / ReAct / LangGraph

ReAct, agentic workflows, and LangGraph remain OUTSIDE the core by default. Evaluate ONLY if real need appears for: multi-step evidence gathering, tool use, database lookup, external retrieval, iterative workflows, resumable stateful workflows.

LangGraph may be evaluated as orchestration infrastructure. Do NOT replace: CASE contracts, DomainRegistry, LLMProvider, Validation, Risk, Decision Engine, Audit.

LangChain MUST NOT be introduced as a central dependency.

---

## 10. Multimodal

Multimodal is future and depends on a real use case. The vision model has NO final authority. Evidence must be validated.

---

## 11. Additional Domain Packs

New domains (Finance, Real Estate, Urban, Infrastructure, others) ONLY when: they add value, respect DomainRegistry, do not contaminate core, have clear taxonomy, have tests, have evaluation strategy.

Do NOT create domains to complete a list.

---

## 12. Production / Scale

**Future evolution order:**

```
Stable Core → Public Deployment → CI/CD → Observability → Real Data → Meaningful Integration → Specialist ML → PostgreSQL where justified → Optional agentic / geo / multimodal
```

Do NOT introduce automatically: Kubernetes, Kafka, Redis, service mesh, distributed microservices. Infrastructure must follow need.

---

## 13. Decision Gate for Every Future Technology

Before introducing ANY new technology, answer:

1. WHAT REAL PROBLEM DOES THIS SOLVE?
2. WHY DOES CASE NEED IT?
3. WHY THIS TECHNOLOGY?
4. WHAT IS THE BASELINE?
5. WHAT WILL WE MEASURE?
6. WHAT NEW FAILURE MODES APPEAR?
7. WHAT IS THE MAINTENANCE COST?
8. DOES IT PRESERVE CASE ARCHITECTURE?
9. DOES IT INCREASE PROFESSIONAL SIGNAL?
10. CAN THE SAME RESULT BE ACHIEVED MORE SIMPLY?

If answers do not justify: `DEFERRED / NOT JUSTIFIED`.

---

## 14. Roadmap Order

**Strategic order:**

1. CURRENT → Phase 2 Evidence & Enterprise Foundation
2. NEXT → Public Deployment Verification
3. NEXT → Portfolio Discovery
4. NEXT → First Real Integration
5. NEXT → Real/Public Data Evaluation
6. THEN, only when justified → Specialist Model → ML Adaptation / LoRA → Hybrid Decision Intelligence → PostgreSQL → PostGIS → Agentic / LangGraph → Multimodal → Additional Domain Packs

Not all must be implemented.

---

## 15. Persistence Requirement

Every time one of these capabilities is evaluated, accepted, deferred, rejected, or implemented, update:

- `docs/ROADMAP.md`
- `docs/AGENT_CONTEXT.md`
- `docs/DEVELOPMENT_STATUS.md`
- `docs/DECISION_LOG.md` (when appropriate)

Register: DATE, CAPABILITY, DECISION, REASON, EVIDENCE, STATUS, NEXT REVIEW CONDITION.

---

## 16. Final Principle

CASE must NOT evolve via "technology first."

CASE must evolve via:

```
REAL PROBLEM → REAL DATA → BASELINE → EVIDENCE → ARCHITECTURAL DECISION → IMPLEMENTATION → MEASUREMENT
```

Never the other way around.

The goal is that each new technology is a consequence of demonstrated need. Do not build for fashion. Do not build to increase component count. Do not build to make CASE look more enterprise. Build only when it makes CASE more real, more useful, more measurable, or more reliable.
