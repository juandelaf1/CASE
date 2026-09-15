# PHASE 2 — GOLDEN BASELINE

**Established:** 2026-09-14
**Completed:** 2026-09-15
**Branch:** `case/phase-2-evidence-capabilities`
**HEAD:** `dbbbfb5` (Phase 2 completion)

## Metrics

| Metric | Value |
|--------|-------|
| pytest | 568 passed, 7 skipped, 0 failures |
| ruff | All checks passed |
| mypy | Success: no issues found (84 source files) |
| API health | `GET /health` → `{"status":"ok","version":"1.0.0"}` |
| Streamlit | HTTP 200 on localhost:8501 |

## Frozen Invariants

All 15 frozen invariants (I01-I15) verified and active.

## API Endpoints

| # | Method | Path | Phase |
|---|--------|------|-------|
| 1 | GET | `/` | v1 |
| 2 | GET | `/health` | v1 |
| 3 | GET | `/domains` | v1 |
| 4 | POST | `/api/v1/triage` | v1 |
| 5 | GET | `/api/v1/audit/{case_id}` | v1 |
| 6 | GET | `/api/v1/hitl/pending` | v1 |
| 7 | GET | `/api/v1/hitl/{decision_id}` | v1 |
| 8 | POST | `/api/v1/hitl/{decision_id}/under-review` | v1 |
| 9 | POST | `/api/v1/hitl/{decision_id}/approve` | v1 |
| 10 | POST | `/api/v1/hitl/{decision_id}/reject` | v1 |
| 11 | POST | `/api/v1/hitl/{decision_id}/escalate` | v1 |
| 12 | POST | `/api/v1/hitl/{decision_id}/modify` | v1 |
| 13 | GET | `/api/v1/cases` | Phase 2 |
| 14 | GET | `/api/v1/cases/{case_id}` | Phase 2 |
| 15 | GET | `/api/v1/providers` | Phase 2 |

## Streamlit Pages

| Section | Page | Status |
|---------|------|--------|
| Operations | Control Room | CONNECTED |
| Operations | Triage | CONNECTED |
| Operations | Case Explorer | CONNECTED |
| Operations | Human Review | CONNECTED |
| Operations | Audit Trail | CONNECTED |
| Intelligence | Provider Lab | CONNECTED |
| Intelligence | Evaluation Lab | CONNECTED |
| Intelligence | Counterfactual Lab | CONNECTED |
| Engineering | Architecture | CONNECTED |

## Protection Rule

If any Phase 2 modification breaks this baseline:

STOP → diagnose → fix/revert → restore → continue
