import json
import time
from typing import Any

import httpx

from case_core.contracts.llm import LLMRequest, LLMResponse
from case_core.contracts.telemetry import TokenUsage
from case_core.ports.llm import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.time()

        ollama_messages = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in request.messages
        ]

        payload = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": request.decoding_parameters.temperature,
                "num_predict": request.decoding_parameters.max_tokens,
                "top_p": request.decoding_parameters.top_p,
            },
            "format": request.response_schema,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
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
            if e.response.status_code == 429:
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

        raw_output = data.get("message", {}).get("content", "")
        parsed = None
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            pass

        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        usage = TokenUsage(
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
            total_tokens=prompt_eval_count + eval_count,
        )

        finish_reason = "stop"
        if data.get("done") is False:
            finish_reason = "length"

        return LLMResponse(
            raw_output=raw_output,
            parsed=parsed,
            usage=usage,
            model=self._model,
            provider=self.name,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            metadata={
                "total_duration_ns": data.get("total_duration", 0),
                "eval_duration_ns": eval_duration_ns,
                "done": data.get("done", False),
            },
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def get_model_info(self) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/show",
                    json={"name": self._model},
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception:
            return None
