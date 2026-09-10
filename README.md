# CASE — AI Decision Platform

## Foundation v0.3

CASE is a domain-agnostic AI Decision Platform that transforms unstructured operational cases into structured, validated, evidence-backed decisions with human oversight.

## Architecture

```text
Streamlit UI → FastAPI → Application → Domain → Ports → Infrastructure
```

## Project Structure

```text
src/
├── case_core/
│   ├── contracts/     # Pydantic v2 schemas
│   ├── domain/        # DomainRegistry, DomainPolicy
│   ├── ports/         # LLMProvider, RepositoryPort, AuditPort
│   ├── providers/     # MockProvider, OllamaProvider, CloudProvider
│   ├── reliability/   # Validation, repair, retry
│   ├── prompts/       # PromptBuilder
│   └── application/   # TriageEngine
├── case_api/
│   └── api/v1/        # FastAPI endpoints
└── case_infra/
    └── persistence/   # SQLite adapters
tests/
├── unit/
├── integration/
└── behavioral/
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Model Selection (Experimental — CLOSED)

**Primary model**: `llama3.2` (3.2B, Q4_K_M, 2.0 GB)
**Alternative**: `qwen3:8b` when quality prioritized over latency with adequate hardware

| Model | Classification | Avg Latency | Status |
|-------|---------------|-------------|--------|
| llama3.2 | 66.67% | 14.6s | Selected — primary |
| qwen3:8b | 73.33% | 131s | Alternative |
| phi4-mini | 60.00% | 19.6s | Discarded |
| gemma3:4b | 60.00% | 40.8s | Discarded |
| qwen3:4b | — | >120s | Discarded |
| deepseek-r1:8b | — | >500s | Partial/aborted — not used for selection |

**Caveats**: Offline benchmark, synthetic data (15 cases), CPU-only, not production performance. Accuracy ≠ calibrated probability.

> [!IMPORTANT]
> Model selection is closed and OUTSIDE the roadmap. No further model experiments or downloads.
> This decision does not change the architecture of CASE.

## Status

**Foundation v0.3** — Specification FROZEN.
Implementation Phase 0: Academic/Portfolio MVP.

**Implementation Readiness**: READY
**Blueprint Status**: FROZEN
**Benchmark Status**: PRELIMINARY (v0.2, 15 cases, llama3.2 selected)