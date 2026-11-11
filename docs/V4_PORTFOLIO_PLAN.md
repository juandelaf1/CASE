# V4 Portfolio Plan — CASE Ecosystem Evidence & Portfolio Release

**Branch:** `v4/portfolio-release`  
**Baseline:** `8c97976` (V3 Ecosystem Integration)  
**Date:** 2026-09-28

---

## CURRENT EXPERIENCE

### What the User Sees

**12 Streamlit pages** organized in two groups:

**DEMO FLOW (primary):**
- Decision Center — landing page, 3 pre-built demo cases, full pipeline visualization
- Triage — custom case submission, 7-step pipeline visual, LLM proposal vs CASE governance
- Comparison — live side-by-side provider comparison (Groq/Ollama/Mock)
- Human Review — pending decisions, approve/reject/escalate/modify actions
- Audit Trail — event timeline with color-coded event types

**TECHNICAL/ENGINEERING:**
- Cases (Case Explorer) — paginated browser with domain/lifecycle filters
- Control Room — health checks, decision metrics, provider status
- Status — system status, provider availability, configuration
- Evaluation Lab — 3 synthetic test cases, match/mismatch results
- Counterfactual Lab — 10 bias pairs, invariance rates
- Provider Lab — health checks, latency/cost charts, telemetry
- Architecture — connected/isolated components, layer map

**15 API endpoints** (17 including seismic)  
**4 providers** (Mock default, Groq, Ollama, Cloud)  
**5 domains** (urban, logistics, infrastructure, seismic, real_estate)  
**Bilingual** (Spanish default, English via i18n)

---

## CURRENT EVIDENCE

### REAL (requires external services)
| Evidence | Source | Status |
|----------|--------|--------|
| Groq inference | Groq API | Requires API key, ~255ms |
| Ollama inference | Local server | Requires running Ollama, ~18s |
| Cloud inference | OpenAI-compatible | Requires API key, not publicly tested |
| USGS seismic data | USGS API | External adapter, graceful degradation |
| SQLite persistence | Local file | Real persistence + audit |
| API auth | APIKeyAuthMiddleware | Constant-time comparison |
| Rate limiting | RateLimitMiddleware | Per-IP sliding window |

### SYNTHETIC / DETERMINISTIC
| Evidence | Source | Notes |
|----------|--------|-------|
| MockProvider | 10 pre-canned responses | Deterministic, zero latency |
| Evaluation page | 3 hardcoded urban cases | MockProvider only |
| Counterfactual page | 10 logistics bias pairs | MockProvider only |
| Decision Center demos | 3 pre-built cases | Run with active provider |
| Architecture metrics | Hardcoded component lists | Not live data |
| Bias evaluation tests | Synthetic data | Metric computation verified, not end-to-end |
| Security scenarios | 10 attack cases | Exist but no UI runner |

---

## CURRENT GAPS

### Critical
1. **All evaluation is MockProvider-based** — security/bias results demonstrate framework, not real LLM behavior
2. **Bias pairs: logistics only** — 0 counterfactual pairs for urban/infrastructure/seismic
3. **Security scenarios: no UI runner** — 10 attack cases exist but must run programmatically
4. **Evaluation dataset tiny** — 3 cases in UI, framework supports arbitrary datasets

### Documentation
5. **DEVELOPMENT_STATUS.md outdated** — references old test counts
6. **ARCHITECTURE.md inconsistent** — says "11 endpoints" in one place, "15" in another
7. **README.md date outdated** — "Last checked: 2026-09-17"
8. **ROADMAP.md test counts wrong** — shows 568, actual is 813
9. **No UI screenshots** — only CASE_banner.jpg exists

### Code Quality
10. **Hardcoded Spanish in views** — triage.py, status.py, comparison.py, architecture.py have Spanish outside i18n
11. **CircuitBreakerProvider not default** — wrapper exists but composition.py doesn't use it

### Functional
12. **No auth demo in UI** — API has middleware, UI doesn't show it
13. **No real-time updates** — pages require manual rerun
14. **CloudProvider not tested publicly** — implementation exists, no live evidence

---

## CURRENT DEMO FLOWS

### What Works End-to-End
| Flow | Status |
|------|--------|
| MockProvider triage | FULLY DETERMINISTIC |
| Groq triage | REAL (requires API key) |
| Ollama triage | REAL (requires local server) |
| HITL lifecycle | FULLY WORKING |
| Audit trail | FULLY WORKING |
| Provider comparison | FULLY WORKING |
| Cost estimation | FULLY WORKING |
| Evaluation (synthetic) | WORKS (MockProvider only) |
| Counterfactual (synthetic) | WORKS (MockProvider only) |

### Demo Scripts (6 in examples/)
- demo_auto_approve.py — low-risk logistics
- demo_human_review.py — ambiguous case
- demo_escalate.py — critical case
- demo_invalid_output.py — terminal failure
- demo_hitl_lifecycle.py — full HITL workflow
- demo_all_domains.py — all 4 domains

---

## REQUIRED PORTFOLIO WORK

### P1: Control Room as Product Entry Point (HIGH)
**Problem:** Control Room exists but doesn't communicate the CASE story  
**Change:** Redesign to answer: What is CASE? Is it healthy? What's happening? What needs attention?  
**Evidence:** Real health data, real decision metrics, clear system status  
**Scope:** 1 page redesign  
**Risk:** LOW  
**Portfolio Value:** HIGH — first thing evaluators see

### P2: Signature Demo Case (HIGH)
**Problem:** No canonical end-to-end demo that tells the CASE story  
**Change:** Create one polished demo flow: Incident → Domain → Proposal → Validation → Risk → Decision → Audit  
**Evidence:** Real pipeline execution, clear labels  
**Scope:** 1 demo case + documentation  
**Risk:** LOW  
**Portfolio Value:** HIGH — makes the system understandable

### P3: Failure Demo (HIGH)
**Problem:** CASE handles model failure but it's not visible  
**Change:** Expose the retry/repair flow in the UI  
**Evidence:** Real ReliabilityPipeline behavior  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** HIGH — proves CASE is designed for failure

### P4: HITL Demo (MEDIUM)
**Problem:** HITL exists but the story isn't clear  
**Change:** Show why automation was not allowed, what the human did, what the audit recorded  
**Evidence:** Real lifecycle transitions  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** MEDIUM — demonstrates human control

### P5: Provider Evidence Lab (HIGH)
**Problem:** Provider Lab shows charts but doesn't tell the provider story  
**Change:** Show: provider replacement doesn't require rewriting CASE. Clear status labels: Real/Deterministic/Not Configured/Not Verified  
**Evidence:** Real provider behavior  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** HIGH — proves provider abstraction

### P6: Evaluation Presentation (MEDIUM)
**Problem:** Evaluation page exists but metrics aren't explained  
**Change:** For each metric: name, formula, source, scope, limitations  
**Evidence:** Real metric computation  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** MEDIUM — demonstrates measurement thinking

### P7: Counterfactual Presentation (MEDIUM)
**Problem:** Bias pairs exist but the story isn't clear  
**Change:** Show ORIGINAL vs COUNTERFACTUAL with statuses: INVARIANT/CHANGED/EXPECTED/UNEXPECTED  
**Evidence:** Real metric computation  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** MEDIUM — demonstrates bias awareness

### P8: Architecture as Portfolio Explanation (HIGH)
**Problem:** Architecture page lists components but doesn't explain the ecosystem  
**Change:** Show: Connected Core, Providers, Domains, Platform Capabilities, Isolated/Future  
**Evidence:** Real repository truth  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** HIGH — definitive portfolio explanation

### P9: Case Explorer / Decision Trace (MEDIUM)
**Problem:** Case Explorer exists but doesn't expose the full trace  
**Change:** Show: Input → Proposal → Validation → Risk → Decision → Human Action → Audit  
**Evidence:** Real persisted data  
**Scope:** UI enhancement  
**Risk:** LOW  
**Portfolio Value:** MEDIUM — strongest portfolio surface

### P10: Documentation Sync (HIGH)
**Problem:** Docs are outdated and inconsistent  
**Change:** Sync README, ARCHITECTURE, ROADMAP with current state  
**Evidence:** Repository truth  
**Scope:** Documentation  
**Risk:** LOW  
**Portfolio Value:** HIGH — evaluators read docs first

### P11: Hardcoded Spanish Fix (LOW)
**Problem:** Some views have Spanish outside i18n  
**Change:** Route through t() function  
**Evidence:** Code inspection  
**Scope:** Code quality  
**Risk:** LOW  
**Portfolio Value:** LOW — consistency

---

## PORTFOLIO CLAIM (Target)

> CASE is a modular AI decision orchestration ecosystem that connects LLM providers, domain policies, reliability controls, human oversight, persistence, auditability and evaluation through explicit boundaries and typed contracts.

Every part must be defensible from the repository.

---

## V4 SCOPE (Justified)

### IMPLEMENT
| # | Change | Priority |
|---|--------|----------|
| P1 | Control Room redesign | HIGH |
| P2 | Signature demo case | HIGH |
| P3 | Failure demo | HIGH |
| P5 | Provider evidence lab | HIGH |
P8 | Architecture as portfolio explanation | HIGH |
| P10 | Documentation sync | HIGH |
| P6 | Evaluation presentation | MEDIUM |
| P7 | Counterfactual presentation | MEDIUM |
| P9 | Case Explorer trace | MEDIUM |
| P4 | HITL demo | MEDIUM |

### DEFER
| # | Change | Reason |
|---|--------|--------|
| P11 | Hardcoded Spanish fix | Low value, large scope |
| — | New domains | Feature count, not evidence |
| — | New providers | Same |
| — | RBAC/Governance | Future scope |
| — | Distributed tracing | Over-engineering |

---

## IMPLEMENTATION ORDER

1. Control Room (entry point)
2. Signature demo case
3. Failure demo
4. HITL demo
5. Provider evidence lab
6. Evaluation presentation
7. Counterfactual presentation
8. Case Explorer trace
9. Architecture page
10. Documentation sync
11. Quality gates
12. Commit + push
