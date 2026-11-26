# ADR-CASE-MC-001 — Deployment and Isolation Strategy (Autonomous-first, Multi-tenant-capable)

- **Status:** Proposed (2026-11-10)
- **Deciders:** CASE maintainers / ecosystem governance
- **Context:** CASE must serve as a reusable transversal evaluator for different consumers/organizations without mixing identities, permissions, data, policies, or audits, while remaining operable for communities with limited resources.

## Alternatives considered

### A — Isolated instances (one CASE per consumer/organization/context)
| Dimension | Assessment |
|---|---|
| Security | **Strong** isolation by deployment boundary (separate DB/credentials/config/runtime). Low risk of cross-tenant data leakage in application logic. |
| Complexity | **Low** application complexity; no shared-tenant data model required initially. |
| Cost/operation | Higher per-tenant operational overhead if many tenants; simpler per instance. Good fit for few/sovereign deployments and self-hosting. |
| Scalability | Scales by adding instances; less efficient for many small tenants. |
| Backups/recovery | **Simple and safe** per tenant (independent restore). |
| Maintenance | More instances to patch/monitor; predictable blast radius. |
| Self-hosting/low resources | **Favorable** for communities needing autonomy/control with modest footprint. |

### B — Shared multi-tenant instance
| Dimension | Assessment |
|---|---|
| Security | Requires **complete, proven** app+DB+audit+idempotency isolation, exhaustive authz, and strong testing; higher leakage risk if flawed. |
| Complexity | **High** (schema, migrations, SecurityContext propagation, object-level authz, RLS/constraints, ops). |
| Cost/operation | Efficient at higher tenant density; shared infra. |
| Scalability | Better density; requires quotas/rate limits/observability maturity. |
| Backups/recovery | More complex (tenant-scoped restore/export concerns). |
| Maintenance | Centralized updates but higher criticality. |
| Self-hosting/low resources | Possible but harder to operate safely; overkill for small/autonomous deployments. |

## Decision (progressive, security-first)
1. **Primary supported path now:** **Autonomous/isolated instances** (or strict single-consumer isolated deployments) as the default, low-risk, self-hostable mode.
2. **Evolution path:** **Shared multi-tenant** is an **opt-in capability** only when full isolation is implemented, migrated safely, negatively/concurrently tested, and independently reviewed. Until then, shared multi-consumer remains **fail-closed/blocked**.
3. **No excuse principle:** isolated-instance support does **not** remove the requirement to implement internal isolation primitives (SecurityContext, tenant/consumer-stamped storage, scoped queries, idempotency scoping, object-level authz) so CASE is correct by construction and can evolve safely.

## Consequences
- Immediate focus: harden identity/authz and make storage/context isolation real for a single authorized owner context; keep multi-consumer blocked.
- Future: enable multi-tenant only behind explicit, evidence-backed gate (e.g. verified isolation config/flag + migration/tests/review).
- Documentation must distinguish: autonomous local, strict autonomous instance, single-consumer isolated, multi-consumer shared, production.

## Related
- `docs/MULTICONSUMER_SECURITY_HARDENING.md`
- ADR-005 (identity/delegation), ADR-006 (CASE multi-consumer) in ecosystem governance.