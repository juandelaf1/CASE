from __future__ import annotations

from pydantic import BaseModel

from case_core.contracts.telemetry import TokenUsage


class PricingConfig(BaseModel):
    """Per-provider/model pricing configuration. All values in USD per token."""
    provider: str
    model: str
    prompt_price_per_token: float = 0.0
    completion_price_per_token: float = 0.0
    currency: str = "USD"
    is_free: bool = False


class CostEstimate(BaseModel):
    """Estimated cost for a single LLM call."""
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float
    currency: str
    is_free: bool
    is_estimated: bool = True


DEFAULT_PRICING: list[PricingConfig] = [
    PricingConfig(
        provider="mock",
        model="mock",
        is_free=True,
    ),
    PricingConfig(
        provider="ollama",
        model="llama3.2",
        is_free=True,
    ),
    PricingConfig(
        provider="groq",
        model="qwen/qwen3.8-27b",
        prompt_price_per_token=0.0000002,
        completion_price_per_token=0.0000006,
    ),
    PricingConfig(
        provider="cloud",
        model="gpt-4o-mini",
        prompt_price_per_token=0.00000015,
        completion_price_per_token=0.0000006,
    ),
    PricingConfig(
        provider="cloud",
        model="gpt-4o",
        prompt_price_per_token=0.0000025,
        completion_price_per_token=0.00001,
    ),
]


class CostModel:
    """Provider-neutral cost estimation from token usage."""

    def __init__(self, pricing: list[PricingConfig] | None = None) -> None:
        self._pricing = pricing or DEFAULT_PRICING
        self._by_key: dict[tuple[str, str], PricingConfig] = {}
        for p in self._pricing:
            self._by_key[(p.provider, p.model)] = p

    def get_pricing(self, provider: str, model: str) -> PricingConfig | None:
        return self._by_key.get((provider, model))

    def estimate(
        self,
        provider: str,
        model: str,
        usage: TokenUsage,
    ) -> CostEstimate:
        config = self.get_pricing(provider, model)

        if config is None or config.is_free:
            return CostEstimate(
                provider=provider,
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                prompt_cost=0.0,
                completion_cost=0.0,
                total_cost=0.0,
                currency="USD",
                is_free=True,
                is_estimated=False,
            )

        prompt_cost = usage.prompt_tokens * config.prompt_price_per_token
        completion_cost = usage.completion_tokens * config.completion_price_per_token

        return CostEstimate(
            provider=provider,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            currency=config.currency,
            is_free=False,
            is_estimated=True,
        )

    def register_pricing(self, config: PricingConfig) -> None:
        self._by_key[(config.provider, config.model)] = config
        self._pricing.append(config)
