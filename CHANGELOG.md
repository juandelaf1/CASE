# Changelog

All notable changes to CASE will be documented in this file.

---

## [Unreleased]

### Added
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
