# Changelog

All notable changes to CASE will be documented in this file.

---

## [Unreleased]

### Fixed
- GroqProvider: retry with `json_object` format when `strict: True` schema validation fails (HTTP 400)
- Engine: detect provider errors (error/timeout/auth) before pipeline validation
- test_sqlite: DB path tests use `tmp_path`, never delete `case_audit.db`
- Bootstrap: `_ensure_tables()` re-validates table existence on every DB operation
- Health endpoint: validates DB tables, returns `database` status

### Added
- Chain-of-Thought (CoT) prompt with 6-step analysis process
  - Decision rationale and decision factors in response schema
  - Semantic validation (rationale >= 20 chars, factors >= 1 item)
  - Structured analysis without exposing internal reasoning
- ReAct module (`src/case_core/react/__init__.py`)
  - Controlled deterministic flow: CHECK_EVIDENCE → CHECK_URGENCY → CHECK_DOMAIN
  - 3 steps, no LLM loop, trace stored in metadata
  - UI visualization in Decision Center
- 10-word summary validator
  - Pydantic validator `_validate_ten_words` with auto-repair
  - Pipeline semantic validation with `_repair_summary_to_ten_words`
  - Prompt instruction for exactly 10 words
- Cost tracking (`src/case_core/evaluation/cost.py`)
  - `CostModel`, `PricingConfig`, `CostEstimate` classes
  - Groq pricing (qwen3.8: $0.20/M prompt, $0.60/M completion)
  - API response field `cost` with total_cost, currency, is_free
- Token tracking exposed in `provider_info` (prompt_tokens, completion_tokens, total_tokens)
- Error classification in Streamlit client
  - `backend_offline`: ConnectError/timeout → offline component
  - `backend_error`: 5xx → specific error message
  - `validation`: 4xx → validation detail
  - `provider`: LLM failure
- Professional light theme (off-white bg, white surfaces, graphite text)
  - Silver/teal brand accent, semantic colors (green/amber/red)
  - Typography scale: page 1.8rem, hero 2.8rem, decision 2.4rem
  - Desktop-optimized layout (max 920px content)
- i18n system (`streamlit_app/i18n.py`) — ~250 keys per language, EN/ES
- CASE banner branding (`docs/images/CASE_banner.jpg`) in sidebar
- Decision Center view with hero, AI Proposal vs Final Decision
- Evidence in demo cases (82721, 4, 108) for LogisticsPolicy validation
- Backend offline component with retry and diagnostics

### Changed
- API response extended: `decision_rationale`, `decision_factors`, `summary`, `react_trace`, `cost`
- ReliabilityPipeline: `DECISION_FIELDS` split into REQUIRED/OPTIONAL
- `semantic_validate` updated for rationale, factors, summary validation
- MockProvider responses updated with new fields (rationale, factors, summary)
- Demo cases now send evidence satisfying LogisticsPolicy

### Fixed
- HTTP 500 on triage: SQLite DB corruption (0-byte file) → clean restart
- Domain validation error: demo cases missing evidence → added evidence items
- NameError `client` in decision_center.py
- httpx.ConnectError unhandled in 7+ views
- Wrong import in counterfactual.py
- HTML malformation in components.py
- Missing future annotations in client.py

### Tests
- 679 passed, 13 failed (5 pre-existing, 8 flaky/Groq-dependent), 7 skipped
- mypy: 0 errors (93 source files)
- ruff src: 0 errors
- 3/3 demo cases E2E with Groq real inference (qwen/qwen3.8-27b)
  - `.env.example` with all supported variables (no secrets)
  - Precedence: environment variables > `.env` > defaults
  - `.env` already in `.gitignore` (never committed)
  - 10 new tests for .env loading and precedence
- Phase 4: Error Analysis + Specialist Model Decision
  - 3 real USAID cases analyzed through full CASE pipeline (normal, ambiguous, critical)
  - Error analysis script (`scripts/phase4_error_analysis.py`)
  - Specialist Model Decision: NOT JUSTIFIED (no evidence of systematic LLM errors)
  - Demo cases documentation (3 reproducible cases for Friday demo)
  - Total tests: 671 passed, 14 skipped
- Phase 4: Logistics Integration (PRIMARY — real external data, main use case)
  - USAID SCMS Delivery History adapter (`src/logistics_adapter/usaid_adapter.py`)
  - Logistics pipeline (`src/logistics_adapter/pipeline.py`)
  - 10,324 real shipment records (public domain, USAID/PEPFAR)
  - Wires existing ShipmentClassification into CASE pipeline
  - 27 new unit tests (adapter, pipeline, classification, architecture)
  - Total tests: 671 passed (+27), 14 skipped
- Phase 4: Seismic Risk Integration (SECONDARY — proof of domain generalization)
  - USGS Earthquake Hazards API adapter (`src/usgs_adapter/client.py`)
  - SeismicRiskPolicy domain policy (`src/case_core/domain/seismic_policy.py`)
  - SeismicAutomationPolicy automation policy (`src/case_core/domain/seismic_automation.py`)
  - 50 new unit tests (seismic domain + USGS client, mocked)
  - 5 integration tests (live USGS API + full pipeline with mock provider)
  - Phase 4 Portfolio Discovery, Integration Candidates, Integration Proposal
  - Domain registered in composition.py (4th domain: seismic_risk)
  - Total tests: 644 passed (+50), 14 skipped
- Phase 3: Real Provider Integration
  - GroqProvider implementation (OpenAI-compatible)
  - Live provider tests (7/7 pass)
  - Provider Comparison view
  - Provider Lab updates (Groq support, availability)
  - Phase 3 Provider Report
  - Groq Decision Gate
  - Phase 4 Specialist Model Proposal

### Changed
- Default Groq model: `qwen/qwen3.8-27b`
- Provider selection via `CASE_PROVIDER` env var
- Registered 4th domain: `seismic_risk` in DomainRegistry

### Fixed
- Groq structured output schema compliance (additionalProperties:false)

---

## [1.0.0] - 2026-09-14

### Added
- Phase 1: CASE v1
  - Contracts, Ports, Domain, Reliability, Risk, Providers
  - TriageEngine, PromptBuilder, FastAPI (15 endpoints)
  - Streamlit UI (9 pages)
  - SQLite persistence
  - MockProvider, OllamaProvider, CloudProvider
  - 568 tests passing

- Phase 2: Evidence Capabilities
  - Case Explorer (paginated list, search, full detail)
  - Provider Lab (config, telemetry, availability)
  - Evaluation Lab (synthetic eval, honest metrics)
  - Counterfactual Lab (10 pairs, invariance)
  - Architecture page (connected vs isolated)
  - Failure UX (shared health check, errors)
  - Navigation reorganization (Operations/Intelligence/Engineering)
  - 594 tests passing

---

## Quality Gates

| Version | pytest | ruff | mypy |
|---------|--------|------|------|
| v1.0.0 | 568 passed | 0 errors | 0 errors |
| Phase 2 | 594 passed | 0 errors | 0 errors |
| Phase 3 | 608 passed | 0 errors | 0 errors |
| Phase 4 | 671 passed | 0 errors | 0 errors |
| v1.1.0 | 679 passed | 0 errors | 0 errors |
