# Consumer Integration Guide (CASE)

## Principle
External products (Poolar, dashboards, etc.) consume CASE through versioned contracts. CASE does not embed consumer business logic.

## Recommended pattern
1. **Consumer-side adapter**: map consumer domain objects to `case.evaluate` envelope.
2. **Contract**: use `docs/CASE_EVALUATE_CONTRACT.md` (`case-eval/v0.1-draft`).
3. **Correlation/Idempotency**: generate `correlation_id` and `idempotency_key` on the consumer side; persist them with the consumer operation.
4. **AuthZ**: use scoped API key/consumer identity configured in CASE strict/shared mode.
5. **Error handling**: treat `status=error` and contract errors as explicit; do not silently fallback to autonomous execution.

## Poolar (future slice)
- Location: Poolar repo (adapter/client), not CASE core.
- Slice: one narrow flow (e.g. evaluate a logistics/shipment case) mapped to `case.evaluate`.
- CASE responsibility: stable contract, authz, idempotency, audit, decision result.
- Poolar responsibility: UI/workflow, mapping, when to call CASE, how to present HITL result.

## Do / Don't
- Do: versioned contracts, additive evolution, explicit correlation ids.
- Do: keep consumer adapters thin and tested.
- Don't: import Poolar/domain-consumer logic into `case_core`.
- Don't: bypass CASE decision governance for autonomous execution.

## Supply Chain Disruption slice (synthetic demo)

This slice shows how a Poolar-style consumer can send a disruption event to CASE without embedding Poolar logic in CASE core.

- **Request example:** `docs/examples/supply_chain_disruption_evaluate.request.json`
- **Runnable demo:** `python scripts/demo_supply_chain_disruption_slice.py`
- **Domain:** `supply_chain_disruption` (registered CASE domain pack)
- **Contract:** `case.evaluate` (`case-eval/v0.1-draft`)

### Consumer mapping (Poolar adapter responsibility)

| Poolar/source concept | CASE `case.evaluate` field |
|---|---|
| Operation/correlation id | `correlation_id` |
| Idempotent consumer action | `idempotency_key` |
| Disruption summary | `payload.summary` |
| Normalized urgency | `payload.urgency` |
| Signals/docs/metrics | `payload.evidence[]` |
| Target domain | `payload.domain = "supply_chain_disruption"` |

### Expected governed outcome

CASE returns a contract response with decision/action, confidence, lifecycle hint, and audit-friendly fields. Poolar owns presentation and workflow; CASE owns decision governance.
