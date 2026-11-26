"""Security configuration and request identity for CASE API.

Modes:
- dev: local development. Explicit opt-in to open access when no credentials configured.
- shared: fail-closed. Requires authenticated credentials and server-derived scopes/tenant.
- prod: same as shared, plus startup fails on missing essential security config.

Multi-tenant/shared isolation of persistence and idempotency is NOT demonstrated in the
current storage implementation. Shared/prod modes therefore enforce a single-authorized
consumer/tenant context (no cross-tenant data isolation guarantees). Requests implying
a different tenant/consumer context are rejected.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConsumerIdentity:
    consumer_id: str
    tenant_id: str | None = None
    organization_id: str | None = None
    scopes: tuple[str, ...] = field(default_factory=tuple)
    mode: str = "dev"
    active: bool = True
    organizations: tuple[str, ...] = field(default_factory=tuple)
    restrictions: dict[str, Any] = field(default_factory=dict)

    @property
    def scope_set(self) -> set[str]:
        return set(self.scopes)


@dataclass(frozen=True)
class SecurityConfig:
    mode: str
    consumers_by_key_hash: dict[str, ConsumerIdentity]
    dev_open_access: bool
    single_tenant_id: str | None

    @property
    def is_strict(self) -> bool:
        return self.mode in {"shared", "prod"}

    @property
    def has_credentials(self) -> bool:
        return bool(self.consumers_by_key_hash)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _parse_consumers(raw: str) -> dict[str, ConsumerIdentity]:
    """Parse CASE_API_KEYS JSON.

    Supported forms:
    - {"api_key": {"consumer_id": "...", "tenant_id": "...", "scopes": ["case:evaluate"]}}
    - {"api_key": ["case:evaluate"]} (legacy-ish shorthand; consumer_id derived)
    - [{"key":"...","consumer_id":"...","tenant_id":"...","scopes":[...]}]
    """
    consumers: dict[str, ConsumerIdentity] = {}
    if not raw or not raw.strip():
        return consumers
    data = json.loads(raw)

    def add(key: str, spec: Any) -> None:
        if not key:
            return
        if isinstance(spec, list):
            spec = {"scopes": spec}
        if not isinstance(spec, dict):
            spec = {}
        consumer_id = str(spec.get("consumer_id") or _hash_key(key)[:12])
        tenant_id = spec.get("tenant_id")
        org_id = spec.get("organization_id")
        scopes = spec.get("scopes") or []
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",") if s.strip()]
        scopes_t = tuple(str(s) for s in scopes)
        organizations = spec.get("organizations") or ([] if org_id is None else [org_id])
        if isinstance(organizations, str):
            organizations = [o.strip() for o in organizations.split(",") if o.strip()]
        organizations_t = tuple(str(o) for o in organizations)
        active = bool(spec.get("active", True))
        restrictions = spec.get("restrictions") or {}
        if not isinstance(restrictions, dict):
            restrictions = {}
        identity = ConsumerIdentity(
            consumer_id=consumer_id,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            organization_id=str(org_id) if org_id is not None else None,
            scopes=scopes_t,
            active=active,
            organizations=organizations_t,
            restrictions=restrictions,
        )
        consumers[_hash_key(key)] = identity

    if isinstance(data, dict):
        for k, v in data.items():
            add(str(k), v)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                add(str(item.get("key") or item.get("api_key") or ""), item)
    return consumers


def load_security_config(env: dict[str, str] | None = None) -> SecurityConfig:
    e = os.environ if env is None else env
    mode = (e.get("CASE_SECURITY_MODE") or "dev").strip().lower()
    if mode not in {"dev", "shared", "prod"}:
        mode = "dev"

    consumers = _parse_consumers(e.get("CASE_API_KEYS", ""))
    # Backward-compatible single key: CASE_API_KEY grants case:evaluate (and broad dev use)
    single_key = (e.get("CASE_API_KEY") or "").strip()
    if single_key and _hash_key(single_key) not in consumers:
        scopes = tuple(
            s.strip()
            for s in (e.get("CASE_API_SCOPES") or "case:evaluate").split(",")
            if s.strip()
        ) or ("case:evaluate",)
        consumers[_hash_key(single_key)] = ConsumerIdentity(
            consumer_id=(e.get("CASE_CONSUMER_ID") or "default-consumer"),
            tenant_id=e.get("CASE_TENANT_ID") or None,
            organization_id=e.get("CASE_ORGANIZATION_ID") or None,
            scopes=scopes,
        )

    tenant_ids = {c.tenant_id for c in consumers.values() if c.tenant_id}
    single_tenant_id = next(iter(tenant_ids)) if len(tenant_ids) == 1 else (None if not tenant_ids else "__multiple__")

    # Explicit dev open access allowed only in dev mode without credentials
    dev_open_access = mode == "dev" and not consumers

    if mode in {"shared", "prod"} and not consumers:
        raise RuntimeError(
            f"CASE_SECURITY_MODE={mode} requires credentials (CASE_API_KEYS or CASE_API_KEY). "
            "Refusing to start in open/shared mode."
        )

    # Persistence/idempotency isolation not demonstrated: prevent multi-consumer/multi-tenant in strict modes
    if mode in {"shared", "prod"}:
        if len(consumers) > 1:
            raise RuntimeError(
                f"CASE_SECURITY_MODE={mode} with multiple consumers is not supported: "
                "tenant/consumer isolation of persistence, audit, and idempotency is not demonstrated. "
                "Configure a single authorized consumer/tenant context."
            )
        if single_tenant_id == "__multiple__":
            raise RuntimeError("Multiple tenant contexts configured; isolation not demonstrated.")

    # Re-bind mode into identities for convenience
    consumers = {
        h: ConsumerIdentity(
            i.consumer_id, i.tenant_id, i.organization_id, i.scopes, mode, i.active, i.organizations, i.restrictions
        )
        for h, i in consumers.items()
    }

    return SecurityConfig(
        mode=mode,
        consumers_by_key_hash=consumers,
        dev_open_access=dev_open_access,
        single_tenant_id=None if single_tenant_id == "__multiple__" else single_tenant_id,
    )
