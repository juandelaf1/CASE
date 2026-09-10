import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, "src")

from case_core.contracts.llm import DecodingParameters, LLMRequest
from case_core.providers.cloud import CloudProvider


def _make_request(mock_id: str = "test") -> LLMRequest:
    return LLMRequest(
        messages=[
            {"role": "system", "content": "You are a test system."},
            {"role": "user", "content": f"[{mock_id}] Test case report"},
        ],
        response_schema={"type": "object", "properties": {"decision": {"type": "string"}}},
        decoding_parameters=DecodingParameters(temperature=0.0, max_tokens=100, top_p=1.0),
        metadata={"case_id": "test-case"},
    )


def _mock_openai_response(content: str, finish_reason: str = "stop") -> dict:
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        "system_fingerprint": "fp_test",
    }


class TestCloudProviderConstruction:
    def test_default_construction(self):
        with patch.dict(os.environ, {"CASE_CLOUD_API_KEY": "test-key"}):
            provider = CloudProvider()
            assert provider.name == "cloud"
            assert provider.model == "gpt-4o-mini"
            assert provider.api_key == "test-key"
            assert provider.base_url == "https://api.openai.com/v1"

    def test_custom_construction(self):
        provider = CloudProvider(
            api_key="custom-key",
            base_url="https://custom.api.com/v1",
            model="custom-model",
            provider_name="custom-cloud",
        )
        assert provider.name == "custom-cloud"
        assert provider.model == "custom-model"
        assert provider.api_key == "custom-key"
        assert provider.base_url == "https://custom.api.com/v1"

    def test_env_vars_override(self):
        with patch.dict(os.environ, {
            "CASE_CLOUD_API_KEY": "env-key",
            "CASE_CLOUD_BASE_URL": "https://env.api.com/v1",
            "CASE_CLOUD_MODEL": "env-model",
            "CASE_CLOUD_PROVIDER": "env-provider",
        }):
            provider = CloudProvider()
            assert provider.api_key == "env-key"
            assert provider.base_url == "https://env.api.com/v1"
            assert provider.model == "env-model"
            assert provider.name == "env-provider"

    def test_implements_llm_provider(self):
        from case_core.ports.llm import LLMProvider
        provider = CloudProvider(api_key="test")
        assert isinstance(provider, LLMProvider)


class TestCloudProviderMissingCredentials:
    @pytest.mark.asyncio
    async def test_missing_api_key_returns_authentication_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CASE_CLOUD_API_KEY", None)
            provider = CloudProvider()
            request = _make_request()
            response = await provider.complete(request)
            assert response.finish_reason == "authentication_error"
            assert response.raw_output == ""
            assert response.parsed is None
            assert "missing_api_key" in response.metadata["error"]

    @pytest.mark.asyncio
    async def test_health_check_false_when_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CASE_CLOUD_API_KEY", None)
            provider = CloudProvider()
            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_get_model_info_none_when_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CASE_CLOUD_API_KEY", None)
            provider = CloudProvider()
            assert await provider.get_model_info() is None


class TestCloudProviderSuccessMapping:
    @pytest.mark.asyncio
    async def test_successful_response_mapping(self):
        decision_json = json.dumps({
            "decision": "approve",
            "reason": "Test reason",
            "urgency": "MEDIUM",
            "confidence": 0.85,
            "evidence_summary": "Test evidence",
        })
        mock_response = _mock_openai_response(decision_json)

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response),
        ))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            request = _make_request()
            response = await provider.complete(request)

        assert response.raw_output == decision_json
        assert response.parsed is not None
        assert response.parsed["decision"] == "approve"
        assert response.usage.prompt_tokens == 50
        assert response.usage.completion_tokens == 30
        assert response.usage.total_tokens == 80
        assert response.finish_reason == "stop"
        assert response.provider == "cloud"
        assert response.model == "gpt-4o-mini"
        assert response.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_response_metadata_fields(self):
        mock_response = _mock_openai_response("{}")
        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response),
        ))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert "id" in response.metadata
        assert "created" in response.metadata
        assert "system_fingerprint" in response.metadata


class TestCloudProviderErrorMapping:
    @pytest.mark.asyncio
    async def test_timeout_returns_timeout(self):
        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.finish_reason == "timeout"
        assert response.raw_output == ""
        assert response.parsed is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_unavailable(self):
        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.finish_reason == "provider_unavailable"
        assert response.raw_output == ""

    @pytest.mark.asyncio
    async def test_401_returns_authentication_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=mock_response)
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.finish_reason == "authentication_error"

    @pytest.mark.asyncio
    async def test_429_returns_rate_limit(self):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429", request=MagicMock(), response=mock_response
        )
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=mock_response)
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.finish_reason == "rate_limit"

    @pytest.mark.asyncio
    async def test_500_returns_provider_unavailable(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_response.json.return_value = {"error": {"message": "Internal error"}}

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=mock_response)
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.finish_reason == "provider_unavailable"

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self):
        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(side_effect=ValueError("unexpected"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.finish_reason == "error"
        assert "unexpected" in response.metadata["error"]


class TestCloudProviderMalformedResponse:
    @pytest.mark.asyncio
    async def test_invalid_json_in_response(self):
        mock_response = _mock_openai_response("this is not json {{{")

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response),
        ))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.raw_output == "this is not json {{{"
        assert response.parsed is None
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_empty_choices_returns_empty(self):
        mock_response = {"choices": [], "usage": {}}

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response),
        ))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.raw_output == ""
        assert response.parsed is None


class TestCloudProviderHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        mock_httpx = MagicMock()
        mock_httpx.get = AsyncMock(return_value=MagicMock(status_code=200))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        mock_httpx = MagicMock()
        mock_httpx.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            assert await provider.health_check() is False


class TestCloudProviderUsageMetadata:
    @pytest.mark.asyncio
    async def test_usage_from_response(self):
        mock_response = _mock_openai_response("{}")
        mock_response["usage"] = {
            "prompt_tokens": 120,
            "completion_tokens": 45,
            "total_tokens": 165,
        }

        mock_httpx = MagicMock()
        mock_httpx.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response),
        ))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
            provider = CloudProvider(api_key="test-key")
            response = await provider.complete(_make_request())

        assert response.usage.prompt_tokens == 120
        assert response.usage.completion_tokens == 45
        assert response.usage.total_tokens == 165

    @pytest.mark.asyncio
    async def test_finish_reason_mapping(self):
        for api_reason, expected in [("stop", "stop"), ("length", "length"), ("content_filter", "content_filter")]:
            mock_response = _mock_openai_response("{}", finish_reason=api_reason)

            mock_httpx = MagicMock()
            mock_httpx.post = AsyncMock(return_value=MagicMock(
                status_code=200,
                raise_for_status=MagicMock(),
                json=MagicMock(return_value=mock_response),
            ))
            mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
            mock_httpx.__aexit__ = AsyncMock(return_value=False)

            with patch("case_core.providers.cloud.httpx.AsyncClient", return_value=mock_httpx):
                provider = CloudProvider(api_key="test-key")
                response = await provider.complete(_make_request())

            assert response.finish_reason == expected, f"Expected {expected} for API reason {api_reason}"


class TestCloudProviderNoCoreCoupling:
    def test_no_core_domain_imports(self):
        import inspect

        from case_core.providers.cloud import CloudProvider

        source = inspect.getsource(CloudProvider)
        assert "from case_core.domain" not in source
        assert "from case_core.application" not in source
        assert "from case_core.contracts.operational_case" not in source

    def test_only_llm_contracts_imports(self):
        import case_core.providers.cloud as mod

        src_lines = []
        for name in dir(mod):
            obj = getattr(mod, name)
            if isinstance(obj, type):
                src_lines.append(str(getattr(obj, "__module__", "")))

        source = "\n".join(src_lines)
        assert "case_core.contracts.llm" in source or "case_core.ports.llm" in source

    def test_provider_module_imports(self):
        from case_core.ports.llm import LLMProvider
        from case_core.providers.cloud import CloudProvider

        assert issubclass(CloudProvider, LLMProvider)
