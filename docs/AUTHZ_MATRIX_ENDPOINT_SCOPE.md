# CASE — Authz Matrix: Endpoint × Operation × Scope × Context

**Status:** design + partial enforcement in strict mode (Cycle 3). Multi-consumer shared **blocked**.

## Modes
- **dev (explicit, no credentials):** open access only when no credentials configured; backward-compatible for local/autonomous flows.
- **shared/prod (strict):** authenticated identity required for non-exempt routes; scopes derived from server identity; tenant/org bound; fail-closed.

## Exempt routes
| Route | Reason |
|---|---|
| `/`, `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json` | API documentation/metadata |
| `/health` | Operational health (review ingress in production) |

**Note:** `/api/v1/seismic/health` is **not** in auth exempt set (treated as business/operational route requiring auth in strict mode unless explicitly justified).

## Proposed scope taxonomy (server-derived)
| Scope | Purpose |
|---|---|
| `case:evaluate` | `/api/v1/evaluate` capability (recommendation-only) |
| `case:triage` | `/api/v1/triage` evaluation/triage operations |
| `case:read` | Read cases/decisions listings and summaries |
| `case:decision:read` | Read individual decision details |
| `case:audit:read` | Read audit events |
| `case:hitl:read` | Read HITL queue/items |
| `case:hitl:write` | HITL actions (approve/reject/escalate/modify/under-review) |
| `case:compare` | Comparison operations |
| `case:admin` | Administrative operations (minimal, review per deployment) |

## Matrix (current enforcement state)
| Endpoint | Method | Resource/Op | Strict auth | Scope check | Object-level | Tenant filter | Audit | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| `/api/v1/evaluate` | POST | capability evaluate (recommendation) | **enforced** | **enforced** (`case:evaluate`) | context-bound + payload tenant/org validated | **enforced** (identity-bound) | event emitted (adapter) | Idempotency scoped in strict mode |
| `/api/v1/triage` | POST | triage/decision create | **enforced** | **enforced (strict)** (`case:triage`/`case:evaluate`/`case:admin`) | context propagated to engine/repos | **enforced via repos when context present** | via engine/pipeline | Decisions/audits stamped/filtered when context available |
| `/api/v1/cases` | GET | list decisions/cases | **enforced** | **enforced (strict)** (`case:read`/`case:admin`) | list filtered by context | **enforced** | — | Returns only authorized context |
| `/api/v1/cases/{case_id}` | GET | get case+decision+audit | **enforced** | **enforced (strict)** (`case:read`/`case:decision:read`/`case:admin`) | 404 if not in context | **enforced** | — | No cross-tenant existence leakage (404) |
| `/api/v1/audit/{case_id}` | GET | audit events | **enforced** | **enforced (strict)** (`case:audit:read`/`case:read`/`case:admin`) | filtered by context | **enforced** | — | Isolated by context |
| `/api/v1/hitl/pending` | GET | HITL queue | **enforced** | **enforced (strict)** (`case:hitl:read`/`case:read`/`case:admin`) | filtered by context | **enforced** | — | Scoped listing |
| `/api/v1/hitl/{decision_id}` | GET | HITL decision detail | **enforced** | **enforced (strict)** (`case:hitl:read`/`case:decision:read`/`case:read`/`case:admin`) | 404 if not in context | **enforced** | — | Object-level check |
| `/api/v1/hitl/{decision_id}/under-review` | POST | HITL action | **enforced** | **enforced (strict)** (`case:hitl:write`/`case:admin`) | 404 + lifecycle check | **enforced** | **emitted** with context | Updates isolated by context |
| `/api/v1/hitl/{decision_id}/approve` | POST | HITL action | **enforced** | **enforced (strict)** (`case:hitl:write`/`case:admin`) | 404 + lifecycle check | **enforced** | **emitted** with context | Isolated |
| `/api/v1/hitl/{decision_id}/reject` | POST | HITL action | **enforced** | **enforced (strict)** (`case:hitl:write`/`case:admin`) | 404 + lifecycle check | **enforced** | **emitted** with context | Isolated |
| `/api/v1/hitl/{decision_id}/escalate` | POST | HITL action | **enforced** | **enforced (strict)** (`case:hitl:write`/`case:admin`) | 404 + lifecycle check | **enforced** | **emitted** with context | Isolated |
| `/api/v1/hitl/{decision_id}/modify` | POST | HITL action | **enforced** | **enforced (strict)** (`case:hitl:write`/`case:admin`) | 404 + lifecycle check | **enforced** | **emitted** with context | Isolated |
| `/api/v1/comparison` | POST | comparison | **enforced** | **enforced (strict)** (`case:compare`/`case:triage`/`case:evaluate`/`case:admin`) | context propagated to engine/repos | **enforced via repos when context present** | via engine/pipeline | Per-provider decisions stamped by context |
| `/domains` | GET | metadata | **enforced** | **enforced (strict)** (`case:read`/`case:admin`) | N/A (static) | N/A | — | Low sensitivity |
| `/api/v1/providers` | GET | metadata | **enforced** | **enforced (strict)** (`case:read`/`case:admin`) | N/A | N/A | — | Low sensitivity |
| `/api/v1/seismic/events` | GET | integration read | **enforced** | **enforced (strict)** (`case:read`/`case:admin`) | External fetch; access controlled | N/A | — | USGS fetch, no tenant data persisted |
| `/api/v1/seismic/health` | GET | ops | **enforced** (not exempt) | **enforced (strict)** (`case:read`/`case:admin`) | N/A | N/A | — | Consider exemption/ops scope if justified |

**Status:** auth required on non-exempt routes in strict mode; scope checks enforced in strict mode for listed routes (dev remains backward-compatible/open when uncredentialed).

- Negative coverage **401/403 sistemática** verificada para todas las rutas de negocio protegidas en `tests/integration/test_strict_authz_matrix.py` (2026-11-11).
- **Efectos de denegación (sin credenciales, scope insuficiente, credenciales inválidas, consumidor revocado):** verificado que no se crean decisiones/auditorías/registros de idempotencia en DB aislada para las 17 rutas en `tests/integration/test_denial_effects.py` (2026-11-11).
- **Integridad E2E estricta (parcial):** replay/conflicto/in-progress de `/api/v1/evaluate` sin duplicación de decisiones; acceso/mutación HITL entre contextos aislados sin efectos sobre objetos ajenos; transición HITL inválida sin cambio de estado ni evento HITL de negocio (`tests/integration/test_strict_integrity_e2e.py`, 2026-11-11).

Cobertura **aún no exhaustiva** en efectos persistentes/auditoría técnica por todas las variantes de error, fault injection de fallos parciales, recuperación, concurrencia multi-proceso robusta, y revisión independiente; shared multi-consumer permanece **bloqueado**.
