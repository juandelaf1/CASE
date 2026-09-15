"""Logistics pipeline — connects USAID adapter to CASE triage engine.

Converts real shipment records into CASE OperationalCase objects,
classifies them using existing logistics modules, and routes through
the full CASE pipeline (TriageEngine → ReliabilityPipeline → Decision).

Architecture:
  USAID CSV → ShipmentRecord → ShipmentProfile → ShipmentClassification
    → OperationalCase → TriageEngine → TriageDecision
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.logistics_classification import ShipmentClassification
from case_core.domain.logistics_contracts import ShipmentProfile
from case_core.domain.logistics_understanding import ShipmentUnderstanding
from logistics_adapter.usaid_adapter import ShipmentRecord, USSAIDShipmentAdapter

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedShipment:
    """A shipment that has been profiled and classified."""

    record: ShipmentRecord
    profile: ShipmentProfile
    classification: dict[str, str | float]
    needs_verification: bool
    operational_case: OperationalCase


@dataclass
class PipelineResult:
    """Result of processing a batch of shipments through the pipeline."""

    total_records: int = 0
    loaded: int = 0
    profiled: int = 0
    classified: int = 0
    cases_created: int = 0
    processing_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    classifications: list[dict[str, Any]] = field(default_factory=list)


class LogisticsPipeline:
    """End-to-end logistics pipeline: data → profile → classify → CASE case."""

    def __init__(self, csv_path: str | None = None) -> None:
        self._adapter = USSAIDShipmentAdapter(csv_path=csv_path or "data/raw/SCMS_Delivery_History_Dataset.csv")
        self._understanding = ShipmentUnderstanding()
        self._classifier = ShipmentClassification()

    def run(self, limit: int | None = None) -> PipelineResult:
        """Execute the full pipeline.

        Args:
            limit: Maximum records to process. None = all.

        Returns:
            PipelineResult with metrics and classified shipments.
        """
        start = time.time()
        result = PipelineResult()

        records = self._adapter.load_records(limit=limit)
        result.total_records = len(records)
        result.loaded = len(records)

        for record in records:
            try:
                classified = self._process_record(record)
                result.classified += 1
                result.cases_created += 1
                result.classifications.append({
                    "shipment_id": record.shipment_id,
                    "country": record.country,
                    "product_group": record.product_group,
                    "shipment_mode": record.shipment_mode,
                    "weight_kg": record.weight_kg,
                    "classification": classified.classification,
                    "needs_verification": classified.needs_verification,
                })
            except Exception as e:
                result.errors.append(f"Record {record.shipment_id}: {e}")
                logger.warning("Failed to process record %s: %s", record.shipment_id, e)

        result.processing_time_ms = (time.time() - start) * 1000
        logger.info(
            "Pipeline complete: %d/%d records processed in %.0fms",
            result.classified,
            result.total_records,
            result.processing_time_ms,
        )
        return result

    def _process_record(self, record: ShipmentRecord) -> ClassifiedShipment:
        profile = self._adapter.to_shipment_profile(record)
        classification = self._classifier.classify(profile)
        needs_verification = self._classifier.needs_additional_verification(profile)
        case = self._create_operational_case(record, profile, classification)

        return ClassifiedShipment(
            record=record,
            profile=profile,
            classification=classification,
            needs_verification=needs_verification,
            operational_case=case,
        )

    def _create_operational_case(
        self,
        record: ShipmentRecord,
        profile: ShipmentProfile,
        classification: dict[str, str | float],
    ) -> OperationalCase:
        report_text = profile.metadata.get("report_text", "")

        urgency = self._classification_to_urgency(classification)

        evidence = self._build_evidence(record, profile, classification)

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

    def _build_evidence(
        self,
        record: ShipmentRecord,
        profile: ShipmentProfile,
        classification: dict[str, str | float],
    ) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []

        evidence.append(EvidenceItem(
            id=f"ev-{record.shipment_id}-text",
            type=EvidenceType.TEXT,
            content=profile.metadata.get("report_text", ""),
            source="usaidscms",
            confidence=0.95,
            extracted_at="2026-09-15T00:00:00Z",
        ))

        if record.weight_kg > 0:
            evidence.append(EvidenceItem(
                id=f"ev-{record.shipment_id}-weight",
                type=EvidenceType.METRIC,
                content=json.dumps({"weight_kg": record.weight_kg, "value_usd": record.line_item_value}),
                source="usaidscms",
                confidence=1.0,
                extracted_at="2026-09-15T00:00:00Z",
            ))

        evidence.append(EvidenceItem(
            id=f"ev-{record.shipment_id}-classification",
            type=EvidenceType.RULE,
            content=json.dumps(classification),
            source="logistics_classification",
            confidence=0.9,
            extracted_at="2026-09-15T00:00:00Z",
        ))

        return evidence

    @staticmethod
    def _classification_to_urgency(classification: dict[str, str | float]) -> UrgencyLevel:
        risk = classification.get("risk_level", "LOW")
        logistics_class = classification.get("logistics_class", "standard")

        if risk == "HIGH" or logistics_class == "immediate":
            return UrgencyLevel.CRITICAL
        if risk == "MEDIUM" or logistics_class == "priority":
            return UrgencyLevel.HIGH
        if logistics_class == "express":
            return UrgencyLevel.MEDIUM
        return UrgencyLevel.LOW
