"""Phase 4 Error Analysis — runs 3 real USAID cases through full CASE pipeline.

Selects 3 representative records:
  A) Normal/Low-risk: Truck, ARV Adult, $7,976
  B) Ambiguous/Medium-risk: Air, HRDT HIV test, $40,000
  C) Critical/High-risk: Air, ARV Pediatric, $140,581

Runs each through: Adapter → Profile → Classification → OperationalCase
  → TriageEngine (Groq) → ReliabilityPipeline → RiskAssessment → TriageDecision

Documents output at every stage. No fabricated metrics.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")

from case_core.composition import create_app_dependencies
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.logistics_classification import ShipmentClassification
from logistics_adapter.usaid_adapter import ShipmentRecord, USSAIDShipmentAdapter

# ---------------------------------------------------------------------------
# Target records (from dataset analysis)
# ---------------------------------------------------------------------------

TARGET_IDS = {
    "A": "82721",   # Normal: Truck, ARV Adult, 150kg, $7,976
    "B": "4",       # Ambiguous: Air, HRDT HIV test, 171kg, $40,000
    "C": "108",     # Critical: Air, ARV Pediatric, 2,126kg, $140,581
}


def _load_target_records() -> dict[str, ShipmentRecord]:
    adapter = USSAIDShipmentAdapter()
    all_records = adapter.load_records()
    by_id = {r.shipment_id: r for r in all_records}
    targets = {}
    for label, uid in TARGET_IDS.items():
        if uid in by_id:
            targets[label] = by_id[uid]
        else:
            print(f"WARNING: Record {uid} not found for case {label}")
    return targets


def _build_case_from_record(record: ShipmentRecord) -> OperationalCase:
    adapter = USSAIDShipmentAdapter()
    profile = adapter.to_shipment_profile(record)
    classifier = ShipmentClassification()
    classification = classifier.classify(profile)
    needs_verification = classifier.needs_additional_verification(profile)

    report_text = profile.metadata.get("report_text", "")

    risk = classification.get("risk_level", "LOW")
    logistics_class = classification.get("logistics_class", "standard")
    if risk == "HIGH" or logistics_class == "immediate":
        urgency = UrgencyLevel.CRITICAL
    elif risk == "MEDIUM" or logistics_class == "priority":
        urgency = UrgencyLevel.HIGH
    elif logistics_class == "express":
        urgency = UrgencyLevel.MEDIUM
    else:
        urgency = UrgencyLevel.LOW

    evidence = [
        EvidenceItem(
            id=f"ev-{record.shipment_id}-text",
            type=EvidenceType.TEXT,
            content=report_text,
            source="usaidscms",
            confidence=0.95,
            extracted_at="2026-09-15T00:00:00Z",
        ),
        EvidenceItem(
            id=f"ev-{record.shipment_id}-weight",
            type=EvidenceType.METRIC,
            content=json.dumps({"weight_kg": record.weight_kg, "value_usd": record.line_item_value}),
            source="usaidscms",
            confidence=1.0,
            extracted_at="2026-09-15T00:00:00Z",
        ),
        EvidenceItem(
            id=f"ev-{record.shipment_id}-classification",
            type=EvidenceType.RULE,
            content=json.dumps(classification),
            source="logistics_classification",
            confidence=0.9,
            extracted_at="2026-09-15T00:00:00Z",
        ),
    ]

    metadata = {
        "shipment_id": profile.shipment_id,
        "country": record.country,
        "shipment_mode": record.shipment_mode,
        "product_group": record.product_group,
        "sub_classification": record.sub_classification,
        "vendor": record.vendor,
        "weight_kg": record.weight_kg,
        "line_item_value": record.line_item_value,
        "freight_cost_usd": record.freight_cost_usd,
        "classification": classification,
        "manufacturing_site": record.manufacturing_site,
        "data_source": "usaidscms",
        "data_license": "public_domain",
    }

    return OperationalCase(
        case_id=f"LOG-{record.shipment_id}",
        report_text=report_text,
        domain="logistics",
        urgency=urgency,
        evidence=evidence,
        metadata=metadata,
    )


@dataclass
class StageResult:
    stage: str
    status: str
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class CaseAnalysis:
    label: str
    record_id: str
    record_summary: str
    profile_summary: str
    classification: dict[str, str | float]
    needs_verification: bool
    initial_urgency: str
    stages: list[StageResult] = field(default_factory=list)
    final_decision: dict[str, Any] | None = None
    final_risk: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)


async def analyze_case(label: str, record: ShipmentRecord, engine: Any) -> CaseAnalysis:
    adapter = USSAIDShipmentAdapter()
    profile = adapter.to_shipment_profile(record)
    classifier = ShipmentClassification()
    classification = classifier.classify(profile)
    needs_verification = classifier.needs_additional_verification(profile)

    case = _build_case_from_record(record)

    analysis = CaseAnalysis(
        label=label,
        record_id=record.shipment_id,
        record_summary=f"{record.shipment_mode} {record.product_group}/{record.sub_classification} to {record.country}, {record.weight_kg:.0f}kg, ${record.line_item_value:,.0f}",
        profile_summary=f"cargo={profile.cargo_type.value}, priority={profile.priority.value}, handling={profile.special_handling.value}, constraints={profile.constraints}",
        classification=classification,
        needs_verification=needs_verification,
        initial_urgency=case.urgency.value,
    )

    # Stage 1: Domain resolution
    t0 = time.time()
    try:
        from case_core.domain.registry import DomainRegistry
        registry = DomainRegistry()
        from case_core.domain.logistics_policy import LogisticsPolicy
        registry.register(LogisticsPolicy())
        domain_policy = registry.get("logistics")
        analysis.stages.append(StageResult(
            stage="domain_resolution",
            status="ok",
            output="LogisticsPolicy resolved for domain='logistics'",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except Exception as e:
        analysis.stages.append(StageResult(stage="domain_resolution", status="error", error=str(e)))
        analysis.errors.append(f"domain_resolution: {e}")
        return analysis

    # Stage 2: Evidence validation
    t0 = time.time()
    try:
        valid, msg = domain_policy.validate_evidence(case.evidence)
        analysis.stages.append(StageResult(
            stage="evidence_validation",
            status="ok" if valid else "failed",
            output=msg,
            duration_ms=(time.time() - t0) * 1000,
        ))
        if not valid:
            analysis.errors.append(f"evidence_validation: {msg}")
            return analysis
    except Exception as e:
        analysis.stages.append(StageResult(stage="evidence_validation", status="error", error=str(e)))
        analysis.errors.append(f"evidence_validation: {e}")
        return analysis

    # Stage 3: TriageEngine execution (full pipeline with Groq)
    t0 = time.time()
    try:
        result = await engine.execute(case)
        duration = (time.time() - t0) * 1000

        if result.error is not None:
            analysis.stages.append(StageResult(
                stage="triage_engine",
                status="error",
                output=f"Error: {result.error.category.value} - {result.error.message}",
                duration_ms=duration,
            ))
            analysis.errors.append(f"triage_engine: {result.error.category.value}: {result.error.message}")
            return analysis

        if result.decision is None:
            analysis.stages.append(StageResult(
                stage="triage_engine",
                status="no_decision",
                output="No decision produced",
                duration_ms=duration,
            ))
            analysis.errors.append("triage_engine: no decision produced")
            return analysis

        decision = result.decision
        analysis.stages.append(StageResult(
            stage="triage_engine",
            status="ok",
            output=f"action={decision.action}, urgency={decision.urgency}, confidence={decision.confidence:.2f}",
            duration_ms=duration,
        ))

        analysis.final_decision = {
            "decision_id": decision.decision_id,
            "action": decision.action,
            "reason": decision.reason,
            "urgency": decision.urgency,
            "confidence": decision.confidence,
            "evidence_summary": decision.evidence_summary,
            "lifecycle": decision.lifecycle.value,
            "processing_time_ms": decision.processing_time_ms,
            "provider_info": decision.metadata.get("provider_info"),
        }

    except Exception as e:
        analysis.stages.append(StageResult(stage="triage_engine", status="error", error=str(e), duration_ms=(time.time() - t0) * 1000))
        analysis.errors.append(f"triage_engine: {e}")
        return analysis

    # Stage 4: Risk assessment (from automation policy)
    t0 = time.time()
    try:
        from case_core.domain.logistics_automation import LogisticsAutomationPolicy
        auto_policy = LogisticsAutomationPolicy()
        risk_assessment = auto_policy.assess_risk(
            case=case,
            data={"decision": decision.action, "urgency": decision.urgency},
            validation_status="valid",
            evidence_quality="high",
            confidence=decision.confidence,
        )
        analysis.stages.append(StageResult(
            stage="risk_assessment",
            status="ok",
            output=f"risk={risk_assessment.risk_level.value}, automation={risk_assessment.automation_decision.value}, hitl={risk_assessment.requires_hitl}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        analysis.final_risk = {
            "risk_level": risk_assessment.risk_level.value,
            "automation_decision": risk_assessment.automation_decision.value,
            "requires_hitl": risk_assessment.requires_hitl,
            "factors": risk_assessment.factors,
            "justification": risk_assessment.justification,
        }
    except Exception as e:
        analysis.stages.append(StageResult(stage="risk_assessment", status="error", error=str(e)))
        analysis.errors.append(f"risk_assessment: {e}")

    return analysis


async def main():
    print("=" * 80)
    print("PHASE 4 ERROR ANALYSIS - Real USAID Cases through Full CASE Pipeline")
    print("=" * 80)

    records = _load_target_records()
    if not records:
        print("ERROR: No target records found")
        return

    print(f"\nLoaded {len(records)} target records")

    # Initialize CASE engine with Groq
    groq_key = os.environ.get("CASE_GROQ_API_KEY", "")
    if groq_key:
        os.environ["CASE_PROVIDER"] = "groq"
        print("Using provider: Groq (qwen/qwen3.8-27b)")
    else:
        os.environ["CASE_PROVIDER"] = "mock"
        print("Using provider: Mock (no CASE_GROQ_API_KEY)")

    deps = create_app_dependencies()
    engine = deps.engine

    analyses: list[CaseAnalysis] = []
    for label in ["A", "B", "C"]:
        if label not in records:
            print(f"\nSkipping case {label}: record not found")
            continue
        record = records[label]
        print(f"\n{'-' * 60}")
        print(f"CASE {label}: {record.shipment_id}")
        print(f"{'-' * 60}")
        analysis = await analyze_case(label, record, engine)
        analyses.append(analysis)

        print(f"  Record: {analysis.record_summary}")
        print(f"  Profile: {analysis.profile_summary}")
        print(f"  Classification: {json.dumps(analysis.classification, indent=4)}")
        print(f"  Needs verification: {analysis.needs_verification}")
        print(f"  Initial urgency: {analysis.initial_urgency}")
        print()
        for stage in analysis.stages:
            icon = "OK" if stage.status == "ok" else "FAIL" if stage.status == "error" else stage.status.upper()
            print(f"  [{icon}] {stage.stage}: {stage.output or stage.error} ({stage.duration_ms:.0f}ms)")

        if analysis.final_decision:
            print("\n  FINAL DECISION:")
            d = analysis.final_decision
            print(f"    Action: {d['action']}")
            print(f"    Urgency: {d['urgency']}")
            print(f"    Confidence: {d['confidence']:.2f}")
            print(f"    Reason: {d['reason'][:200]}")
            print(f"    Lifecycle: {d['lifecycle']}")
            if d.get('provider_info'):
                pi = d['provider_info']
                print(f"    Provider: {pi.get('provider')}/{pi.get('model')}")
                print(f"    Tokens: {pi.get('total_tokens')}, Latency: {pi.get('latency_ms'):.0f}ms")

        if analysis.final_risk:
            r = analysis.final_risk
            print("\n  RISK ASSESSMENT:")
            print(f"    Level: {r['risk_level']}")
            print(f"    Automation: {r['automation_decision']}")
            print(f"    HITL required: {r['requires_hitl']}")
            print(f"    Factors: {r['factors']}")
            print(f"    Justification: {r['justification'][:200]}")

        if analysis.errors:
            print(f"\n  ERRORS: {analysis.errors}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"{'Case':<8} {'Record':<10} {'Decision':<12} {'Urgency':<10} {'Risk':<10} {'HITL':<8} {'Confidence':<12} {'Errors'}")
    print("-" * 80)
    for a in analyses:
        d = a.final_decision or {}
        r = a.final_risk or {}
        print(f"{a.label:<8} {a.record_id:<10} {d.get('action','N/A'):<12} {d.get('urgency','N/A'):<10} {r.get('risk_level','N/A'):<10} {str(r.get('requires_hitl','N/A')):<8} {d.get('confidence',0):<12.2f} {len(a.errors)}")

    # Error classification
    print("\nERROR CLASSIFICATION:")
    all_errors = []
    for a in analyses:
        all_errors.extend(a.errors)
    if not all_errors:
        print("  No errors detected across all cases")
    else:
        for err in all_errors:
            stage = err.split(":")[0] if ":" in err else "unknown"
            print(f"  [{stage}] {err}")

    # Save results
    results = []
    for a in analyses:
        results.append({
            "label": a.label,
            "record_id": a.record_id,
            "record_summary": a.record_summary,
            "profile_summary": a.profile_summary,
            "classification": a.classification,
            "needs_verification": a.needs_verification,
            "initial_urgency": a.initial_urgency,
            "stages": [{"stage": s.stage, "status": s.status, "output": s.output, "error": s.error, "duration_ms": s.duration_ms} for s in a.stages],
            "final_decision": a.final_decision,
            "final_risk": a.final_risk,
            "errors": a.errors,
        })

    with open("docs/phase4_error_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nResults saved to docs/phase4_error_analysis_results.json")


if __name__ == "__main__":
    asyncio.run(main())
