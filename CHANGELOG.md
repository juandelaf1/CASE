# Changelog

All notable changes to CASE are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-09-11

### Initial Release — CASE Decision Platform

#### Core Architecture

- **Contracts:** 9 Pydantic v2 schema files (operational_case, decision, lifecycle, evidence, error, audit, llm, automation, telemetry)
- **Ports:** 6 ABC interfaces (LLMProvider, DomainPolicy, AuditPort, RepositoryPort, DecisionRepositoryPort, AutomationPolicy)
- **Domain Registry:** 3 domains registered (Urban Operations, Logistics, Infrastructure)
- **Reliability Pipeline:** Full validation chain (JSON parse, schema, semantic, domain, retry with backoff, terminal failure)
- **Prompt Builder:** TIER1_SYSTEM + TIER3_DEVELOPER security constraints
- **TriageEngine:** Application-layer orchestrator, domain-agnostic, provider-agnostic
- **Composition Root:** Dependency wiring extracted to `composition.py`

#### Providers

- **MockProvider:** Deterministic responses for 10 test scenarios, 17 tests
- **OllamaProvider:** Local LLM integration, 13 unit tests + 5 integration tests
- **CloudProvider:** OpenAI-compatible API, 24 tests (mock HTTP)

#### Domain Packs

- **Logistics:** Full domain pack — policy, 6 incident types, routing, recommended actions, 5 departments, LogisticsAutomationPolicy
- **Urban Operations:** Policy, evidence validation, urgency classification, DefaultAutomationPolicy
- **Infrastructure:** Policy, evidence validation, urgency classification, DefaultAutomationPolicy

#### Reliability & Validation

- JSON parsing with error recovery
- Schema validation (5 required fields, enum values, confidence 0-1)
- Semantic validation (reason length >= 10, evidence_summary length >= 5)
- Domain validation (policy-specific evidence requirements)
- Retry with exponential backoff (MAX_VALIDATION_RETRIES=3, MAX_TRANSIENT_RETRIES=2)
- Terminal failure handling with audit trail

#### Risk-Based Automation

- AutomationEvaluator with risk matrix
- Effective urgency: max(LLM urgency, case urgency) — prevents urgency downgrade
- Three outcomes: AUTO_APPROVE, HUMAN_REVIEW, ESCALATE
- LogisticsAutomationPolicy: domain-specific rules, 5 departments
- DefaultAutomationPolicy: conservative generic policy for Urban/Infrastructure
- Security tests: 3 anti-manipulation tests

#### Human-in-the-Loop (HITL)

- 6 API endpoints: pending, approve, reject, escalate, modify, under-review
- Decision lifecycle: AI_PROPOSED → UNDER_REVIEW → APPROVED/MODIFIED/REJECTED/ESCALATED
- Transition validation (cannot approve from REJECTED)
- Full audit trail for all HITL actions

#### Security

- TIER3_DEVELOPER prompt constraints (UNTRUSTED instructions)
- Schema validation blocks manipulation
- Effective urgency prevents downgrade
- 31 security tests, 10 attack scenarios
- Prompt injection defense tested

#### Bias Evaluation

- BiasEvaluator class with counterfactual pair analysis
- 10 bias pairs (logistics domain)
- Metrics: pair consistency rate, decision invariance, urgency invariance, routing invariance, automation invariance, HITL consistency
- routing_invariance_rate bug fixed

#### Evaluation Framework

- EvaluationRunner for single case and dataset execution
- Metrics: decision accuracy, urgency accuracy, confidence, timing, error rate
- ReportGenerator for JSON output
- Dataset loader for test scenarios

#### API

- FastAPI with 11 endpoints
- Health check, domains, triage, audit, HITL lifecycle
- Delegates to TriageEngine for all triage operations

#### Persistence

- SQLite adapters: repository, audit, decision repository
- Decision lifecycle tracking
- Audit event storage

#### UI

- Streamlit app: Decision Center, System Status, HITL display
- Display only, no write operations

#### Testing

- 393 tests passing, 7 skipped (Ollama integration), 0 failures
- 18 unit test files, 2 integration test files
- Behavioral evaluation: 79 tests (BS001-BS030)
- Quality gates: ruff 0 errors, mypy 0 errors

#### Quality Hardening

- All mypy errors resolved (22 errors across 11 files)
- All ruff errors resolved (66 errors)
- Unused dependencies removed (sqlalchemy, pydantic-settings, python-dotenv)
- httpx added as direct dependency
- Type annotations added where missing

---

## Milestones

| Commit | Description |
|--------|-------------|
| `c26dc66` | Initial CASE project snapshot |
| `65b3832` | Clean generated artifacts, ignore runtime files |
| `9c2a9af` | Bias evaluation framework corrections |
| `d825c41` | Centralize triage orchestration (TriageEngine) |
| `afbdc6f` | Extract application composition root |
| `2a7e225` | Fix routing invariance evaluation |
| `345202b` | Wire risk-based automation in TriageEngine production path |
| `1f4ae7d` | Update status after automation wiring commit |
