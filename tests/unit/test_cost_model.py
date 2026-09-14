import sys

sys.path.insert(0, "src")

from case_core.contracts.telemetry import TokenUsage
from case_core.evaluation.cost import CostModel, PricingConfig


class TestCostModelDefaults:
    def test_mock_provider_free(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = cm.estimate("mock", "mock", usage)
        assert result.is_free is True
        assert result.total_cost == 0.0

    def test_ollama_provider_free(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = cm.estimate("ollama", "llama3.2", usage)
        assert result.is_free is True
        assert result.total_cost == 0.0

    def test_cloud_gpt4o_mini(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        result = cm.estimate("cloud", "gpt-4o-mini", usage)
        assert result.is_free is False
        assert result.prompt_cost == 1000 * 0.00000015
        assert result.completion_cost == 500 * 0.0000006
        assert result.total_cost == result.prompt_cost + result.completion_cost

    def test_cloud_gpt4o(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        result = cm.estimate("cloud", "gpt-4o", usage)
        assert result.is_free is False
        assert result.total_cost > 0

    def test_unknown_provider_treated_as_free(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = cm.estimate("unknown", "model", usage)
        assert result.is_free is True
        assert result.total_cost == 0.0


class TestCostModelCustom:
    def test_register_custom_pricing(self):
        cm = CostModel()
        custom = PricingConfig(
            provider="custom",
            model="custom-model",
            prompt_price_per_token=0.000001,
            completion_price_per_token=0.000002,
        )
        cm.register_pricing(custom)
        usage = TokenUsage(prompt_tokens=100, completion_tokens=100, total_tokens=200)
        result = cm.estimate("custom", "custom-model", usage)
        assert result.is_free is False
        assert result.prompt_cost == 100 * 0.000001
        assert result.completion_cost == 100 * 0.000002

    def test_get_pricing_returns_config(self):
        cm = CostModel()
        config = cm.get_pricing("mock", "mock")
        assert config is not None
        assert config.is_free is True

    def test_get_pricing_unknown_returns_none(self):
        cm = CostModel()
        config = cm.get_pricing("nonexistent", "model")
        assert config is None


class TestCostModelWithCustomPricing:
    def test_custom_init_pricing(self):
        custom = [
            PricingConfig(provider="a", model="b", prompt_price_per_token=0.001, completion_price_per_token=0.002),
        ]
        cm = CostModel(pricing=custom)
        usage = TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
        result = cm.estimate("a", "b", usage)
        assert result.total_cost == 10 * 0.001 + 10 * 0.002


class TestCostEstimateContract:
    def test_fields_complete(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = cm.estimate("mock", "mock", usage)
        assert hasattr(result, "provider")
        assert hasattr(result, "model")
        assert hasattr(result, "prompt_tokens")
        assert hasattr(result, "completion_tokens")
        assert hasattr(result, "total_tokens")
        assert hasattr(result, "prompt_cost")
        assert hasattr(result, "completion_cost")
        assert hasattr(result, "total_cost")
        assert hasattr(result, "currency")
        assert hasattr(result, "is_free")
        assert hasattr(result, "is_estimated")

    def test_is_estimated_for_paid(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = cm.estimate("cloud", "gpt-4o-mini", usage)
        assert result.is_estimated is True

    def test_is_not_estimated_for_free(self):
        cm = CostModel()
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = cm.estimate("mock", "mock", usage)
        assert result.is_estimated is False
