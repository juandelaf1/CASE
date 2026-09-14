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
| HEAD | `02f193e` |
| Commits | 9 |
| Remote | NONE |
| Working tree | Clean |
| Python | 3.13.12 via `C:\Users\JUAN\miniconda3\python.exe` |
| Platform | Windows (PowerShell) |

---

## Current Project State

- **Foundation v0.3:** FROZEN. Contracts, ports, domain system, pipeline, prompts.
- **Blueprint v1.1:** FROZEN. Architecture, domain packs, security, automation, bias.
- **393 tests passing**, 7 skipped (Ollama integration), 0 failures.
- **TriageEngine implemented** and committed.
- **API delegates to TriageEngine** for triage endpoint.
- **Composition Root** extracted to `composition.py`.
- **3 domain packs:** Urban (partial), Logistics (full), Infrastructure (partial).
- **3 providers:** Mock, Ollama, Cloud.
- **Security evaluation:** 31 tests, 10 attack scenarios.
- **Risk-Based Automation:** 12 tests + 3 security, all domains wired.
- **Bias evaluation:** 23 tests, routing_invariance fixed, logistics-only pairs.
- **Phase 4 evaluation:** COMPLETED. All areas evaluated.

---

## COMPLETED

- Contracts (9 files, Pydantic v2)
- Ports (6 interfaces)
- DomainRegistry (3 domains)
- ReliabilityPipeline (parse, schema, semantic, domain, retry, repair)
- PromptBuilder (TIER1 + TIER3 security)
- TriageEngine (application layer orchestrator, 175 lines, 25 tests)
- Composition Root (extracted to composition.py)
- MockProvider (17 tests)
- OllamaProvider (13 tests + 5 integration)
- CloudProvider (24 tests)
- Evaluation Framework (runner, metrics, reports)
- Streamlit UI (Decision Center, Status, HITL display)
- HITL Lifecycle (6 API endpoints, lifecycle states, audit)
- Logistics Domain Pack (policy, routing, automation, recommended actions)
- Urban Policy (validation, urgency, DefaultAutomationPolicy)
- Infrastructure Policy (validation, urgency, DefaultAutomationPolicy)
- Security Evaluation (31 tests, 10 scenarios)
- Risk-Based Automation (12 tests + 3 security, all domains)
- Bias Evaluation (23 tests, routing_invariance fixed)
- Phase 4 Final Evaluation (all areas evaluated)
- API (delegates to TriageEngine)
- Persistence (SQLite adapters)
- Audit (AuditPort, event trail)

---

## CURRENT PRIORITY

**Phase 5 — Hybrid Decision Intelligence.** After Phase 4 Specialist Models is complete, the next priority is Hybrid Decision Intelligence.

---

## NEXT PRIORITY

**Phase 6 — Additional Domain Packs.** After Phase 5 Hybrid Decision Intelligence is complete, the next priority is Additional Domain Packs.

---

## DEFERRED

- Urban/Infrastructure Routing (FUTURE)
- Urban/Infrastructure domain-specific automation (DefaultAutomationPolicy used)
- Bias pairs for Urban and Infrastructure domains (FUTURE)
- Quality hardening
- Documentation consolidation
- Demo preparation
- Portfolio readiness

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
- 0 ruff errors
- 0 mypy errors
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
CURRENT PHASE: Phase 5 — Hybrid Decision Intelligence [ACTIVE]
CURRENT SPRINT: Sprint 5 — Hybrid Decision Intelligence [ACTIVE]
CURRENT TASK: Implement Decision Engine, combine LLM + specialist + rules + evidence + HITL + audit
NEXT TASK: Phase 6 — Additional Domain Packs
```

---

## Autonomous Execution Protocol

### Phase Numbering
| Phase | Name | Status |
|-------|------|--------|
| Phase 1 | CASE v1 | COMPLETED |
| Phase 2 | Logistics Intelligence | COMPLETED |
| Phase 3 | ML Adaptation | COMPLETED |
| Phase 4 | Specialist Models | COMPLETED |
| Phase 5 | Hybrid Decision Intelligence | ACTIVE |
| Phase 6 | Additional Domain Packs | FUTURE |
| Phase 7 | Advanced Governance/Security | FUTURE |
| Phase 8 | Production/Scale Readiness | FUTURE |

### Quality Gates
Before advancing to the next phase, all quality gates must pass:
- `pytest` 0 failures
- `ruff` 0 errors
- `mypy` 0 errors
- Integration tests all pass
- No regressions in existing capabilities

### Exit Criteria
Each phase must meet its exit criteria before the next phase begins:
- **Phase 2 exit:** All logistics intelligence components implemented, tested, and evaluated
- **Phase 3 exit:** ML adaptation pipeline operational with fine-tuned models
- **Phase 4 exit:** Specialist models deployed and integrated with the LLM pipeline
- **Phase 5 exit:** Full hybrid decision pipeline operational end-to-end
- **Phase 6 exit:** New domain packs implemented with bias evaluation coverage
- **Phase 7 exit:** Governance and security capabilities production-ready
- **Phase 8 exit:** Production deployment successful with scale validation

### Change-Control Rules
Before adding any of the following, there must be explicit technical justification:
- Models
- Dependencies
- Infrastructure
- Frameworks
- Architectural changes
This maps to I10 (complexity requires justification).

### Scope Boundaries
The following must NOT be implemented within the current milestone without a new explicit decision:
- BERT / encoder models
- Fine-tuning / LoRA
- RAG (retrieval-augmented generation)
- Agent frameworks
- Ensembles
- New Domain Packs (Finance, Real Estate, etc.)
- New infrastructure (Kubernetes, Docker, cloud deployment)
- Speculative ML optimization
- Unjustified benchmarks

---

## UPDATE PROTOCOL

This file must be updated when:
- A milestone is completed
- The current priority changes
- A new phase begins
- A significant architectural decision is made
- The working tree state changes materially
