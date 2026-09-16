"""Controlled ReAct module for CASE.

Implements a deterministic Thought → Action → Observation flow
for pre-processing case analysis before LLM invocation.

Actions are deterministic and controlled:
- CHECK_EVIDENCE: Validates evidence completeness and quality
- CHECK_URGENCY: Analyzes urgency indicators in report text
- CHECK_DOMAIN: Validates domain context and policy requirements

The ReAct trace is a structured, safe artifact intended for demonstration.
Private chain-of-thought from the LLM is never exposed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from case_core.contracts.evidence import EvidenceItem as EvidenceItem
from case_core.contracts.operational_case import OperationalCase


@dataclass
class ReActStep:
    step_number: int
    action: str
    observation: str


@dataclass
class ReActTrace:
    steps: list[ReActStep] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [
                {"step": s.step_number, "action": s.action, "observation": s.observation}
                for s in self.steps
            ],
            "summary": self.summary,
        }


def _check_evidence(case: OperationalCase) -> str:
    evidence = case.evidence
    if not evidence:
        return "No evidence provided. Case lacks supporting data for validation."

    text_items = [e for e in evidence if e.type.value == "text"]
    metric_items = [e for e in evidence if e.type.value == "metric"]
    total = len(evidence)
    avg_confidence = sum(e.confidence for e in evidence) / total if total > 0 else 0.0

    parts = [f"{total} evidence items available"]
    if text_items:
        parts.append(f"{len(text_items)} text evidence")
    if metric_items:
        parts.append(f"{len(metric_items)} metric evidence")
    parts.append(f"Average confidence: {avg_confidence:.2f}")

    if avg_confidence >= 0.8:
        parts.append("Evidence quality: high")
    elif avg_confidence >= 0.5:
        parts.append("Evidence quality: moderate")
    else:
        parts.append("Evidence quality: low")

    return "; ".join(parts)


def _check_urgency(case: OperationalCase) -> str:
    text = case.report_text.lower()
    indicators = []

    critical_words = ["critical", "emergency", "immediate", "urgent"]
    high_words = ["delayed", "stuck", "failure", "damage", "lost"]
    medium_words = ["route", "delivery", "shipment", "warehouse"]

    found_critical = [w for w in critical_words if w in text]
    found_high = [w for w in high_words if w in text]
    found_medium = [w for w in medium_words if w in text]

    if found_critical:
        indicators.append(f"Critical indicators found: {', '.join(found_critical)}")
    if found_high:
        indicators.append(f"High-severity indicators: {', '.join(found_high)}")
    if found_medium:
        indicators.append(f"Operational indicators: {', '.join(found_medium)}")

    if not indicators:
        indicators.append("No urgency keywords detected in report text")

    reported = case.urgency.value if hasattr(case.urgency, "value") else str(case.urgency)
    indicators.append(f"Reported urgency: {reported}")

    return "; ".join(indicators)


def _check_domain(case: OperationalCase, domain_context: dict[str, Any]) -> str:
    parts = [f"Domain: {case.domain}"]

    if "evidence_types" in domain_context:
        valid_types = set(domain_context["evidence_types"])
        evidence_types = {e.type.value for e in case.evidence}
        supported = evidence_types.intersection(valid_types)
        unsupported = evidence_types - valid_types
        if supported:
            parts.append(f"Supported evidence types: {', '.join(supported)}")
        if unsupported:
            parts.append(f"Unsupported evidence types: {', '.join(unsupported)}")
        else:
            parts.append("All evidence types validated against domain policy")

    if "incident_types" in domain_context:
        parts.append(f"Domain incident types: {', '.join(domain_context['incident_types'][:3])}...")

    evidence_ok, msg = True, ""
    for e in case.evidence:
        if e.type.value not in domain_context.get("evidence_types", []):
            evidence_ok = False
            break

    if evidence_ok:
        parts.append("Domain evidence validation: passed")
    else:
        parts.append(f"Domain evidence validation: {msg or 'type mismatch detected'}")

    return "; ".join(parts)


def execute_react(
    case: OperationalCase,
    domain_context: dict[str, Any] | None = None,
) -> ReActTrace:
    ctx = domain_context or {}
    steps = []

    obs1 = _check_evidence(case)
    steps.append(ReActStep(step_number=1, action="CHECK_EVIDENCE", observation=obs1))

    obs2 = _check_urgency(case)
    steps.append(ReActStep(step_number=2, action="CHECK_URGENCY", observation=obs2))

    obs3 = _check_domain(case, ctx)
    steps.append(ReActStep(step_number=3, action="CHECK_DOMAIN", observation=obs3))

    evidence_count = len(case.evidence)
    has_text = any(e.type.value == "text" for e in case.evidence)
    has_metric = any(e.type.value == "metric" for e in case.evidence)

    if evidence_count >= 2 and has_text and has_metric:
        readiness = "Case ready for LLM analysis with sufficient multi-modal evidence"
    elif evidence_count >= 1:
        readiness = "Case ready for LLM analysis with limited evidence"
    else:
        readiness = "Case has no evidence; LLM analysis may result in rejection"

    return ReActTrace(
        steps=steps,
        summary=readiness,
    )
