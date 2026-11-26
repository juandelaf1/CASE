# CASE — Multi-consumer Security Hardening (Cycles 2-3, 2026-11-10)

**Status:** security hardening + persistence isolation primitives implemented; **shared multi-consumer mode remains BLOCKED (fail-closed)** because end-to-end isolation across all write/audit paths and exhaustive route/object-level controls are **not fully demonstrated**.  
**Base:** `v4/portfolio-release@8ba646a8a0dce461d5398816f73f51dd2f1ef642` (local changes uncommitted).

## Cycle 3 progress (implemented, local)
- **ADR:** `docs/adr/ADR-CASE-MC-001-deployment-and-isolation-strategy.md` (A: isolated instances vs B: shared multi-tenant; progressive decision: autonomous/isolated primary, shared multi-tenant only with proven isolation).
- **SecurityContext:** `case_core.contracts.security.SecurityContext` + request propagation from verified identity (`request.state.security_context`) with consumer/tenant/org/scopes/principal/credential status/restrictions/correlation.
- **Persistence schema/migration (SQLite, backward-compatible):** added `consumer_id`, `tenant_id`, `organization_id` columns and indexes to decisions, audit events, cases (and repo audit_events table); explicit autonomous-owner backfill for legacy rows (`local-autonomous`/`local`). No destructive changes.
- **Context-stamped writes / context-filtered reads:** `SQLiteDecisionRepository`, `SQLiteAuditAdapter`, `SQLiteRepository` accept optional `security_context`; when provided, writes stamp verified context and queries filter by `(consumer_id, tenant_id)`; list/count/update/get enforce scoped access.
- **Idempotency store:** `SQLiteIdempotencyStore` with composite key `(consumer_id, tenant_id, operation, idempotency_key)`, request hash, replay/conflict/in-progress handling. Integrated in `/api/v1/evaluate` for strict authenticated contexts.
- **API/engine propagation:** key read/HITL endpoints pass context and return 404 for out-of-context resources; engine accepts/passes `security_context` to decision save and engine audit emission; triage/evaluate thread context into engine execution.
- **Repo-level PoC (evidence):** cross-consumer/tenant invisibility for same IDs (get/list/count/audit), scoped idempotency no collision, replay and payload-conflict detection — **PASSED** (`case_isolation_poc.py`, 2026-11-10).
- **Shared multi-consumer startup gate:** still fail-closed in `shared/prod` when multi-consumer/multi-tenant configured or isolation not demonstrated. **Not enabled.**

## 1. Operational modalities

### 1.1 Autonomous isolated mode (`CASE_SECURITY_MODE=dev`, no credentials)
- **Purpose:** local/autonomous CASE operation, existing integrations and developer workflows.
- **Behavior:** explicit dev mode; open access allowed only when no credentials are configured. Request-declared scopes on `/api/v1/evaluate` are validated for backward compatibility when provided.
- **Use outside local:** **not recommended without explicit controls**. For any non-local/shared exposure, configure credentials and use strict mode (and satisfy isolation requirements).

### 1.2 Strict single-consumer isolated mode (`shared`/`prod` with one authorized consumer/tenant context)
- **Purpose:** isolated deployment serving a single authorized consumer/owner context with fail-closed security.
- **Controls required/enforced:** authenticated credentials, server-derived identity/scopes, `case:evaluate` scope from identity for `/api/v1/evaluate`, tenant/org binding or rejection of mismatched payload context, revoked-consumer rejection, fail-fast startup on missing/unsafe config.
- **Limitation:** underlying persistence/audit/idempotency stores are not tenant-partitioned; safe only as a single authorized consumer/tenant deployment boundary (infrastructure/process isolation outside app not claimed here).

### 1.3 Shared multi-consumer mode
- **Status:** **NOT APT / BLOCKED (fail-closed).** Startup fails in `shared/prod` when multiple consumers or multiple tenant contexts are configured, or when isolation cannot be demonstrated.
- **Enablement criteria (all required, implemented + tested + independently reviewed):** mandatory auth on all business routes, server-verified consumer identity, scopes from authenticated identity, authorized tenant/org context, isolated queries/evaluations/evidence/decisions/audits/events/results, isolated idempotency keys, cross-consumer access protection, concurrent idempotency safety, and negative multi-consumer tests.

## 2. Identity model (server-side)

Configured via `CASE_API_KEY` (single) or `CASE_API_KEYS` (JSON). Identity fields resolved on server:
- `consumer_id` (required identity label)
- `tenant_id` (authorized tenant binding)
- `organization_id` / `organizations` (authorized org context)
- `scopes` (authorization claims)
- `active` (revocation/status; inactive/revoked → 403)
- `restrictions` (extensibility; not fully enforced)

**Rules:** payload-declared scopes/tenant/org do not grant authority in strict mode. Tenant/org in payload must match authorized context or be rejected. Missing tenant binding for a payload-supplied tenant in strict mode is rejected (fail-closed).

## 3. Authorization matrix (endpoint × operation × strict-mode requirement)

| Endpoint | Method | Category | Auth (strict) | Scope/authorization notes | Isolation status |
|---|---|---|---|---|---|
| `/`, `/docs`, `/redoc`, `/docs/oauth2-redirect`, `/openapi.json` | GET | docs/meta | exempt | dev/docs exposure; restrict at ingress in production | N/A |
| `/health` | GET | ops | exempt | no sensitive data intended | N/A |
| `/api/v1/seismic/health` | GET | ops | **authenticated in strict** (not in auth exempt set) | rate-limit exempt configured separately; review if public health needed | N/A |
| `/api/v1/evaluate` | POST | business/write-eval | **required** | `case:evaluate` from server identity; tenant/org binding enforced; recommendation-only | **No cross-consumer isolation proven** (multi-consumer blocked) |
| `/api/v1/triage` | POST | business/write-eval | **required** | scope model to be specialized (currently authenticated identity required by middleware) | **Not isolated by tenant/consumer in storage** |
| `/api/v1/providers` | GET | read | **required** | read scope recommended (future) | global |
| `/domains` | GET | read | **required** | read scope recommended | global/static |
| `/api/v1/cases` | GET | read | **required** | must filter by authorized tenant/consumer when isolation implemented | **Global query (no tenant filter)** |
| `/api/v1/cases/{case_id}` | GET | read | **required** | object-level authz required | **Global by id** |
| `/api/v1/audit/{case_id}` | GET | read/audit | **required** | audit access scope + object/tenant authz required | **Global by case** |
| `/api/v1/hitl/pending` | GET | read/HITL | **required** | HITL scope + tenant isolation required | **Global** |
| `/api/v1/hitl/{decision_id}` | GET | read/HITL | **required** | object-level authz required | **Global by id** |
| `/api/v1/hitl/{decision_id}/*` (under-review/approve/reject/escalate/modify) | POST | write/HITL | **required** | HITL action scopes + actor/tenant authorization required | **Global by id** |
| `/api/v1/comparison` | POST | business/eval | **required** | evaluate/compare scope; data isolation required | **Not isolated** |
| `/api/v1/seismic/events` | GET | read/integration | **required** | read scope; external data fetch | external source (USGS), no tenant data isolation concern in fetch but access should be controlled |

**Fail-closed in strict mode:** middleware requires valid, active credentials for all non-exempt routes. Any newly added business route must not be added to exemptions without explicit security review.

## 4. Persistence and isolation (current state)

- **Stores:** SQLite adapters/repositories (`sqlite_decision_repository.py`, `sqlite_audit.py`, `sqlite_adapter.py`); global DB path/config; no `consumer_id`/`tenant_id` columns observed.
- **Queries:** list/get by case/decision without tenant/consumer constraints.
- **Audit:** events stored without verified identity context enforcement.
- **Idempotency:** `/api/v1/evaluate` accepts/echoes `idempotency_key` but no durable idempotency store/enforcement with composite scoping demonstrated.
- **Conclusion:** **isolation not demonstrated**. Multi-consumer shared mode remains blocked in startup.

## 5. Idempotency target design (required for shared multi-consumer)

- Scope key at minimum by: `consumer_id` + `tenant_id` + `operation/capability` + `idempotency_key` (+ payload hash/version as needed).
- Enforce uniqueness/lookup in persistence (DB constraint/index), not only in-memory/request logic.
- Concurrent retries: same context+payload → consistent result (stored/replayed); same key with incompatible payload → conflict (409/controlled error).
- Prevent cross-consumer/tenant retrieval or collision by construction.

## 6. Audit and traceability target

Each audit/event record should include (when available/authorized): verified `consumer_id`, authorized `tenant_id`/`organization_id`, applied policy/scopes, evidence references, contract/capability version, result/outcome, correlation/request identifiers, timestamp, actor type. Avoid storing secrets and unnecessary PII.

## 7. Precise plan to complete full multi-consumer isolation

1. **Security context propagation:** introduce request-scoped `SecurityContext` (identity, tenant, org, scopes, correlation) passed to application/ports; remove reliance on global unauthenticated context for business operations.
2. **Schema migration:** add `consumer_id`, `tenant_id`, `organization_id` (nullable only for explicit legacy mapping) to cases/decisions/audits/events/results/idempotency tables; backfill via explicit, reviewed mapping (no arbitrary ownership); add indexes and uniqueness constraints for idempotency composite keys.
3. **Port/repository changes:** require `SecurityContext` in read/write methods; enforce tenant/consumer predicates in every query and write; deny by default on missing context in strict mode.
4. **Object-level authorization:** verify resource ownership/tenant on get/update/HITL/audit endpoints (404/403 as appropriate, no existence leakage across tenants).
5. **Idempotency store:** persistent table keyed by `(consumer_id, tenant_id, operation, idempotency_key)` with request/result fingerprint, status, timestamps; transactional handling for concurrency.
6. **Endpoint scope specialization:** define and enforce granular scopes (e.g. `case:evaluate`, `case:triage`, `case:read`, `case:audit:read`, `case:hitl:write`, `case:admin`) mapped from server identity.
7. **Multi-tenant enablement gate:** allow multi-consumer config in `shared/prod` only when a runtime capability flag/config confirms isolation migrations and tests passed (e.g. `CASE_MULTI_CONSUMER_ISOLATION=verified`), otherwise keep fail-closed.
8. **Database hardening (if PostgreSQL):** evaluate RLS policies, least-privilege roles, and constraint-based guarantees with automated tests.
9. **Testing:** negative matrix across all business endpoints, concurrent idempotency, cross-tenant read/write/audit attempts, migration/backfill tests, regression for autonomous/dev mode.
10. **Independent security review:** code/diff review + test evidence before declaring shared multi-consumer APTO.

## 8. Test/verification evidence (cycles 2-3)
- **Integration (no live):** 34 passed (`tests/integration` excl. groq/ollama) after Cycle 3 changes.
- **Security/authz:** 12+ tests covering startup fail-closed, missing/invalid/revoked creds, scope enforcement, tenant/org spoofing, route auth coverage, dev regression, idempotent request handling.
- **Repo isolation PoC:** PASSED — context-stamped storage and filtered access (decisions/audit), cross-tenant invisibility, scoped idempotency replay/conflict/no-collision.
- **Port/compat:** optional `security_context` params added (backward compatible); dev/autonomous flows preserved.

## 9. Gaps remaining (blockers to declare shared multi-consumer APTO)
- **End-to-end write-path coverage:** ReliabilityPipeline audit emissions and any other internal persistence paths must consistently receive/enforce verified `security_context`; decisions/audits created in all flows must be stamped and retrievable only in-context (prove with API-level multi-consumer PoC using isolated DBs/contexts).
- **Exhaustive authz:** per-endpoint scope specialization (read/write/HITL/audit/admin), object-level checks on every resource path, exhaustive negative matrix for all business routes (including `/api/v1/comparison`, seismic, provider/domain/admin as applicable).
- **Migrations:** formal, versioned migration scripts (upgrade/downgrade where feasible) tested on DB copies from previous schema; explicit legacy-to-owner mapping documented/executed (no arbitrary tenant assignment).
- **Idempotency hardening:** persistent enforcement for all relevant operations if needed, concurrent/retry stress tests, incompatible-payload conflict coverage at API level per consumer/tenant.
- **PostgreSQL/RLS:** evaluate and, if justified, implement/test constraints/RLS as defense-in-depth; keep SQLite compatibility for dev.
- **Independent security review:** required before enabling multi-consumer.
- **Observability/ops:** quotas/rate limiting per consumer, tracing/audit enrichment, backup/restore considerations per deployment mode.

## 10. Modality classification (current)
| Modality | Status | Demonstrated | Missing for next level |
|---|---|---|---|
| Autónomo local (dev explícito) | **Apto (local controlado)** | Compatibilidad, tests integración no-live, modo explícito | Controles de exposición si sale de local |
| Instancia autónoma estricta / consumidor aislado único | **Apto con reservas** | Auth fail-closed, identidad/scopes server-side, revocación, anti-spoofing, context stamping/filtering en repos, idempotencia scoped en evaluate, bloqueo multi-consumer | End-to-end context enforcement total, migraciones formales versionadas, revisión independiente, evidencia operativa |
| Multi-consumidor compartido | **NO APTO (bloqueado)** | Gate fail-closed, primitivas de aislamiento parciales | Todos los gaps de §9 demostrados y revisados |
| Producción | **NO APTO** | — | Hardening completo, ops/observabilidad/cumplimiento, evidencia y aprobación humana |