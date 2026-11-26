"""Security context for authenticated, authorized request execution.

This context is created by the API/auth layer after successful authentication and
must be treated as server-verified. Domain/application/persistence layers must not
construct or elevate identity from untrusted payload data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SecurityContext:
    consumer_id: str
    tenant_id: str | None = None
    organization_id: str | None = None
    organizations: tuple[str, ...] = field(default_factory=tuple)
    scopes: tuple[str, ...] = field(default_factory=tuple)
    principal_id: str | None = None
    credential_status: str = "active"
    restrictions: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    mode: str = "dev"

    @property
    def scope_set(self) -> set[str]:
        return set(self.scopes)

    @property
    def storage_consumer_id(self) -> str:
        return self.consumer_id or "local-autonomous"

    @property
    def storage_tenant_id(self) -> str:
        return self.tenant_id or "local"

    @property
    def storage_organization_id(self) -> str:
        return self.organization_id or ""

    def can_access_tenant(self, tenant_id: str | None) -> bool:
        if tenant_id is None or tenant_id == "":
            return self.storage_tenant_id in {"", "local"} or self.mode == "dev"
        return tenant_id == self.storage_tenant_id

    def can_access_consumer(self, consumer_id: str | None) -> bool:
        if consumer_id is None or consumer_id == "":
            return self.storage_consumer_id in {"", "local-autonomous"} or self.mode == "dev"
        return consumer_id == self.storage_consumer_id


LOCAL_AUTONOMOUS_CONTEXT = SecurityContext(
    consumer_id="local-autonomous",
    tenant_id="local",
    mode="dev",
    credential_status="active",
)
