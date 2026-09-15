# Changelog

All notable changes to CASE will be documented in this file.

---

## [Unreleased]

### Added
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
