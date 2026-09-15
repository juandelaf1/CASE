"""Unit tests for logistics adapter and pipeline.

Tests USAID adapter, ShipmentProfile creation, classification,
and OperationalCase generation. Uses sample data — no network calls.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, "src")

from case_core.domain.logistics_classification import ShipmentClassification
from case_core.domain.logistics_contracts import (
    CargoType,
    ShipmentPriority,
)
from logistics_adapter.pipeline import LogisticsPipeline, PipelineResult
from logistics_adapter.usaid_adapter import ShipmentRecord, USSAIDShipmentAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(**overrides: object) -> ShipmentRecord:
    defaults = {
        "shipment_id": "100",
        "project_code": "100-CI-T01",
        "pq_number": "Pre-PQ Process",
        "po_so_number": "SCMS-4",
        "asn_dn_number": "ASN-8",
        "country": "Côte d'Ivoire",
        "managed_by": "PMO - US",
        "fulfill_via": "Direct Drop",
        "vendor_inco_term": "EXW",
        "shipment_mode": "Air",
        "pq_first_sent_date": "Pre-PQ Process",
        "po_sent_date": "Date Not Captured",
        "scheduled_delivery_date": "2-Jun-06",
        "delivered_date": "2-Jun-06",
        "delivery_recorded_date": "2-Jun-06",
        "product_group": "HRDT",
        "sub_classification": "HIV test",
        "vendor": "RANBAXY",
        "item_description": "HIV Reveal G3 Rapid Test, 30 Tests",
        "molecule_test_type": "HIV",
        "brand": "Reveal",
        "dosage": "N/A",
        "dosage_form": "Test kit",
        "unit_of_measure": "30",
        "line_item_quantity": 19,
        "line_item_value": 551.0,
        "pack_price": 29.0,
        "unit_price": 0.97,
        "manufacturing_site": "Ranbaxy, India",
        "first_line_designation": "Yes",
        "weight_kg": 13.0,
        "freight_cost_usd": 780.34,
        "line_item_insurance_usd": 0.0,
    }
    defaults.update(overrides)
    return ShipmentRecord(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ShipmentRecord tests
# ---------------------------------------------------------------------------

class TestShipmentRecord:
    def test_to_dict(self):
        record = _make_record()
        d = record.to_dict()
        assert d["shipment_id"] == "100"
        assert d["country"] == "Côte d'Ivoire"
        assert d["weight_kg"] == 13.0

    def test_defaults(self):
        record = _make_record(weight_kg=0.0, freight_cost_usd=0.0)
        assert record.weight_kg == 0.0
        assert record.freight_cost_usd == 0.0


# ---------------------------------------------------------------------------
# USSAIDShipmentAdapter tests
# ---------------------------------------------------------------------------

class TestUSSAIDShipmentAdapterConstruction:
    def test_default_path(self):
        adapter = USSAIDShipmentAdapter()
        assert adapter._csv_path == "data/raw/SCMS_Delivery_History_Dataset.csv"

    def test_custom_path(self):
        adapter = USSAIDShipmentAdapter(csv_path="/tmp/test.csv")
        assert adapter._csv_path == "/tmp/test.csv"


class TestUSSAIDShipmentAdapterToProfile:
    def test_basic_conversion(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record()
        profile = adapter.to_shipment_profile(record)

        assert profile.shipment_id == "USAID-100"
        assert profile.weight_kg == 13.0
        assert profile.destination == "Côte d'Ivoire"
        assert profile.cargo_type == CargoType.FRAGILE
        assert profile.metadata["country"] == "Côte d'Ivoire"
        assert profile.metadata["shipment_mode"] == "Air"

    def test_arv_gets_general_cargo(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(product_group="ARV", sub_classification="Adult")
        profile = adapter.to_shipment_profile(record)
        assert profile.cargo_type == CargoType.GENERAL

    def test_hrdt_gets_fragile_cargo(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(product_group="HRDT")
        profile = adapter.to_shipment_profile(record)
        assert profile.cargo_type == CargoType.FRAGILE

    def test_high_value_gets_high_priority(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(line_item_value=200000.0)
        profile = adapter.to_shipment_profile(record)
        assert profile.priority == ShipmentPriority.HIGH

    def test_pediatric_gets_high_priority(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(sub_classification="Pediatric")
        profile = adapter.to_shipment_profile(record)
        assert profile.priority == ShipmentPriority.HIGH

    def test_heavy_weight_adds_constraint(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(weight_kg=5000.0)
        profile = adapter.to_shipment_profile(record)
        assert "heavy_shipment" in profile.constraints

    def test_direct_drop_adds_constraint(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(fulfill_via="Direct Drop")
        profile = adapter.to_shipment_profile(record)
        assert "direct_drop" in profile.constraints


class TestUSSAIDShipmentAdapterParsing:
    def test_load_records_missing_file(self):
        adapter = USSAIDShipmentAdapter(csv_path="/nonexistent/file.csv")
        records = adapter.load_records()
        assert records == []

    def test_load_records_limit(self):
        adapter = USSAIDShipmentAdapter()
        if not os.path.exists(adapter._csv_path):
            pytest.skip("USAID dataset not available")
        records = adapter.load_records(limit=5)
        assert len(records) == 5

    def test_load_records_all_fields(self):
        adapter = USSAIDShipmentAdapter()
        if not os.path.exists(adapter._csv_path):
            pytest.skip("USAID dataset not available")
        records = adapter.load_records(limit=1)
        assert len(records) == 1
        r = records[0]
        assert r.shipment_id != ""
        assert r.country != ""
        assert r.product_group != ""


# ---------------------------------------------------------------------------
# ShipmentClassification tests (using profiles from adapter)
# ---------------------------------------------------------------------------

class TestShipmentClassificationWithAdapter:
    def test_classify_hrdt_shipment(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(product_group="HRDT", weight_kg=13.0)
        profile = adapter.to_shipment_profile(record)
        classifier = ShipmentClassification()
        result = classifier.classify(profile)

        assert "shipment_type" in result
        assert "risk_level" in result
        assert "logistics_class" in result
        assert "complexity_score" in result
        assert "handling_category" in result

    def test_classify_heavy_shipment(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(weight_kg=5000.0, line_item_value=200000.0)
        profile = adapter.to_shipment_profile(record)
        classifier = ShipmentClassification()
        result = classifier.classify(profile)

        assert result["shipment_type"] == "heavy_freight"
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_classify_standard_shipment(self):
        adapter = USSAIDShipmentAdapter()
        record = _make_record(
            product_group="ARV",
            sub_classification="Adult",
            weight_kg=100.0,
            line_item_value=5000.0,
        )
        profile = adapter.to_shipment_profile(record)
        classifier = ShipmentClassification()
        result = classifier.classify(profile)

        assert result["shipment_type"] == "general_freight"
        assert result["risk_level"] == "LOW"
        assert result["logistics_class"] == "standard"


# ---------------------------------------------------------------------------
# LogisticsPipeline tests
# ---------------------------------------------------------------------------

class TestLogisticsPipelineConstruction:
    def test_default_construction(self):
        pipeline = LogisticsPipeline()
        assert pipeline._adapter is not None
        assert pipeline._classifier is not None

    def test_custom_csv_path(self):
        pipeline = LogisticsPipeline(csv_path="/tmp/test.csv")
        assert pipeline._adapter._csv_path == "/tmp/test.csv"


class TestLogisticsPipelineRun:
    def test_run_missing_file(self):
        pipeline = LogisticsPipeline(csv_path="/nonexistent/file.csv")
        result = pipeline.run()
        assert result.loaded == 0
        assert result.classified == 0

    def test_run_with_limit(self):
        pipeline = LogisticsPipeline()
        if not os.path.exists(pipeline._adapter._csv_path):
            pytest.skip("USAID dataset not available")
        result = pipeline.run(limit=10)
        assert result.loaded == 10
        assert result.classified == 10
        assert result.errors == []

    def test_pipeline_result_structure(self):
        pipeline = LogisticsPipeline()
        if not os.path.exists(pipeline._adapter._csv_path):
            pytest.skip("USAID dataset not available")
        result = pipeline.run(limit=5)
        assert isinstance(result, PipelineResult)
        assert result.processing_time_ms > 0
        assert len(result.classifications) == 5


class TestLogisticsPipelineCases:
    def test_operational_cases_created(self):
        pipeline = LogisticsPipeline()
        if not os.path.exists(pipeline._adapter._csv_path):
            pytest.skip("USAID dataset not available")
        result = pipeline.run(limit=5)
        assert result.cases_created == 5

    def test_case_has_logistics_domain(self):
        adapter = USSAIDShipmentAdapter()
        if not os.path.exists(adapter._csv_path):
            pytest.skip("USAID dataset not available")
        records = adapter.load_records(limit=1)
        assert len(records) == 1

        pipeline = LogisticsPipeline()
        classified = pipeline._process_record(records[0])
        case = classified.operational_case

        assert case.domain == "logistics"
        assert case.case_id.startswith("LOG-")
        assert len(case.evidence) >= 2
        assert case.metadata["data_source"] == "usaidscms"

    def test_classification_accuracy_on_sample(self):
        pipeline = LogisticsPipeline()
        if not os.path.exists(pipeline._adapter._csv_path):
            pytest.skip("USAID dataset not available")
        result = pipeline.run(limit=100)

        classifications = result.classifications
        assert len(classifications) == 100

        risk_levels = [c["classification"]["risk_level"] for c in classifications]
        assert all(r in ("LOW", "MEDIUM", "HIGH") for r in risk_levels)

        logistics_classes = [c["classification"]["logistics_class"] for c in classifications]
        assert all(lc in ("standard", "express", "priority", "immediate", "lager") for lc in logistics_classes)


# ---------------------------------------------------------------------------
# Architecture boundary tests
# ---------------------------------------------------------------------------

class TestLogisticsAdapterNoCoreCoupling:
    def test_adapter_no_core_domain_imports(self):
        import inspect

        from logistics_adapter.usaid_adapter import USSAIDShipmentAdapter
        source = inspect.getsource(USSAIDShipmentAdapter)
        assert "from case_core.application" not in source
        assert "from case_core.providers" not in source
        assert "from case_core.reliability" not in source

    def test_adapter_imports_contracts(self):
        import logistics_adapter.usaid_adapter as mod

        source = open(mod.__file__).read()
        assert "from case_core.domain.logistics_contracts" in source
