# case.evaluate Contract (v0.1-draft)

> Boundary contract for consumer-agnostic decision evaluation through CASE.
> Status: **draft, release-ready for consumer validation** (implementation-aligned).

## Purpose

`case.evaluate` is the HTTP boundary for external consumers (Poolar, dashboards, other apps) to request a CASE decision without coupling to CASE internals. CASE core remains domain/provider agnostic; consumers adapt to this contract.

## Endpoint

- `POST /api/v1/evaluate`
- Router: `src/case_api/api/v1/routers/evaluate.py`
- Compat exports: `case_api.api.v1.app` reexports `EvaluateEnvelopeRequest`, `EvaluatePayload`, `evaluate_case`.

## Request Envelope

```json
{
  "contract_version": "case-eval/v0.1-draft",
  "capability_id": "case.evaluate",
  "correlation_id": "string",
  "idempotency_key": "string",
  "data_status": "synthetic|real|unknown",
  "payload": {
    "domain": "logistics|seismic|supply_chain_disruption|...",
    "summary": "string",
    "urgency": "LOW|MEDIUM|HIGH|CRITICAL",
    "evidence": [{"id":"...","type":"text|metric|image|file","content":"...","source":"...","confidence":0.0}],
    "provider": "optional-provider-name"
  }
}
```

### Semantics

- `contract_version`: required; supported versions currently `{"case-eval/v0.1-draft"}`. Unsupported versions return HTTP 400 with `code=CONTRACT_UNSUPPORTED`.
- `capability_id`: must be `case.evaluate` (or empty for legacy compatibility in adapter).
- `correlation_id`: caller-provided trace id; echoed in response.
- `idempotency_key`: required for replay-safe semantics in strict/shared modes.
- `data_status`: provenance marker; does not change core decision logic.
- `payload.domain`: must be a registered CASE domain.
- `payload.provider`: optional; validated when present.

## Response Envelope

```json
{
  "contract_version": "case-eval/v0.1-draft",
  "capability_id": "case.evaluate",
  "correlation_id": "...",
  "idempotency_key": "...",
  "status": "ok|pending_review|error",
  "data_status": "...",
  "provenance": { "provider": "case", "mapping": "..." },
  "result": {
    "decision_type": "recommendation",
    "case_ref": "...",
    "action": "...",
    "urgency": "...",
    "confidence": 0.0,
    "decision_factors": [],
    "evidence_summary": "...",
    "requires_human_review": false,
    "lifecycle_hint": "...",
    "reason": "...",
    "summary": "...",
    "decision_rationale": "...",
    "processing_time_ms": 0.0
  },
  "warnings": [],
  "errors": []
}
```

On evaluation failure mapped by the adapter, `status="error"`, `errors` contains structured detail, and `result.requires_human_review=true`.

## Security / Reliability

- AuthZ/scopes enforced in strict mode (`case:evaluate` / admin scope as configured).
- Idempotency: in `shared/prod` security modes, replay/conflict/recovery handled by SQLite idempotency store.
- Correlation ID propagated through request context and audit where available.
- Fault hooks supported for integrity/recovery testing.

## Versioning & Compatibility

- **Current supported:** `case-eval/v0.1-draft`.
- **Validation:** unsupported `contract_version` -> HTTP 400 `CONTRACT_UNSUPPORTED`.
- **Additive within version:** new optional fields may be added; consumers must ignore unknown fields.
- **Breaking changes:** require new `contract_version` (e.g. `case-eval/v1.0`). Old supported versions may coexist during a deprecation window.
- **Deprecation:** announce in docs/changelog, keep compatibility window, remove with major release note.
- **v1.0 promotion criteria:** at least one external consumer (e.g. Poolar) validates a real/synthetic slice, envelope fields frozen, and contract tests pass in CI.

## Consumer Integration Rules

- CASE core must not gain consumer-specific branches; consumer adapters map into this contract.
- Consumers own mapping from their domain objects to `case.evaluate` payload.
- Idempotency key and correlation id are consumer responsibilities; CASE enforces replay/conflict semantics in strict modes.
- Poolar integration should live in Poolar as an adapter/client calling this contract.

## Test Coverage

- `tests/integration/test_evaluate_api.py`
- `tests/integration/test_evaluate_contract.py`
- `tests/integration/test_evaluate_security.py`
- `tests/integration/test_idempotency_recovery.py`
- `tests/integration/test_fault_injection_ag.py`
- `scripts/demo_supply_chain_disruption_slice.py` (synthetic consumer slice)
