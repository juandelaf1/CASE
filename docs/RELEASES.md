# CASE Releases

> Release history and milestones. Last updated: 2026-09-14.

---

## v1.0.0 — [PENDING]

**Target:** Public release milestone.

**Date:** 2026-09-14

### What's Included

**Connected System (End-to-End Working):**
- Core contracts (9 Pydantic v2 schemas)
- Ports (6 ABC interfaces)
- DomainRegistry (3 registered domains)
- TriageEngine (application orchestrator)
- ReliabilityPipeline (validation chain)
- AutomationEvaluator (risk-based automation)
- PromptBuilder (security constraints)
- 3 Providers (Mock, Ollama, Cloud)
- SQLite persistence
- FastAPI API (11 endpoints)
- Streamlit UI (display only)
- HITL lifecycle (6 endpoints)
- Security evaluation (31 tests, 10 scenarios)
- Bias evaluation (23 tests)
- 526 tests passing

**Isolated Implementations (Not Wired):**
- Logistics Intelligence (8 modules)
- ML Adaptation (7 modules)
- Specialist Models (2 modules)
- Hybrid Decision Engine (1 module)
- Real Estate Domain (1 module)
- Governance Framework (1 module)
- Production Readiness (1 module)

### Known Limitations

- MockProvider primary evidence source
- Offline evaluation only
- Security/bias tested only with MockProvider
- No production deployment
- No authentication/authorization
- SQLite only
- Isolated modules not wired to pipeline

### Quality

- 526 tests passing, 7 skipped, 0 failures
- 0 ruff errors
- 0 mypy errors

---

## v0.1.0 — 2026-09-11

### Initial Release

- Core architecture (contracts, ports, domain, pipeline, prompts)
- 3 providers (Mock, Ollama, Cloud)
- 3 domain packs (Urban, Logistics, Infrastructure)
- TriageEngine orchestrator
- ReliabilityPipeline
- Risk-based automation
- HITL lifecycle
- Security evaluation
- Bias evaluation
- Evaluation framework
- Streamlit UI
- 393 tests passing

### Commits

| Commit | Description |
|--------|-------------|
| `c26dc66` | Initial CASE project snapshot |
| `65b3832` | Clean generated artifacts |
| `9c2a9af` | Bias evaluation corrections |
| `d825c41` | Centralize triage orchestration |
| `afbdc6f` | Extract composition root |
| `2a7e225` | Fix routing invariance |
| `345202b` | Wire risk-based automation |
| `1f4ae7d` | Update status |
| `0322f82` | Resolve mypy/ruff errors |
| `02f193e` | Finalize README, CHANGELOG |

---

## Post-v1.0 Roadmap

| Version | Focus |
|---------|-------|
| v1.0.1 | Architecture hardening |
| v1.0.2 | Evaluation improvements |
| v1.1 | Specialist model integration |
| v1.2 | ML adaptation improvements |
| v1.3 | Hybrid decision integration |
| v1.4 | Domain expansion |
| v1.5 | Advanced governance |
| v2.0 | Next-generation decision intelligence |
