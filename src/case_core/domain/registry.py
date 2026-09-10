
from case_core.ports.domain import DomainPolicy


class DomainRegistry:
    """Registry for domain policies. Configuration-based, no hardcoded core logic."""

    def __init__(self) -> None:
        self._policies: dict[str, DomainPolicy] = {}

    def register(self, policy: DomainPolicy) -> None:
        self._policies[policy.domain_name] = policy

    def get(self, domain_name: str) -> DomainPolicy | None:
        return self._policies.get(domain_name)

    def list_domains(self) -> list[str]:
        return list(self._policies.keys())

    def validate_domain(self, domain_name: str) -> bool:
        return domain_name in self._policies
