# case.evaluate Contract (v0.1-draft)

> Boundary contract for consumer-agnostic decision evaluation through CASE.
> Status: **draft**, implementation-aligned as of 2026-11-13.

## Purpose

`case.evaluate` is the HTTP boundary for external consumers (Poolar, dashboards, other apps) to request a CASE decision without coupling to CASE internals. CASE core remains domain/provider agnostic; consumers adapt to this contract.

## Endpoint

- `POST /api/v1/evaluate`
- Router: `src/case_api/api/v1/routers/evaluate.py`
- Schemas/exports compat: `case_api.api.v1.app` reexports `EvaluateEnvelopeRequest`, `EvaluatePayload`, `evaluate_case`.

## Request Envelope

```json
{
  "contract_version": "case-eval/v0.1-draft",
  "capability_id": "case.evaluate",
  "correlation_id": "string",
  "idempotency_key": "string",
  "data_status": "synthetic|real|unknown",
  "payload": {
    "domain": "logistics|seismic|...",
    "summary": "string",
    "urgency": "LOW|MEDIUM|HIGH|CRITICAL",
    "evidence": [{"id":"...","type":"text|metric|file|...","content":"...","source":"...","confidence":0.0}],
    "provider": "optional-provider-name"
  }
}
```

### Semantics
- `contract_version`: required; currently `case-eval/v0.1-draft`. Unsupported versions return contract error.
- `capability_id`: must be `case.evaluate`.
- `correlation_id`: caller-provided trace id; echoed/propagated where possible.
- `idempotency_key`: required in strict/shared modes for replay-safe execution semantics.
- `data_status`: provenance marker; does not change core decision logic.
- `payload.domain`: must be a registered CASE domain.
- `payload.provider`: optional; must pass provider validation when present.

## Response Envelope

Success/failure are returned in a normalized envelope:

```json
{
  "contract_version": "case-eval/v0.1-draft",
  "capability_id": "case.evaluate",
  "correlation_id": "...",
  "status": "ok|error",
  "result": {
    "case_ref": "...",
    "decision_id": "...",
    "operation_id": "...",
    "recommendation": "...",
    "confidence": 0.0
  },
  "error": null
}
```

On error, `status="error"` and `error` contains structured detail (`code`, `message`, details as applicable).

## Security / Reliability

- AuthZ/scopes enforced in strict mode (`case:evaluate` / admin scope as configured).
- Idempotency: in `shared/prod` security modes, idempotent replay/conflict behavior is handled by SQLite idempotency store.
- Correlation ID propagated through request context and audit where available.
- Fault hooks may be used in tests for integrity/recovery scenarios.

## Versioning & Compatibility

- **Current version:** `case-eval/v0.1-draft` (implementation-aligned, draft).
- **Supported versions:** server accepts declared supported versions; unsupported versions return `CONTRACT_UNSUPPORTED`.
- **Additive changes:** allowed within a version (new optional fields). Consumers must ignore unknown fields.
- **Breaking changes:** require a new `contract_version` (e.g. `case-eval/v1.0`). Old versions may be supported during a deprecation window.
- **Deprecation:** announce in docs/changelog, keep compatibility window, then remove with major release note.
- **Stability target:** promote to `case-eval/v1.0` when at least one external consumer (e.g. Poolar) validates the contract in a real slice and the envelope is frozen.

## Consumer Integration Rules

- CASE core must not gain consumer-specific branches; consumer adapters map into this contract.
- Consumers own mapping from their domain objects to `case.evaluate` payload.
- Idempotency key and correlation id are consumer responsibilities to pass; CASE enforces replay/conflict semantics in strict modes.
- Poolar integration should live in Poolar as an adapter/client calling this contract.

## Test Coverage

Relevant tests include:
- `tests/integration/test_evaluate_api.py`
- `tests/integration/test_evaluate_contract.py`
- `tests/integration/test_evaluate_security.py`
- `tests/integration/test_idempotency_recovery.py`
- `tests/integration/test_fault_injection_ag.py`
