from pydantic import BaseModel


class TokenUsage(BaseModel):
    """Token usage metadata for LLM responses. Used by all providers."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OperationalTelemetry(BaseModel):
    """Stage-level timing telemetry. Contract for future observability (Blueprint v1.1)."""
    case_id: str
    stage: str
    duration_ms: float
    timestamp: str


class LLMTelemetry(BaseModel):
    """LLM call telemetry. Contract for future observability (Blueprint v1.1)."""
    provider: str
    model: str
    latency_ms: float
    tokens: TokenUsage
