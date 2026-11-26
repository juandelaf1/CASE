# CASE — Technical Case Study

## Problem
Using LLM outputs directly for operational decisions is risky: responses can be inconsistent, ambiguous, or wrong in ways that are hard to detect automatically. CASE addresses the need to turn unstructured case inputs into **structured, validated, auditable decisions** while keeping human oversight central.

## Decisions
- **Orchestration boundary:** treat the LLM as a proposal generator; CASE validates, evaluates risk/reliability, routes outcomes, and governs persistence/HITL actions.
- **Hexagonal architecture:** core logic depends on ports/contracts (Pydantic v2), with provider/domain implementations behind interfaces to preserve neutrality and testability.
- **Reliability pipeline:** multi-stage handling (parse/schema/semantic/domain checks, retries/repair paths) before accepting outputs.
- **Risk-based routing with HITL:** conservative outcomes (`AUTO_APPROVE`, `HUMAN_REVIEW`, `ESCALATE`) and full human lifecycle actions (approve/reject/modify/escalate).
- **Auditability by design:** decision events and lifecycle transitions recorded through audit/persistence ports/adapters.
- **Explicit scope separation:** distinguish connected runtime components from implemented-but-isolated modules to avoid overstating capabilities.

## Trade-offs
- **Safety/control vs autonomy:** prefers human review under uncertainty; not optimized for fully autonomous decisioning.
- **Determinism/testability vs real-world variability:** extensive deterministic/mock-based validation demonstrates architecture and behavior, but real-provider behavior requires separate/live validation.
- **Domain coverage depth:** some domains/policies are more complete than others; conservative defaults apply where domain-specific automation is limited.
- **Portfolio scope vs production hardening:** SQLite, limited auth/deployment claims, and known issues are documented; system is not presented as production-deployed.

## Evidence
- **Automated quality signals:** repository-documented test, lint, and type-check results (pytest/ruff/mypy snapshots) and extensive test suites across contracts, reliability, behavioral/security/bias/regression areas.
- **Runtime interfaces:** FastAPI endpoints, Streamlit UI, demo scripts, and HITL/audit flows for observable behavior.
- **Provider abstraction in practice:** mock and live-capable provider integrations (subject to environment/config) behind the same interface.
- **Documented architecture/state:** `ARCHITECTURE.md`, `DEVELOPMENT_STATUS.md`, `DECISION_LOG.md`, capability audit, and explicit limitations/isolated modules.

## Limits & learnings
- **Limits:** portfolio/research project (not production), evaluation and some validations rely heavily on synthetic/mock contexts, and domain automation/routing depth varies; isolated modules are not part of the connected execution path unless explicitly wired.
- **Learnings:** explicit contracts, validation pipelines, and conservative governance make AI-assisted workflows more inspectable and safer; clearly separating “connected” from “implemented but isolated” prevents capability inflation.
