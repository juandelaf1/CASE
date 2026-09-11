import json
import re
import time
from typing import Any

from case_core.contracts.llm import LLMRequest, LLMResponse
from case_core.contracts.telemetry import TokenUsage
from case_core.ports.llm import LLMProvider

TEST_MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "TEST-MOCK-01": {
        "decision": "approve",
        "reason": "Standard urban maintenance case with sufficient evidence",
        "urgency": "MEDIUM",
        "confidence": 0.85,
        "evidence_summary": "Report text validated, single evidence item provided",
    },
    "TEST-MOCK-02": {
        "decision": "reject",
        "reason": "Insufficient evidence to support claim",
        "urgency": "LOW",
        "confidence": 0.70,
        "evidence_summary": "Only one evidence item, no supporting documentation",
    },
    "TEST-MOCK-03": {
        "decision": "escalate",
        "reason": "High urgency case requires human review",
        "urgency": "HIGH",
        "confidence": 0.60,
        "evidence_summary": "Emergency keywords detected, escalation recommended",
    },
    "TEST-MOCK-04": {
        "decision": "approve",
        "reason": "Critical infrastructure failure confirmed",
        "urgency": "CRITICAL",
        "confidence": 0.92,
        "evidence_summary": "Multiple evidence items support structural failure",
    },
    "TEST-MOCK-05": {
        "decision": "approve",
        "reason": "Logistics route optimization approved",
        "urgency": "MEDIUM",
        "confidence": 0.78,
        "evidence_summary": "Route data and metrics provided",
    },
    "TEST-MOCK-06": {
        "decision": "reject",
        "reason": "Case outside operational scope",
        "urgency": "LOW",
        "confidence": 0.88,
        "evidence_summary": "Domain mismatch detected",
    },
    "TEST-MOCK-07": {
        "decision": "escalate",
        "reason": "Ambiguous case requires specialist review",
        "urgency": "MEDIUM",
        "confidence": 0.55,
        "evidence_summary": "Mixed signals from evidence analysis",
    },
    "TEST-MOCK-08": {
        "decision": "approve",
        "reason": "Routine infrastructure inspection completed",
        "urgency": "LOW",
        "confidence": 0.82,
        "evidence_summary": "Standard inspection checklist satisfied",
    },
    "TEST-MOCK-09": {
        "decision": "reject",
        "reason": "Duplicate case detected",
        "urgency": "LOW",
        "confidence": 0.95,
        "evidence_summary": "Case matches existing approved case",
    },
    "TEST-MOCK-10": {
        "decision": "approve",
        "reason": "Urban lighting repair authorized",
        "urgency": "MEDIUM",
        "confidence": 0.80,
        "evidence_summary": "Photo evidence confirms lighting failure",
    },
}

TEST_MOCK_INVALID_RESPONSES: dict[str, str | None] = {
    "TEST-MOCK-INVALID-JSON": "this is not valid json {{{",
    "TEST-MOCK-INVALID-SCHEMA": json.dumps({"decision": "approve"}),
    "TEST-MOCK-INVALID-SEMANTIC": json.dumps({
        "decision": "approve",
        "reason": "ok",
        "urgency": "MEDIUM",
        "confidence": 0.8,
        "evidence_summary": "x",
    }),
    "TEST-MOCK-RATE-LIMIT": None,
    "TEST-MOCK-TIMEOUT": None,
}


def _extract_mock_id(request: LLMRequest) -> str | None:
    for msg in request.messages:
        content = msg.get("content", "")
        match = re.search(r"TEST-MOCK-(\d{2}|INVALID-\w+|RATE-LIMIT|TIMEOUT)", content)
        if match:
            return f"TEST-MOCK-{match.group(1)}" if match.group(1).startswith(tuple(str(i) for i in range(10))) else f"TEST-MOCK-{match.group(0).split('-', 2)[-1]}"
    return None


class MockProvider(LLMProvider):
    def __init__(self, default_mock_id: str = "TEST-MOCK-01") -> None:
        self._default_mock_id = default_mock_id

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-v1"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.time()
        mock_id = self._extract_mock_id(request)
        if mock_id and mock_id in TEST_MOCK_INVALID_RESPONSES:
            invalid_response = TEST_MOCK_INVALID_RESPONSES[mock_id]
            if invalid_response is None:
                raise TimeoutError(f"Mock timeout: {mock_id}")

            latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                raw_output=invalid_response,
                parsed=None,
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=self.model,
                provider=self.name,
                latency_ms=latency_ms,
                finish_reason="error",
                metadata={"mock_id": mock_id, "error": "invalid_response"},
            )

        response_data = TEST_MOCK_RESPONSES.get(mock_id or self._default_mock_id, TEST_MOCK_RESPONSES["TEST-MOCK-01"])
        raw_output = json.dumps(response_data)

        prompt_tokens = sum(len(str(m)) for m in request.messages) // 4
        completion_tokens = len(raw_output) // 4
        latency_ms = (time.time() - start) * 1000

        return LLMResponse(
            raw_output=raw_output,
            parsed=response_data,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            model=self.model,
            provider=self.name,
            latency_ms=latency_ms,
            finish_reason="stop",
            metadata={"mock_id": mock_id or self._default_mock_id},
        )

    async def health_check(self) -> bool:
        return True

    def _extract_mock_id(self, request: LLMRequest) -> str | None:
        for msg in request.messages:
            content = msg.get("content", "")
            match = re.search(r"TEST-MOCK-(\d{2}|INVALID-\w+|RATE-LIMIT|TIMEOUT)", content)
            if match:
                return f"TEST-MOCK-{match.group(1)}" if match.group(1).startswith(tuple(str(i) for i in range(10))) else f"TEST-MOCK-{match.group(0).split('-', 2)[-1]}"
        return None
