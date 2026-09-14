# CASE Decision Log

> Record of significant technical decisions. Last updated: 2026-09-14.

---

## D001: Foundation v0.3 Frozen

**Decision:** Freeze Foundation specification v0.3

**Context:** CASE needed stable contracts, ports, and pipeline specification.

**Options:**
1. Continue evolving specs
2. Freeze and implement

**Chosen:** Option 2

**Reason:** Stability enables parallel work. Specs are source of truth, not code.

**Trade-offs:** Cannot change specs without explicit review. May require decisions for changes.

**Date:** 2026-09

**Status:** ACTIVE

---

## D002: Blueprint v1.1 Frozen

**Decision:** Freeze Blueprint specification v1.1

**Context:** Architecture, domain packs, security, automation, bias needed stable reference.

**Options:**
1. Continue evolving
2. Freeze and implement

**Chosen:** Option 2

**Reason:** Consistency with Foundation. Clear reference for implementation.

**Trade-offs:** Same as D001.

**Date:** 2026-09

**Status:** ACTIVE

---

## D003: TriageEngine as Application Orchestrator

**Decision:** Single TriageEngine class orchestrates the full triage flow.

**Context:** Needed application-layer component to coordinate domain, provider, pipeline, persistence.

**Options:**
1. Multiple small services
2. Single orchestrator
3. Chain of responsibility

**Chosen:** Option 2

**Reason:** Simplicity. Single point of orchestration. Easy to test and reason about.

**Trade-offs:** God-class risk if too many responsibilities. Mitigated by delegation to ports.

**Date:** 2026-09-11

**Status:** COMMITTED (`d825c41`)

---

## D004: Composition Root Extraction

**Decision:** Extract dependency wiring to `composition.py`.

**Context:** `app.py` was doing both HTTP handling and dependency creation.

**Options:**
1. Keep in app.py
2. Extract to composition.py

**Chosen:** Option 2

**Reason:** Separation of concerns. Easier to test. Easier to swap dependencies.

**Trade-offs:** One more file. Minimal overhead.

**Date:** 2026-09-11

**Status:** COMMITTED (`afbdc6f`)

---

## D005: Risk-Based Automation

**Decision:** Implement risk-based automation with three outcomes.

**Context:** Needed to decide when to auto-approve, when to require human review.

**Options:**
1. Always auto-approve
2. Always human review
3. Risk-based (AUTO_APPROVE / HUMAN_REVIEW / ESCALATE)

**Chosen:** Option 3

**Reason:** Balances efficiency with safety. Conservative by design.

**Trade-offs:** More complex. Requires risk assessment logic.

**Date:** 2026-09-11

**Status:** COMMITTED (`345202b`)

---

## D006: MockProvider as Default

**Decision:** Use MockProvider as default in composition.py.

**Context:** Need deterministic responses for testing and demo.

**Options:**
1. Ollama as default
2. MockProvider as default
3. Config-based selection

**Chosen:** Option 2

**Reason:** No external dependencies for basic operation. Deterministic. Testable.

**Trade-offs:** Not realistic. Users must swap for real LLM.

**Date:** 2026-09

**Status:** ACTIVE

---

## D007: SQLite for Persistence

**Decision:** Use SQLite for all persistence.

**Context:** Need simple storage for demo/portfolio project.

**Options:**
1. PostgreSQL
2. SQLite
3. In-memory only

**Chosen:** Option 2

**Reason:** Zero setup. File-based. Sufficient for demo scope.

**Trade-offs:** No concurrent access. Not production-ready. Acceptable for portfolio.

**Date:** 2026-09

**Status:** ACTIVE

---

## D008: Isolated Module Implementation

**Decision:** Implement Phases 2-8 as isolated modules, not wired to pipeline.

**Context:** Phases 2-8 were implemented by autonomous agent. Modules are tested but not connected.

**Options:**
1. Wire everything to pipeline immediately
2. Implement as isolated modules
3. Skip entirely

**Chosen:** Option 2

**Reason:** Demonstrates extensibility without risk to working system. Wiring requires explicit justification per I10.

**Trade-offs:** Not end-to-end tested. May have integration issues discovered later.

**Date:** 2026-09-14

**Status:** COMMITTED

---

## D009: Honest Documentation

**Decision:** Document actual state honestly, including isolated modules.

**Context:** Previous documentation claimed "COMPLETED" for modules that aren't connected.

**Options:**
1. Keep misleading "COMPLETED" claims
2. Document honestly as "IMPLEMENTED, ISOLATED"

**Chosen:** Option 2

**Reason:** Transparency. Accurate state for future agents. I07 (quality claims require evidence).

**Trade-offs:** Less impressive-looking roadmap. Honest > impressive.

**Date:** 2026-09-14

**Status:** ACTIVE

---

## D010: Remove Benchmark Files

**Decision:** Remove root-level benchmark/test scripts from git.

**Context:** Root directory contained benchmark_candidates.py, test_qwen4b.py, etc.

**Options:**
1. Keep (they're harmless)
2. Remove from git, add to .gitignore

**Chosen:** Option 2

**Reason:** Clean repo. These are evaluation artifacts, not project code.

**Trade-offs:** None meaningful.

**Date:** 2026-09-14

**Status:** COMMITTED
