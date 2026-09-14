"""Tests for Hybrid Decision Intelligence — Phase 5."""


from case_core.hybrid.decision_engine import (
    DecisionComponent,
    DecisionRule,
    DecisionSource,
    HybridDecision,
    HybridDecisionEngine,
)


class TestDecisionContracts:
    def test_decision_component(self):
        comp = DecisionComponent(
            source=DecisionSource.LLM,
            output={"decision": "approve"},
            confidence=0.9,
        )
        assert comp.source == DecisionSource.LLM
        assert comp.confidence == 0.9

    def test_hybrid_decision(self):
        decision = HybridDecision(
            decision_id="dec_1",
            case_id="case_1",
            final_decision="approve",
            confidence=0.85,
        )
        assert decision.final_decision == "approve"
        assert decision.confidence == 0.85

    def test_decision_rule(self):
        rule = DecisionRule(
            rule_id="rule_1",
            condition="urgency == critical",
            action="escalate",
            priority=10,
        )
        assert rule.priority == 10


class TestHybridDecisionEngine:
    def test_creation(self):
        engine = HybridDecisionEngine()
        assert len(engine.get_rules()) == 0

    def test_make_decision_llm_only(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
        )
        assert decision.final_decision == "approve"
        assert decision.confidence > 0
        assert len(decision.components) == 1

    def test_make_decision_specialist_only(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            specialist_outputs=[{"label": "approve", "confidence": 0.85}],
        )
        assert decision.final_decision == "approve"
        assert len(decision.components) == 1

    def test_make_decision_combined(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
            specialist_outputs=[{"label": "approve", "confidence": 0.85}],
        )
        assert decision.final_decision == "approve"
        assert len(decision.components) == 2

    def test_make_decision_with_rules(self):
        engine = HybridDecisionEngine()
        engine.add_rule(DecisionRule(
            rule_id="r1",
            condition="always",
            action="check_safety",
        ))
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
            context={"urgency": "high"},
        )
        assert decision.final_decision == "approve"
        assert any(c.source == DecisionSource.RULES for c in decision.components)

    def test_make_decision_with_evidence(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
            evidence=[{"type": "document", "valid": True}, {"type": "photo", "valid": True}],
        )
        assert decision.final_decision == "approve"
        assert any(c.source == DecisionSource.EVIDENCE for c in decision.components)

    def test_make_decision_with_risk(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
            risk_assessment={"risk_level": "HIGH", "factors": ["hazardous"]},
        )
        assert decision.requires_hitl is True
        assert decision.risk_level == "HIGH"

    def test_hitl_on_low_confidence(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.4},
        )
        assert decision.requires_hitl is True
        assert "Low confidence" in decision.hitl_reason

    def test_hitl_on_disagreement(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
            specialist_outputs=[{"label": "reject", "confidence": 0.85}],
            risk_assessment={"risk_level": "LOW"},
        )
        assert decision.requires_hitl is True
        assert decision.hitl_reason is not None
        assert "disagree" in decision.hitl_reason.lower() or "low confidence" in decision.hitl_reason.lower()

    def test_audit_trail(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
        )
        assert len(decision.audit_trail) > 0

    def test_explanation(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
        )
        assert len(decision.explanation) > 0
        assert "approve" in decision.explanation.lower()

    def test_add_rule(self):
        engine = HybridDecisionEngine()
        rule = DecisionRule(rule_id="r1", condition="always", action="test")
        engine.add_rule(rule)
        assert len(engine.get_rules()) == 1

    def test_no_components_escalate(self):
        engine = HybridDecisionEngine()
        decision = engine.make_decision(case_id="case_1")
        assert decision.final_decision == "ESCALATE"
        assert decision.requires_hitl is True

    def test_full_hybrid_decision(self):
        engine = HybridDecisionEngine()
        engine.add_rule(DecisionRule(
            rule_id="r1",
            condition="urgency == critical",
            action="priority_routing",
            priority=10,
        ))
        decision = engine.make_decision(
            case_id="case_1",
            llm_output={"decision": "approve", "confidence": 0.9},
            specialist_outputs=[{"label": "approve", "confidence": 0.85}],
            evidence=[{"type": "document", "valid": True}],
            risk_assessment={"risk_level": "LOW"},
            context={"urgency": "critical"},
        )
        assert decision.final_decision == "approve"
        assert decision.confidence > 0
        assert len(decision.components) >= 3
        assert len(decision.audit_trail) >= 3
        assert len(decision.explanation) > 0


class TestDecisionSource:
    def test_all_sources(self):
        assert DecisionSource.LLM.value == "llm"
        assert DecisionSource.SPECIALIST.value == "specialist"
        assert DecisionSource.RULES.value == "rules"
        assert DecisionSource.EVIDENCE.value == "evidence"
        assert DecisionSource.RISK.value == "risk"
        assert DecisionSource.HITL.value == "hitl"
        assert DecisionSource.ENSEMBLE.value == "ensemble"
