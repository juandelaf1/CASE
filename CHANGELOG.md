# Changelog

All notable changes to CASE are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-09-14

### Release Preparation

#### Repository Cleanup
- Removed root-level benchmark/test scripts (benchmark_candidates.py, benchmark_qwen4b.py, benchmark_run.py, diagnose_qwen4b.py, smoke_candidates.py, test_deepseek.py, test_qwen4b.py)
- Updated .gitignore to prevent benchmark artifacts

#### Documentation
- Created ARCHITECTURE.md — Technical architecture documentation
- Created DECISION_LOG.md — Record of significant decisions
- Created RELEASES.md — Release history and milestones
- Created LICENSE — MIT license
- Rewrote AGENT_CONTEXT.md — Honest state with verified data
- Rewrote DEVELOPMENT_STATUS.md — Accurate implementation status
- Rewrote ROADMAP.md — Honest assessment of connected vs isolated modules
- Updated CHANGELOG.md — Complete history

#### Quality
- 526 tests passing, 7 skipped, 0 failures
- 0 ruff errors
- 0 mypy errors (82 source files)

---

## [0.2.0] — 2026-09-14

### Implemented Isolated Modules (Not Wired to Pipeline)

#### Phase 2 — Logistics Intelligence
- Shipment classification, route recommendation, carrier matching
- Joint recommendation, risk/automation, evaluation
- 8 standalone modules, 26 tests

#### Phase 3 — ML Adaptation
- Training abstractions, dataset pipeline, LoRA config
- Mock adapters, evaluation framework
- 7 standalone modules, 26 tests

#### Phase 4 — Specialist Models
- Keyword-based classification, risk, routing specialists
- Ensemble specialist, registry
- 2 standalone modules, 21 tests

#### Phase 5 — Hybrid Decision Intelligence
- Multi-source decision combination
- Rules engine, evidence validation, HITL routing
- 1 standalone module, 18 tests

#### Phase 6 — Additional Domain Packs
- Real Estate domain policy and automation
- 1 standalone module, 28 tests

#### Phase 7 — Advanced Governance/Security
- Security manager, compliance manager
- Governance framework, RBAC
- 1 standalone module, 28 tests

#### Phase 8 — Production/Scale Readiness
- Circuit breaker, rate limiter, load balancer
- Performance monitor, health checker
- 1 standalone module, 28 tests

**Note:** All Phase 2-8 modules are tested in isolation but NOT wired into the TriageEngine pipeline.

---

## [0.1.0] — 2026-09-11

### Initial Release — CASE Decision Platform

#### Core Architecture
- **Contracts:** 9 Pydantic v2 schema files
- **Ports:** 6 ABC interfaces
- **Domain Registry:** 3 domains registered
- **Reliability Pipeline:** Full validation chain
- **Prompt Builder:** Security constraints
- **TriageEngine:** Application orchestrator
- **Composition Root:** Dependency wiring

#### Providers
- **MockProvider:** 30 tests
- **OllamaProvider:** 13 tests + 5 integration
- **CloudProvider:** 28 tests

#### Domain Packs
- **Logistics:** Full pack with routing, automation
- **Urban Operations:** Policy, urgency, default automation
- **Infrastructure:** Policy, urgency, default automation

#### Reliability & Validation
- JSON parsing, schema validation, semantic validation
- Domain validation, retry with backoff
- Terminal failure handling

#### Risk-Based Automation
- AutomationEvaluator with risk matrix
- Effective urgency prevents downgrade
- Three outcomes: AUTO_APPROVE, HUMAN_REVIEW, ESCALATE

#### HITL
- 6 API endpoints
- Decision lifecycle management
- Transition validation
- Full audit trail

#### Security
- Prompt injection defense
- Schema validation
- 31 security tests, 10 attack scenarios

#### Bias Evaluation
- 10 counterfactual pairs
- Metrics: pair consistency, decision/routing invariance
- routing_invariance_rate bug fixed

#### Evaluation Framework
- Runner, metrics, reports
- Dataset loader, scenarios

#### API
- FastAPI with 11 endpoints
- Delegates to TriageEngine

#### Persistence
- SQLite adapters for cases, audit, decisions

#### UI
- Streamlit: Decision Center, Status, HITL display

#### Testing
- 393 tests passing, 7 skipped, 0 failures
- Quality: ruff 0 errors, mypy 0 errors

---

## Milestones

| Version | Commit | Description |
|---------|--------|-------------|
| v0.1.0 | `02f193e` | Initial release |
| v0.2.0 | `ecd85b9` | Isolated modules implemented |
| v1.0.0 | pending | Release preparation |
