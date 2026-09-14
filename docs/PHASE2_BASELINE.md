# PHASE 2 — GOLDEN BASELINE

**Established:** 2026-09-14
**Branch:** `case/phase-2-evidence-capabilities`
**HEAD:** `7fc4797` (Phase 1 commit)

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

| # | Method | Path |
|---|--------|------|
| 1 | GET | `/` |
| 2 | GET | `/health` |
| 3 | GET | `/domains` |
| 4 | POST | `/api/v1/triage` |
| 5 | GET | `/api/v1/audit/{case_id}` |
| 6 | GET | `/api/v1/hitl/pending` |
| 7 | GET | `/api/v1/hitl/{decision_id}` |
| 8 | POST | `/api/v1/hitl/{decision_id}/under-review` |
| 9 | POST | `/api/v1/hitl/{decision_id}/approve` |
| 10 | POST | `/api/v1/hitl/{decision_id}/reject` |
| 11 | POST | `/api/v1/hitl/{decision_id}/escalate` |
| 12 | POST | `/api/v1/hitl/{decision_id}/modify` |

## Protection Rule

If any Phase 2 modification breaks this baseline:

STOP → diagnose → fix/revert → restore → continue
