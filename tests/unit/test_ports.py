import sys

import pytest

sys.path.insert(0, "src")

from case_core.ports.audit import AuditPort
from case_core.ports.domain import DomainPolicy
from case_core.ports.llm import LLMProvider
from case_core.ports.repository import RepositoryPort


class TestLLMProviderInterface:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_interface_methods_exist(self):
        assert hasattr(LLMProvider, "complete")
        assert hasattr(LLMProvider, "health_check")
        assert hasattr(LLMProvider, "name")
        assert hasattr(LLMProvider, "model")


class TestDomainPolicyInterface:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            DomainPolicy()

    def test_interface_methods_exist(self):
        assert hasattr(DomainPolicy, "validate_evidence")
        assert hasattr(DomainPolicy, "classify_urgency")
        assert hasattr(DomainPolicy, "get_domain_context")
        assert hasattr(DomainPolicy, "domain_name")


class TestAuditPortInterface:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AuditPort()

    def test_interface_methods_exist(self):
        assert hasattr(AuditPort, "log_event")
        assert hasattr(AuditPort, "get_events_by_case")


class TestRepositoryPortInterface:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            RepositoryPort()

    def test_interface_methods_exist(self):
        assert hasattr(RepositoryPort, "save_case")
        assert hasattr(RepositoryPort, "get_case")
        assert hasattr(RepositoryPort, "list_cases")
