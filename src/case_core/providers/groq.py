from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from case_core.contracts.llm import LLMRequest, LLMResponse
from case_core.contracts.telemetry import TokenUsage
from case_core.ports.llm import LLMProvider

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(LLMProvider):
    """Groq provider — OpenAI-compatible API with low-latency inference.

    Reuses CloudProvider's HTTP patterns but adds structured output support
    via response_format json_schema when response_schema is provided.

    Environment variables:
        CASE_GROQ_API_KEY: Groq API key
        CASE_GROQ_MODEL: Model identifier (default: llama-3.3-70b-versatile)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("CASE_GROQ_API_KEY", "")
        self._model = model or os.environ.get("CASE_GROQ_MODEL", "llama-3.3-70b-versatile")
        self._base_url = (base_url or os.environ.get("CASE_GROQ_BASE_URL", GROQ_BASE_URL)).rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "groq"

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def base_url(self) -> str:
        return self._base_url

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        messages = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in request.messages
        ]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": request.decoding_parameters.temperature,
            "max_tokens": request.decoding_parameters.max_tokens,
            "top_p": request.decoding_parameters.top_p,
        }

        if request.response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "case_decision",
                    "strict": True,
                    "schema": request.response_schema,
                },
            }
        else:
            payload["response_format"] = {"type": "json_object"}

        return payload

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.time()

        if not self._api_key:
            latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                raw_output="",
                parsed=None,
                usage=TokenUsage(),
                model=self._model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason="authentication_error",
                metadata={
                    "error": "missing_api_key",
                    "message": "CASE_GROQ_API_KEY environment variable not set",
                },
            )

        payload = self._build_payload(request)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                raw_output="",
                parsed=None,
                usage=TokenUsage(),
                model=self._model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason="timeout",
                metadata={"error": "timeout", "base_url": self._base_url},
            )
        except httpx.ConnectError:
            latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                raw_output="",
                parsed=None,
                usage=TokenUsage(),
                model=self._model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason="provider_unavailable",
                metadata={"error": "provider_unavailable", "base_url": self._base_url},
            )
        except httpx.HTTPStatusError as e:
            latency_ms = (time.time() - start) * 1000
            finish_reason = "error"
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", "")
            except Exception:
                pass

            if e.response.status_code == 401:
                finish_reason = "authentication_error"
            elif e.response.status_code == 429:
                finish_reason = "rate_limit"
            elif e.response.status_code >= 500:
                finish_reason = "provider_unavailable"

            return LLMResponse(
                raw_output="",
                parsed=None,
                usage=TokenUsage(),
                model=self._model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason=finish_reason,
                metadata={
                    "error": f"HTTP {e.response.status_code}",
                    "status_code": e.response.status_code,
                    "detail": error_detail,
                },
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                raw_output="",
                parsed=None,
                usage=TokenUsage(),
                model=self._model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason="error",
                metadata={"error": str(e)},
            )

        latency_ms = (time.time() - start) * 1000
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            return LLMResponse(
                raw_output="",
                parsed=None,
                usage=TokenUsage(),
                model=self._model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason="error",
                metadata={"error": "empty_choices", "raw_data": data},
            )

        choice = choices[0]
        raw_output = choice.get("message", {}).get("content", "")

        parsed = None
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            pass

        usage_data = data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        finish_reason_raw = choice.get("finish_reason", "stop")
        finish_reason = "stop"
        if finish_reason_raw == "length":
            finish_reason = "length"
        elif finish_reason_raw == "content_filter":
            finish_reason = "content_filter"

        return LLMResponse(
            raw_output=raw_output,
            parsed=parsed,
            usage=usage,
            model=self._model,
            provider=self.name,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            metadata={
                "id": data.get("id", ""),
                "created": data.get("created", 0),
                "system_fingerprint": data.get("system_fingerprint", ""),
            },
        )

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False
