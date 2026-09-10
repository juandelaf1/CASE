from typing import Any

from pydantic import BaseModel, Field

from case_core.contracts.telemetry import TokenUsage


class DecodingParameters(BaseModel):
    temperature: float = 0.0
    max_tokens: int = 1024
    top_p: float = 1.0
    stop: list[str] = Field(default_factory=list)


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    response_schema: dict[str, Any]
    decoding_parameters: DecodingParameters
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    raw_output: str
    parsed: dict[str, Any] | None = None
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: float
    finish_reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)
