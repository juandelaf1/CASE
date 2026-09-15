# Phase 3 Proposal — CASE

> Proposal for next development phase. Created: 2026-09-15.
> Status: PROPOSED — not yet approved.

---

## Phase 2 Summary

Phase 2 (Evidence Capabilities) made existing CASE capabilities observable, measurable, and auditable:

- **Case Explorer:** Paginated case list, search, full case detail with audit trail
- **Provider Lab:** Provider config, telemetry, mock/real status
- **Evaluation Lab:** Synthetic evaluation with honest metrics, data source labels
- **Counterfactual Lab:** 10 counterfactual pairs, invariance evaluation
- **Architecture:** Connected core vs isolated extensions visualization
- **Failure UX:** Standardized health checks, error states, empty states
- **Navigation:** Operations / Intelligence / Engineering sections

---

## Phase 3 — Proposed Direction

### Option A: Real Provider Integration

Connect a real LLM provider (Ollama local or cloud) to demonstrate end-to-end pipeline with actual LLM responses.

**Work:**
- Configure Ollama or cloud provider in deployment
- Run evaluation with real provider
- Compare real vs mock provider behavior
- Document real-world latency, cost, reliability

**Value:** Proves the pipeline works with real LLMs, not just mocks.

**Risk:** Provider availability, latency, cost.

### Option B: Multi-Domain Expansion

Register additional domains (logistics, infrastructure) and run cross-domain evaluation.

**Work:**
- Register LogisticsPolicy and InfrastructurePolicy
- Create domain-specific evaluation scenarios
- Run counterfactual evaluation across domains
- Compare domain policy behavior

**Value:** Demonstrates domain-agnostic architecture actually works across domains.

**Risk:** Domain policies may need refinement.

### Option C: Streamlit Deployment

Deploy the Streamlit UI to Render alongside the existing API service.

**Work:**
- Configure Render service for Streamlit
- Connect to deployed API
- Test end-to-end flow in production-like environment

**Value:** Complete deployed product demo.

**Risk:** Render Streamlit hosting limitations.

### Option D: Advanced Evaluation

Expand evaluation framework with larger datasets, statistical rigor, and cross-validation.

**Work:**
- Generate larger synthetic datasets (50+ cases)
- Add statistical confidence intervals
- Implement cross-validation
- Add cost/latency benchmarks

**Value:** Stronger evidence for portfolio demonstrations.

**Risk:** Synthetic data limitations remain.

---

## Recommendation

**Option A (Real Provider Integration)** — highest value for portfolio. Demonstrates the full pipeline with real LLM responses, which is the core value proposition of CASE.

---

## Constraints

- No new dependencies without documented justification (I10)
- No domain logic leaking into core (I12)
- No provider-specific coupling in core (I13)
- All claims must be evidence-based
- Portfolio-grade project — not production deployment
