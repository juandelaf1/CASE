# ruff: noqa: T201
"""Operator tool for CASE idempotency reconciliation (SQLite, local/controlled use).

Safe by default:
- Lists stale `in_progress` records and marks them `recovery_required` (fail-closed).
- Does NOT release/delete records for re-execution and does NOT fabricate completed responses.
- Evidence-based completion recovers ONLY from verified persisted evidence in the idempotency record
  (no operator-supplied response content).

Usage examples:
  python scripts/reconcile_idempotency.py --db case_audit.db --list-stale --older-than-seconds 300
  python scripts/reconcile_idempotency.py --db case_audit.db --mark-recovery-required --older-than-seconds 300 --actor ops@example
  python scripts/reconcile_idempotency.py --db case_audit.db --inspect --consumer c1 --tenant t1 --key idem-1
  python scripts/reconcile_idempotency.py --db case_audit.db --complete-from-evidence --consumer c1 --tenant t1 --key idem-1 --actor ops@example --note "verified persisted result"

Do NOT run on production/shared databases without backup and authorization.
"""

from __future__ import annotations

import argparse
import json
import sys

# Allow running from repo root without installation
sys.path.insert(0, "src")

from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path containing idempotency_keys")
    ap.add_argument("--list-stale", action="store_true")
    ap.add_argument("--mark-recovery-required", action="store_true")
    ap.add_argument("--complete", action="store_true", help="DISABLED: unverified completion is not permitted")
    ap.add_argument("--complete-from-evidence", action="store_true", help="Complete from verified persisted evidence in record (no operator response)")
    ap.add_argument("--inspect", action="store_true", help="Inspect a specific idempotency record by scoped key")
    ap.add_argument("--older-than-seconds", type=int, default=300)
    ap.add_argument("--actor", default="operator")
    ap.add_argument("--note", default="")
    ap.add_argument("--consumer")
    ap.add_argument("--tenant")
    ap.add_argument("--operation", default="case.evaluate")
    ap.add_argument("--key", dest="idempotency_key")
    ap.add_argument("--response-json", dest="response_json")
    ap.add_argument("--expected-status", default="recovery_required")
    ap.add_argument("--status-code", type=int, default=200)
    args = ap.parse_args()

    store = SQLiteIdempotencyStore(args.db)

    if args.inspect:
        if not (args.consumer and args.tenant and args.idempotency_key):
            raise SystemExit("--inspect requires --consumer, --tenant, --key")
        rec = store.get_by_key(args.consumer, args.tenant, args.operation, args.idempotency_key)
        print(json.dumps({"record": rec}, indent=2, default=str))  # noqa: T201
        return 0 if rec else 2

    if args.complete_from_evidence:
        if not (args.consumer and args.tenant and args.idempotency_key):
            raise SystemExit("--complete-from-evidence requires --consumer, --tenant, --key")
        ok, reason = store.complete_reconciled_from_evidence(
            args.consumer,
            args.tenant,
            args.operation,
            args.idempotency_key,
            actor=args.actor,
            note=args.note or "evidence-based recovery",
            expected_status=args.expected_status or None,
        )
        print(json.dumps({"ok": ok, "reason": reason, "consumer_id": args.consumer, "tenant_id": args.tenant, "idempotency_key": args.idempotency_key}, indent=2))  # noqa: T201
        return 0 if ok else 3

    if args.list_stale or (not args.mark_recovery_required and not args.complete):
        stale = store.list_stale_in_progress(args.older_than_seconds)
        print(json.dumps({"stale_in_progress": stale, "count": len(stale)}, indent=2, default=str))  # noqa: T201
        if not args.mark_recovery_required and not args.complete:
            return 0

    if args.mark_recovery_required:
        stale = store.list_stale_in_progress(args.older_than_seconds)
        marked = []
        for rec in stale:
            ok = store.mark_recovery_required(
                rec["consumer_id"],
                rec["tenant_id"],
                rec["operation"],
                rec["idempotency_key"],
                actor=args.actor,
                note=args.note or "stale in_progress marked recovery_required (fail-closed)",
            )
            if ok:
                marked.append(rec["idempotency_key"])
        print(json.dumps({"marked_recovery_required": marked, "count": len(marked)}, indent=2))  # noqa: T201

    if args.complete:
        raise SystemExit(
            "Refusing --complete: unverified reconciliation completion is not permitted. "
            "Use --complete-from-evidence to recover only from verified persisted evidence."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
