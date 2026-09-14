"""Hybrid Decision Engine — Phase 5."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DecisionSource(str, Enum):
    """Source of a decision component."""

    LLM = "llm"
    SPECIALIST = "specialist"
    RULES = "rules"
    EVIDENCE = "evidence"
    RISK = "risk"
    HITL = "hitl"
    ENSEMBLE = "ensemble"


class DecisionComponent(BaseModel):
    """A single component of the decision."""

    source: DecisionSource
    output: Any
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HybridDecision(BaseModel):
    """Combined decision from multiple sources."""

    decision_id: str
    case_id: str
    final_decision: str
    confidence: float = Field(ge=0.0, le=1.0)
    components: list[DecisionComponent] = Field(default_factory=list)
    requires_hitl: bool = False
    hitl_reason: str | None = None
    explanation: str = ""
    risk_level: str = "LOW"
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionRule(BaseModel):
    """A deterministic decision rule."""

    rule_id: str
    condition: str
    action: str
    priority: int = 0
    enabled: bool = True


class HybridDecisionEngine:
    """Combines LLM, specialist models, rules, evidence, and HITL into final decisions."""

    def __init__(self) -> None:
        self._rules: list[DecisionRule] = []
        self._audit_log: list[dict[str, Any]] = []

    def make_decision(
        self,
        case_id: str,
        llm_output: dict[str, Any] | None = None,
        specialist_outputs: list[dict[str, Any]] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        risk_assessment: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> HybridDecision:
        components = []
        audit_trail = []
        if llm_output:
            components.append(DecisionComponent(
                source=DecisionSource.LLM,
                output=llm_output,
                confidence=llm_output.get("confidence", 0.7),
                metadata=llm_output.get("metadata", {}),
            ))
            audit_trail.append({"source": "llm", "action": "proposal_generated"})
        if specialist_outputs:
            for spec_out in specialist_outputs:
                components.append(DecisionComponent(
                    source=DecisionSource.SPECIALIST,
                    output=spec_out,
                    confidence=spec_out.get("confidence", 0.8),
                    metadata=spec_out.get("metadata", {}),
                ))
            audit_trail.append({"source": "specialist", "action": f"{len(specialist_outputs)} predictions received"})
        rule_decisions = self._apply_rules(context or {})
        if rule_decisions:
            components.append(DecisionComponent(
                source=DecisionSource.RULES,
                output=rule_decisions,
                confidence=1.0,
            ))
            audit_trail.append({"source": "rules", "action": f"{len(rule_decisions)} rules applied"})
        if evidence:
            evidence_valid = self._validate_evidence(evidence)
            components.append(DecisionComponent(
                source=DecisionSource.EVIDENCE,
                output=evidence_valid,
                confidence=evidence_valid.get("confidence", 0.9),
            ))
            audit_trail.append({"source": "evidence", "action": "evidence_validated"})
        risk_level = "LOW"
        if risk_assessment:
            risk_level = risk_assessment.get("risk_level", "LOW")
            components.append(DecisionComponent(
                source=DecisionSource.RISK,
                output=risk_assessment,
                confidence=0.9,
            ))
            audit_trail.append({"source": "risk", "action": f"risk_level={risk_level}"})
        final_decision, confidence = self._reconcile_decisions(components)
        requires_hitl, hitl_reason = self._assess_hitl_requirement(
            final_decision, risk_level, confidence, components
        )
        if requires_hitl:
            audit_trail.append({"source": "hitl", "action": "required", "reason": hitl_reason or "unknown"})
        explanation = self._build_explanation(components, final_decision, confidence, risk_level)
        return HybridDecision(
            decision_id=f"hybrid_{case_id}",
            case_id=case_id,
            final_decision=final_decision,
            confidence=confidence,
            components=components,
            requires_hitl=requires_hitl,
            hitl_reason=hitl_reason,
            explanation=explanation,
            risk_level=risk_level,
            audit_trail=audit_trail,
        )

    def add_rule(self, rule: DecisionRule) -> None:
        self._rules.append(rule)

    def get_rules(self) -> list[DecisionRule]:
        return self._rules.copy()

    def get_audit_log(self) -> list[dict[str, Any]]:
        return self._audit_log.copy()

    def _apply_rules(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        applied = []
        for rule in sorted(self._rules, key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue
            if self._evaluate_condition(rule.condition, context):
                applied.append({
                    "rule_id": rule.rule_id,
                    "action": rule.action,
                    "condition": rule.condition,
                })
        return applied

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        condition_lower = condition.lower()
        for key, _value in context.items():
            if key.lower() in condition_lower:
                return True
        return "always" in condition_lower

    def _validate_evidence(self, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(evidence)
        valid = sum(1 for e in evidence if e.get("valid", True))
        return {
            "total_evidence": total,
            "valid_evidence": valid,
            "confidence": valid / total if total > 0 else 0.0,
            "is_sufficient": valid >= total * 0.5,
        }

    def _reconcile_decisions(self, components: list[DecisionComponent]) -> tuple[str, float]:
        if not components:
            return "ESCALATE", 0.0
        decisions = []
        for comp in components:
            output = comp.output
            if isinstance(output, dict):
                if "decision" in output:
                    decisions.append((output["decision"], comp.confidence))
                elif "label" in output:
                    decisions.append((output["label"], comp.confidence))
                elif "action" in output:
                    decisions.append((output["action"], comp.confidence))
        if not decisions:
            return "ESCALATE", 0.0
        decision_counts: dict[str, float] = {}
        for decision, conf in decisions:
            decision_counts[decision] = decision_counts.get(decision, 0) + conf
        best_decision = max(decision_counts, key=lambda k: decision_counts[k])
        best_confidence = decision_counts[best_decision] / len(decisions)
        return best_decision, min(best_confidence, 1.0)

    def _assess_hitl_requirement(
        self,
        decision: str,
        risk_level: str,
        confidence: float,
        components: list[DecisionComponent],
    ) -> tuple[bool, str | None]:
        if risk_level in ("HIGH", "CRITICAL"):
            return True, f"Risk level {risk_level} requires human review"
        if confidence < 0.6:
            return True, f"Low confidence ({confidence:.2f}) requires human review"
        if decision == "ESCALATE":
            return True, "Decision escalation requires human review"
        specialist_decisions = [c for c in components if c.source == DecisionSource.SPECIALIST]
        llm_decisions = [c for c in components if c.source == DecisionSource.LLM]
        if specialist_decisions and llm_decisions:
            spec_decision = specialist_decisions[0].output
            llm_decision = llm_decisions[0].output
            if isinstance(spec_decision, dict) and isinstance(llm_decision, dict):
                spec_label = spec_decision.get("label", spec_decision.get("decision", ""))
                llm_label = llm_decision.get("decision", llm_decision.get("label", ""))
                if spec_label and llm_label and spec_label != llm_label:
                    return True, f"Specialist ({spec_label}) and LLM ({llm_label}) disagree"
        return False, None

    def _build_explanation(
        self,
        components: list[DecisionComponent],
        decision: str,
        confidence: float,
        risk_level: str,
    ) -> str:
        sources = [c.source.value for c in components]
        explanation = (
            f"Hybrid decision: {decision} (confidence: {confidence:.2f}, risk: {risk_level}). "
            f"Sources combined: {', '.join(sources)}. "
        )
        for comp in components:
            if comp.source == DecisionSource.LLM:
                explanation += f"LLM proposed {comp.output.get('decision', 'N/A')}. "
            elif comp.source == DecisionSource.SPECIALIST:
                explanation += f"Specialist predicted {comp.output.get('label', comp.output.get('decision', 'N/A'))}. "
            elif comp.source == DecisionSource.RULES:
                explanation += f"Rules applied: {len(comp.output)} rules. "
            elif comp.source == DecisionSource.EVIDENCE:
                explanation += f"Evidence: {comp.output.get('valid_evidence', 0)}/{comp.output.get('total_evidence', 0)} valid. "
        return explanation
