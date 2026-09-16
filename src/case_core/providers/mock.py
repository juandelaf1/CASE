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
        "decision_rationale": "Step 1: Key facts identified - urban maintenance case with supporting evidence. Step 2: Evidence quality assessed - sufficient for decision. Step 3: Risk evaluated - medium urgency, no critical indicators. Step 4: Action determined - approve for standard processing.",
        "decision_factors": ["Sufficient evidence provided", "Medium urgency level", "Standard processing path"],
        "summary": "Urban maintenance case approved with sufficient evidence for standard processing",
    },
    "TEST-MOCK-02": {
        "decision": "reject",
        "reason": "Insufficient evidence to support claim",
        "urgency": "LOW",
        "confidence": 0.70,
        "evidence_summary": "Only one evidence item, no supporting documentation",
        "decision_rationale": "Step 1: Key facts - single evidence item, no supporting documentation. Step 2: Evidence quality insufficient - cannot validate claim. Step 3: Risk cannot be assessed. Step 4: Action determined - reject due to insufficient evidence.",
        "decision_factors": ["Insufficient evidence", "No supporting documentation", "Cannot validate claim"],
        "summary": "Claim rejected due to insufficient evidence and missing supporting documentation",
    },
    "TEST-MOCK-03": {
        "decision": "escalate",
        "reason": "High urgency case requires human review",
        "urgency": "HIGH",
        "confidence": 0.60,
        "evidence_summary": "Emergency keywords detected, escalation recommended",
        "decision_rationale": "Step 1: Key facts - emergency keywords detected in report. Step 2: Evidence present but urgency indicators high. Step 3: Risk assessed as high - safety concern. Step 4: Action determined - escalate for human review.",
        "decision_factors": ["Emergency keywords detected", "High urgency indicators", "Human review required"],
        "summary": "High urgency case escalated for immediate human review and assessment",
    },
    "TEST-MOCK-04": {
        "decision": "approve",
        "reason": "Critical infrastructure failure confirmed",
        "urgency": "CRITICAL",
        "confidence": 0.92,
        "evidence_summary": "Multiple evidence items support structural failure",
        "decision_rationale": "Step 1: Key facts - infrastructure failure with multiple evidence items. Step 2: Evidence quality high - multiple sources confirm. Step 3: Risk critical but confirmed - approve for immediate action. Step 4: Action determined - approve for emergency response.",
        "decision_factors": ["Multiple evidence sources", "Critical urgency confirmed", "Emergency response warranted"],
        "summary": "Critical infrastructure failure approved for immediate emergency response action",
    },
    "TEST-MOCK-05": {
        "decision": "approve",
        "reason": "Logistics route optimization approved",
        "urgency": "MEDIUM",
        "confidence": 0.78,
        "evidence_summary": "Route data and metrics provided",
        "decision_rationale": "Step 1: Key facts - logistics route optimization request. Step 2: Evidence quality good - route data and metrics available. Step 3: Risk moderate - standard logistics operation. Step 4: Action determined - approve route optimization.",
        "decision_factors": ["Route data available", "Metrics support optimization", "Standard logistics operation"],
        "summary": "Logistics route optimization approved based on available route data",
    },
    "TEST-MOCK-06": {
        "decision": "reject",
        "reason": "Case outside operational scope",
        "urgency": "LOW",
        "confidence": 0.88,
        "evidence_summary": "Domain mismatch detected",
        "decision_rationale": "Step 1: Key facts - case does not match operational domain. Step 2: Evidence shows domain mismatch. Step 3: Risk not applicable - wrong scope. Step 4: Action determined - reject as out of scope.",
        "decision_factors": ["Domain mismatch detected", "Outside operational scope", "Not applicable for processing"],
        "summary": "Case rejected because it falls outside the operational domain scope",
    },
    "TEST-MOCK-07": {
        "decision": "escalate",
        "reason": "Ambiguous case requires specialist review",
        "urgency": "MEDIUM",
        "confidence": 0.55,
        "evidence_summary": "Mixed signals from evidence analysis",
        "decision_rationale": "Step 1: Key facts - ambiguous case with mixed evidence signals. Step 2: Evidence quality uncertain - conflicting indicators. Step 3: Risk unclear - cannot determine with confidence. Step 4: Action determined - escalate for specialist analysis.",
        "decision_factors": ["Ambiguous evidence signals", "Low confidence level", "Specialist analysis needed"],
        "summary": "Ambiguous case escalated for specialist review due to mixed evidence",
    },
    "TEST-MOCK-08": {
        "decision": "approve",
        "reason": "Routine infrastructure inspection completed",
        "urgency": "LOW",
        "confidence": 0.82,
        "evidence_summary": "Standard inspection checklist satisfied",
        "decision_rationale": "Step 1: Key facts - routine infrastructure inspection. Step 2: Evidence quality good - checklist satisfied. Step 3: Risk low - standard procedure. Step 4: Action determined - approve inspection completion.",
        "decision_factors": ["Inspection checklist complete", "Standard procedure followed", "Low risk confirmed"],
        "summary": "Routine infrastructure inspection approved as checklist requirements satisfied",
    },
    "TEST-MOCK-09": {
        "decision": "reject",
        "reason": "Duplicate case detected",
        "urgency": "LOW",
        "confidence": 0.95,
        "evidence_summary": "Case matches existing approved case",
        "decision_rationale": "Step 1: Key facts - case matches previously approved case. Step 2: Evidence confirms duplication. Step 3: Risk none - duplicate already processed. Step 4: Action determined - reject as duplicate.",
        "decision_factors": ["Duplicate case detected", "Already processed", "No new action needed"],
        "summary": "Duplicate case rejected as it matches an existing approved case",
    },
    "TEST-MOCK-10": {
        "decision": "approve",
        "reason": "Urban lighting repair authorized",
        "urgency": "MEDIUM",
        "confidence": 0.80,
        "evidence_summary": "Photo evidence confirms lighting failure",
        "decision_rationale": "Step 1: Key facts - urban lighting failure with photo evidence. Step 2: Evidence quality high - photo confirms issue. Step 3: Risk moderate - lighting affects public safety. Step 4: Action determined - approve repair authorization.",
        "decision_factors": ["Photo evidence available", "Public safety concern", "Repair authorization warranted"],
        "summary": "Urban lighting repair approved based on photo evidence of failure",
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
        "decision_rationale": "short",
        "decision_factors": [],
        "summary": "nine words only here not ten",
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
