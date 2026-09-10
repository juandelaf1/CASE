from pydantic import BaseModel


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OperationalTelemetry(BaseModel):
    case_id: str
    stage: str
    duration_ms: float
    timestamp: str


class LLMTelemetry(BaseModel):
    provider: str
    model: str
    latency_ms: float
    tokens: TokenUsage
