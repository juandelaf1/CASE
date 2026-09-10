from abc import ABC, abstractmethod

from case_core.contracts.llm import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Port: interface for LLM providers (Mock, Ollama, Cloud)."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        ...

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
