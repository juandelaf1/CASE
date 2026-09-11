# CASE Agent Context

READ THIS FILE BEFORE MODIFYING CASE.

---

## Project Identity

CASE is a domain-agnostic, provider-agnostic AI Decision Platform. It transforms unstructured operational cases into structured, validated, evidence-backed decisions with human oversight.

**Core architecture:** Contracts → Ports → Domain → Providers → Reliability → Application → API → UI

**Frozen specs:** Foundation v0.3, Blueprint v1.1. Do not modify without explicit decision.

---

## Current Repository

| Field | Value |
|-------|-------|
| Path | `C:\Users\JUAN\Desktop\Proyectos\CASE` |
| Branch | `master` |
| HEAD | `9c2a9af` (fix: bias evaluation framework corrections) |
| Remote | NONE |
| Working tree | 2 files modified + 1 new (Composition Root extraction, uncommitted) |
| Python | 3.13.12 via `C:\Users\JUAN\miniconda3\python.exe` |
| Platform | Windows (PowerShell) |

---

## Current Project State

- **Foundation v0.3:** FROZEN. Contracts, ports, domain system, pipeline, prompts.
- **Blueprint v1.1:** FROZEN. Architecture, domain packs, security, automation, bias.
- **377 tests passing**, 7 skipped (Ollama integration), 0 failures.
- **TriageEngine implemented** but NOT committed (working tree dirty).
- **API delegates to TriageEngine** for triage endpoint.
- **3 domain packs:** Urban (partial), Logistics (full), Infrastructure (partial).
- **3 providers:** Mock, Ollama, Cloud.
- **Security evaluation:** 28 tests, 10 attack scenarios.
- **Risk-Based Automation:** 12 tests, Logistics only.
- **Bias evaluation:** 10 pairs (logistics only), routing_invariance_rate bug present.

---

## COMPLETED

- Contracts (9 files, Pydantic v2)
- Ports (6 interfaces)
- DomainRegistry (3 domains)
- ReliabilityPipeline (parse, schema, semantic, domain, retry, repair)
- PromptBuilder (TIER1 + TIER3 security)
- TriageEngine (application layer orchestrator, 175 lines, 15 tests)
- MockProvider (30 tests)
- OllamaProvider (13 tests + 5 integration)
- CloudProvider (28 tests)
- Evaluation Framework (runner, metrics, reports)
- Streamlit UI (Decision Center, Status, HITL display)
- HITL Lifecycle (6 API endpoints, lifecycle states, audit)
- Logistics Domain Pack (policy, routing, automation, recommended actions)
- Security Evaluation (28 tests, 10 scenarios)
- Risk-Based Automation (12 tests, 3 security tests)
- Bias Evaluation (8 standalone functions, 10 pairs, partial)
- API (delegates to TriageEngine)
- Persistence (SQLite adapters)
- Audit (AuditPort, event trail)

---

## CURRENT PRIORITY

**Commit the Phase 2 fix.** 2 files modified, all tests passing, working tree dirty.

Files pending commit:
- `src/case_core/evaluation/metrics/bias.py` (modified)
- `tests/unit/test_bias_evaluation.py` (modified)

---

## NEXT PRIORITY

**Phase 3 — V1 Capability Completion.** Classify Urban/Infrastructure gaps.

---

## DEFERRED

- Urban/Infrastructure Automation (no AutomationPolicy)
- Urban/Infrastructure Routing (no classify_incident_type)
- Fix routing_invariance_rate bug in bias evaluation
- Bias pairs for Urban and Infrastructure domains
- Final evaluation
- Quality hardening

---

## DO NOT DO

- Do NOT benchmark models
- Do NOT download models
- Do NOT redesign architecture
- Do NOT modify frozen specs (Foundation v0.3, Blueprint v1.1)
- Do NOT add speculative infrastructure
- Do NOT duplicate existing functionality
- Do NOT rewrite working components without evidence of problems
- Do NOT commit unless explicitly requested
- Do NOT add new Domain Packs without decision
- Do NOT add RAG, agents, ensembles, BERT, fine-tuning without decision
- Do NOT run benchmarks without decision
- Do NOT modify `C:\Users\JUAN` (parent directory)

---

## SAFETY RULES

Before modifying any file:

1. `git status` — check working tree
2. `git diff` — check what changed
3. Read the file you plan to modify
4. Read related tests
5. Understand the contracts involved
6. Modify minimally
7. Run `pytest` to verify
8. Run `ruff check` and `mypy` if modifying src/
9. Inspect `git diff` after changes
10. Report what you did

---

## QUALITY GATES

After any code change:

```powershell
C:\Users\JUAN\miniconda3\python.exe -m pytest tests/ -q
C:\Users\JUAN\miniconda3\python.exe -m ruff check src tests
C:\Users\JUAN\miniconda3\python.exe -m mypy src
```

Expected:
- 0 pytest failures
- No new ruff errors (65 pre-existing)
- No new mypy errors (22 pre-existing across 11 files)
- API regression: all 11 integration tests pass

---

## RECOVERY RULES

If a task is interrupted or you lose context:

1. `git status` — check what's modified
2. `git diff --stat` — check scope of changes
3. `git log --oneline -5` — check recent commits
4. Read changed files
5. Run `pytest` — check if tests pass
6. Never blindly rewrite files
7. Never assume previous execution succeeded
8. Compare current state against this document

---

## CURRENT ROADMAP POINTER

```
CURRENT PHASE: Phase 3 — V1 Capability Completion
CURRENT SPRINT: Sprint 1 — CASE Decision Platform [COMPLETED]
CURRENT TASK: Commit Phase 2 fix
NEXT TASK: Classify Urban/Infrastructure gaps
```

---

## UPDATE PROTOCOL

This file must be updated when:
- A milestone is completed
- The current priority changes
- A new phase begins
- A significant architectural decision is made
- The working tree state changes materially
