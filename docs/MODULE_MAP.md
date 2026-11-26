# CASE Module Map

> Canonical module boundaries and scaling rules for CASE.  
> Last updated: 2026-11-13 (audit-based draft, grounded in repository inspection).

## Purpose

Define how CASE is structured and extended as a **modular platform**, so it can be completed without coupling the core to any single domain, provider, consumer, or demo flow.

## Core principle

**CASE is provider-agnostic and domain-agnostic at the core.**

- The core engine must work for **any scenario** that can be expressed through CASE contracts and domain packs.
- The current delivery/demo is assembled around a **logistics** use case. Logistics is the **first reference vertical slice**, not the platform boundary.
- UI/demo flows may default to logistics, but core contracts, engine, reliability, persistence, and provider ports must not depend on logistics-specific assumptions.

## Acceptance rule for any new scenario

A new scenario/domain should be addable by:

1. Defining/using CASE contracts.
2. Registering a domain policy and automation policy.
3. Providing domain validation/context/routing as needed.
4. Adding tests and evaluation fixtures.
5. Wiring through composition/configuration.

A new scenario should **not** require changes to core orchestration logic, provider ports, or base decision contracts unless there is an explicit, documented platform-level decision.

## Current state (observed)

| Area | Current state | Notes |
|---|---|---|
| Core | Connected | `case_core/application`, `contracts`, `ports`, `reliability`, `prompts`, `react` |
| Domains | Connected | 5 registered in `composition.py`: `urban_operations`, `logistics`, `infrastructure`, `seismic_risk`, `real_estate` |
| Providers | Connected | Mock/Groq/Ollama/Cloud behind `LLMProvider`, circuit breaker wrapping |
| Persistence | Connected | SQLite decision/audit/idempotency/migrations |
| API | Connected, monolithic | `case_api/api/v1/app.py` contains multiple capabilities; needs router modularization |
| Poolar boundary | Connected, draft | `/api/v1/evaluate` implements `case-eval/v0.1-draft` boundary adapter |
| External adapters | Present | `usgs_adapter`, `logistics_adapter` as top-level src packages |
| Logistics parallel package | Retired | `case_logistics/` removed (issue #9). Canonical: `case_core/domain/logistics_*`; adapter: `logistics_adapter/`. |
| Experimental/isolated | Isolated | ML adaptation, specialist models, hybrid decision engine, governance/prod utilities, logistics intelligence pieces |

## Target module map

| Module | Responsibility | Should contain | Must not contain | Integration rule |
|---|---|---|---|---|
| `case_core` | Platform decision engine | Contracts, ports, engine, reliability, prompt building, lifecycle, errors, audit semantics | HTTP, concrete DB, provider SDKs, domain-specific branching, external adapter logic | Stable, domain/provider agnostic |
| `case_domains/<domain>` | Domain packs | DomainPolicy, AutomationPolicy, evidence validation, urgency/context, domain routing/helpers, domain tests | Core orchestration changes, provider logic, consumer-specific execution | Registered via composition/registry |
| `case_providers/<provider>` | LLM/provider adapters | Provider implementations, health/capability/cost mapping, provider config | Domain rules, API routes, persistence business logic | Implements `LLMProvider` only |
| `case_infra/<backend>` | Persistence/audit/idempotency | Repository/audit adapters, migrations, storage-specific concerns | Decision logic, domain rules, HTTP | Implements persistence ports |
| `case_api` | Transport layer | FastAPI routers, auth/rate-limit middleware, request/response schemas, error mapping | Decision business logic, domain logic, direct external side effects beyond adapter calls | Delegates to engine/services |
| `case_adapters/<name>` | External data/capability adapters | Normalization, client wrappers, provenance, timeout/fallback mapping | CASE core ownership, HITL authority, hidden side effects | Input/output contract; no core coupling |
| `case_integrations/<consumer>` | Consumer boundary adapters | Versioned contracts (e.g. `case.evaluate`, see `docs/CASE_EVALUATE_CONTRACT.md`), mapping, idempotency/correlation/authz integration | Consumer domain orchestration inside CASE core | Versioned, additive, auditable |
| `case_evaluation` | Reproducible evaluation | Deterministic/security/bias/regression suites, datasets, reports, metrics | Fabricated claims, production claims without evidence | Evidence-linked reports only |
| `case_experimental` | R&D modules | ML adaptation, hybrid/specialist models, advanced logistics intelligence, etc. | Implicit pipeline wiring, undocumented behavior | Explicit gate before integration |

## Boundary rules

### Core boundaries

- No `if domain == ...` in core engine/reliability.
- No provider-specific imports in core.
- No consumer-specific logic in core (Poolar is a consumer integration, not core).
- Raw LLM output is never trusted.
- Public contracts change only with explicit versioning/decision.

### Domain boundaries

- Logistics is a reference vertical, not a special core case.
- Domain-specific evidence rules, routing, labels, and demo cases belong in domain/demo layers.
- A domain pack may be rich, but it must plug in through ports/registry.

### Integration boundaries

- Adapters normalize external data; they do not own CASE decisions.
- Consumer integrations (Poolar, others) consume CASE contracts; CASE does not absorb consumer workflows.
- Sensitive execution authority remains in the owning system context; CASE provides governed decision/evaluation/HITL outputs.

### Experimental boundaries

- Isolated modules stay isolated until they pass an integration gate.
- Integration gate: real problem, contract, tests, evidence, no invariant break, rollback path, documented decision.

## Known modularity issues to resolve

| Issue | Why it matters | Direction |
|---|---|---|
| `app.py` is monolithic | Hard to evolve capabilities independently | Resolved: split into `case_api/api/v1/routers/*` (PR #12). |
| `evaluate` contract embedded in app.py | Poolar/consumer boundary should be versioned and isolated | Resolved: router extracted; contract documented in `docs/CASE_EVALUATE_CONTRACT.md` (issue #8). |
| Logistics duplication (`case_core/domain/logistics_*`, `case_logistics/`, `logistics_adapter/`) | Resolved | `case_core/domain/logistics_*` = canonical domain pack; `logistics_adapter/` = data ingestion/normalization; legacy `case_logistics/` retired (issue #9). |
| Doc/state drift (AGENT_CONTEXT/README/ARCHITECTURE) | Creates wrong operational decisions | Make one canonical status source and update links |
| Experimental modules not classified | Can create accidental coupling or dead weight | Maintain explicit integrate/keep-isolated/extract/retire decisions |

## Immediate documentation/actions

1. Keep this file as the canonical module-boundary map.
2. Add/maintain `DEVELOPMENT_STATUS` or refresh AGENT_CONTEXT with verified state.
3. Create ADRs for: logistics boundary, evaluate contract ownership, experimental module gate.
4. Use this map during Phase 1-2 execution (modularization and API/contracts split).

## Related docs

- [AGENT_CONTEXT.md](AGENT_CONTEXT.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md)
- [V3_ECOSYSTEM_PLAN.md](V3_ECOSYSTEM_PLAN.md)
- [INTEGRATION_CANDIDATES.md](INTEGRATION_CANDIDATES.md)
- [DOMAIN_PACK_GUIDE.md](DOMAIN_PACK_GUIDE.md)
- [CASE_EVALUATE_CONTRACT.md](CASE_EVALUATE_CONTRACT.md)
- [CONSUMER_INTEGRATION_GUIDE.md](CONSUMER_INTEGRATION_GUIDE.md)
