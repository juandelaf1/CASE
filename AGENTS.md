# CASE — Agent Instructions

> Guidelines for AI agents and automated tools working with this repository.

---

## Project Identity

**CASE** — Case Assessment and Structured Evaluation

CASE is a domain-agnostic, provider-agnostic AI decision orchestration platform for operational case triage with human oversight.

**Canonical expansion:** Case Assessment and Structured Evaluation

**Do not** use competing expansions such as "Context-Aware Safety/Security Evaluation" unless explicitly documented elsewhere in the repository.

---

## Architecture Rules

### Frozen Invariants (I01-I15)

| ID | Rule |
|----|------|
| I01 | Domain-agnostic core — no `if domain ==` checks in core logic |
| I02 | Provider-agnostic via ports — all LLM interaction through `LLMProvider` ABC |
| I03 | Raw LLM output never trusted — always validated through ReliabilityPipeline |
| I04 | Critical boundaries type-safe — Pydantic v2 at all public contract boundaries |
| I05 | Failures explicit — `CASEError` with category, recoverability, retryability |
| I06 | Human oversight (HITL) — full decision lifecycle with approve/reject/modify/escalate |
| I07 | Quality claims require evidence — no unverified assertions |
| I08 | Benchmarks cannot be fabricated — evaluation results must be reproducible |
| I09 | Minimize sensitive data — no PII in test cases or evaluation |
| I10 | Complexity requires justification — new dependencies/architecture need documented reason |
| I11 | Public contracts cannot change silently — breaking changes require version bump |
| I12 | Domain logic cannot leak into Core — domain-specific code stays in domain packs |
| I13 | Provider-specific logic behind interfaces — no provider imports in core |
| I14 | Production claims require evidence — no deployment claims without deployment |
| I15 | Limitations documented — known limitations must be explicitly stated |

### Architectural Boundaries

- `src/case_core/contracts/` — Frozen foundation. Do not modify without explicit decision.
- `src/case_core/ports/` — Frozen interfaces. Do not modify without explicit decision.
- `src/case_core/application/engine.py` — Core orchestrator. Minimal changes only.
- `src/case_core/reliability/pipeline.py` — Validation chain. Do not bypass.
- `src/case_core/prompts/builder.py` — Prompt construction. Security constraints enforced.

### Connected vs. Isolated

- **Connected:** Components wired via `composition.py` and executed by `TriageEngine`
- **Isolated:** Implemented and tested but not part of the running pipeline

Do not present isolated modules as connected. Do not claim isolated modules are part of the end-to-end execution path.

---

## Coding Conventions

### Python

- Python 3.11+
- Type hints required (mypy strict mode)
- Pydantic v2 for all data contracts
- `from __future__ import annotations` in all files
- No `Any`/`dict` at critical boundaries without justification

### Quality Gates

After any code change, all must pass:

```bash
pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py
ruff check src tests
mypy src --ignore-missing-imports
```

Expected: 0 failures, 0 ruff errors, 0 mypy errors.

### Testing

- Tests in `tests/unit/` and `tests/integration/`
- `tests/unit/test_streamlit_client.py` is permanently skipped (ModuleNotFoundError)
- `test_ollama_integration.py` tests are skipped when Ollama is not running
- Do not fabricate test results
- Do not modify tests to improve numbers

---

## Documentation Rules

### Honesty

- Never claim production deployment if there is none
- Never claim autonomous decision-making
- Never present isolated modules as connected
- Never invent capabilities
- Never fabricate metrics or benchmarks

### Terminology

Prefer:
- implemented, connected, tested, isolated, experimental, planned
- AI decision orchestration, controlled decision boundary
- provider abstraction, domain policy, contract validation
- reliability pipeline, risk-based routing, human-in-the-loop

Avoid:
- AI magic, autonomous intelligence, revolutionary
- enterprise-ready, production-grade (unless evidenced)
- state-of-the-art, cutting-edge

### Project Type

CASE is a **portfolio-grade research/engineering project**. It demonstrates architectural thinking, not production deployment. The architecture is production-oriented, but the system is not a production system.

---

## Dependency Rules

- No new dependencies without documented justification (I10)
- No provider-specific imports in core logic (I13)
- No domain-specific imports in core logic (I12)
- Core must remain domain-agnostic and provider-agnostic

---

## Safety Rules

- Raw LLM output is never trusted directly (I03)
- Risk increases human involvement, not decreases
- Conservative by default: when in doubt, route to humans
- Full audit trail for all decisions
- Human override available at any lifecycle state

---

## What NOT to Do

- Do not refactor working code without need
- Do not introduce unnecessary dependencies
- Do not alter business logic for presentation
- Do not change APIs merely for aesthetics
- Do not change tests to make numbers look better
- Do not remove limitations because they look bad
- Do not fake integration between isolated modules
- Do not create placeholder implementations that appear complete
- Do not rewrite git history
- Do not force push
- Do not commit secrets, keys, or credentials
