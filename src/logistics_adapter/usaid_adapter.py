"""USAID SCMS Delivery History adapter.

Loads real shipment records from the USAID Supply Chain Management System
(SCMS) Delivery History Dataset. Converts structured CSV rows into
CASE-compatible ShipmentProfile and OperationalCase objects.

Data source: USAID / PEPFAR (public domain)
License: US Government public domain
Records: 10,324 shipment records
Fields: 33 columns (shipment ID, country, mode, weight, cost, dates, etc.)
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from case_core.domain.logistics_contracts import (
    CargoType,
    ShipmentPriority,
    ShipmentProfile,
    SpecialHandling,
)

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = "data/raw/SCMS_Delivery_History_Dataset.csv"

SHIPMENT_MODE_MAP: dict[str, str] = {
    "Air": "air",
    "Sea": "sea",
    "Truck": "truck",
    "Air Ocean": "multimodal",
    "Ocean Air": "multimodal",
}

PRODUCT_GROUP_CARGO_MAP: dict[str, CargoType] = {
    "HRDT": CargoType.FRAGILE,
    "ARV": CargoType.GENERAL,
    "ACT": CargoType.GENERAL,
    "Malaria": CargoType.GENERAL,
    "OVC": CargoType.GENERAL,
    "RB": CargoType.GENERAL,
    "HRP": CargoType.FRAGILE,
    "POE": CargoType.GENERAL,
}


@dataclass
class ShipmentRecord:
    """A single shipment record from USAID SCMS data."""

    shipment_id: str
    project_code: str
    pq_number: str
    po_so_number: str
    asn_dn_number: str
    country: str
    managed_by: str
    fulfill_via: str
    vendor_inco_term: str
    shipment_mode: str
    pq_first_sent_date: str
    po_sent_date: str
    scheduled_delivery_date: str
    delivered_date: str
    delivery_recorded_date: str
    product_group: str
    sub_classification: str
    vendor: str
    item_description: str
    molecule_test_type: str
    brand: str
    dosage: str
    dosage_form: str
    unit_of_measure: str
    line_item_quantity: int
    line_item_value: float
    pack_price: float
    unit_price: float
    manufacturing_site: str
    first_line_designation: str
    weight_kg: float
    freight_cost_usd: float
    line_item_insurance_usd: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "shipment_id": self.shipment_id,
            "country": self.country,
            "shipment_mode": self.shipment_mode,
            "product_group": self.product_group,
            "sub_classification": self.sub_classification,
            "vendor": self.vendor,
            "item_description": self.item_description,
            "weight_kg": self.weight_kg,
            "line_item_value": self.line_item_value,
            "freight_cost_usd": self.freight_cost_usd,
            "scheduled_delivery_date": self.scheduled_delivery_date,
            "delivered_date": self.delivered_date,
        }


class USSAIDShipmentAdapter:
    """Adapter for USAID SCMS Delivery History Dataset."""

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH) -> None:
        self._csv_path = csv_path

    def load_records(self, limit: int | None = None) -> list[ShipmentRecord]:
        """Load shipment records from CSV.

        Args:
            limit: Maximum records to load. None = all.

        Returns:
            List of ShipmentRecord objects.
        """
        path = Path(self._csv_path)
        if not path.exists():
            logger.error("USAID dataset not found at %s", self._csv_path)
            return []

        records: list[ShipmentRecord] = []
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break
                    record = self._parse_row(row)
                    if record is not None:
                        records.append(record)
        except Exception as e:
            logger.error("Failed to load USAID dataset: %s", e)
            return []

        logger.info("Loaded %d shipment records from USAID SCMS", len(records))
        return records

    def to_shipment_profile(self, record: ShipmentRecord) -> ShipmentProfile:
        """Convert a ShipmentRecord to a CASE ShipmentProfile."""
        cargo_type = self._infer_cargo_type(record)
        priority = self._infer_priority(record)
        special_handling = self._infer_special_handling(record)
        constraints = self._infer_constraints(record)
        sla_hours = self._compute_sla_hours(record)

        report_text = self._build_report_text(record)

        return ShipmentProfile(
            shipment_id=f"USAID-{record.shipment_id}",
            origin=self._infer_origin(record),
            destination=record.country,
            weight_kg=max(record.weight_kg, 0.0),
            volume_m3=0.0,
            cargo_type=cargo_type,
            priority=priority,
            special_handling=special_handling,
            constraints=constraints,
            sla_hours=sla_hours,
            declared_value_usd=record.line_item_value if record.line_item_value > 0 else None,
            origin_address=record.manufacturing_site,
            destination_address=record.country,
            pickup_datetime=record.po_sent_date if record.po_sent_date != "Date Not Captured" else None,
            delivery_datetime=record.delivered_date if record.delivered_date else None,
            metadata={
                "report_text": report_text,
                "country": record.country,
                "shipment_mode": record.shipment_mode,
                "product_group": record.product_group,
                "sub_classification": record.sub_classification,
                "vendor": record.vendor,
                "freight_cost_usd": record.freight_cost_usd,
                "line_item_quantity": record.line_item_quantity,
                "pack_price": record.pack_price,
                "manufacturing_site": record.manufacturing_site,
                "usaid_raw_id": record.shipment_id,
            },
        )

    def _parse_row(self, row: dict[str, str]) -> ShipmentRecord | None:
        try:
            return ShipmentRecord(
                shipment_id=row.get("ID", "").strip(),
                project_code=row.get("Project Code", "").strip(),
                pq_number=row.get("PQ #", "").strip(),
                po_so_number=row.get("PO / SO #", "").strip(),
                asn_dn_number=row.get("ASN/DN #", "").strip(),
                country=row.get("Country", "").strip(),
                managed_by=row.get("Managed By", "").strip(),
                fulfill_via=row.get("Fulfill Via", "").strip(),
                vendor_inco_term=row.get("Vendor INCO Term", "").strip(),
                shipment_mode=row.get("Shipment Mode", "").strip(),
                pq_first_sent_date=row.get("PQ First Sent to Client Date", "").strip(),
                po_sent_date=row.get("PO Sent to Vendor Date", "").strip(),
                scheduled_delivery_date=row.get("Scheduled Delivery Date", "").strip(),
                delivered_date=row.get("Delivered to Client Date", "").strip(),
                delivery_recorded_date=row.get("Delivery Recorded Date", "").strip(),
                product_group=row.get("Product Group", "").strip(),
                sub_classification=row.get("Sub Classification", "").strip(),
                vendor=row.get("Vendor", "").strip(),
                item_description=row.get("Item Description", "").strip(),
                molecule_test_type=row.get("Molecule/Test Type", "").strip(),
                brand=row.get("Brand", "").strip(),
                dosage=row.get("Dosage", "").strip(),
                dosage_form=row.get("Dosage Form", "").strip(),
                unit_of_measure=row.get("Unit of Measure (Per Pack)", "").strip(),
                line_item_quantity=self._safe_int(row.get("Line Item Quantity", "0")),
                line_item_value=self._safe_float(row.get("Line Item Value", "0")),
                pack_price=self._safe_float(row.get("Pack Price", "0")),
                unit_price=self._safe_float(row.get("Unit Price", "0")),
                manufacturing_site=row.get("Manufacturing Site", "").strip(),
                first_line_designation=row.get("First Line Designation", "").strip(),
                weight_kg=self._safe_float(row.get("Weight (Kilograms)", "0")),
                freight_cost_usd=self._safe_float(row.get("Freight Cost (USD)", "0")),
                line_item_insurance_usd=self._safe_float(row.get("Line Item Insurance (USD)", "0")),
            )
        except Exception as e:
            logger.warning("Failed to parse row: %s", e)
            return None

    def _infer_cargo_type(self, record: ShipmentRecord) -> CargoType:
        pg = record.product_group.upper()
        if pg in PRODUCT_GROUP_CARGO_MAP:
            return PRODUCT_GROUP_CARGO_MAP[pg]
        return CargoType.GENERAL

    def _infer_priority(self, record: ShipmentRecord) -> ShipmentPriority:
        sub = record.sub_classification.lower()
        if "pediatric" in sub or "critical" in sub:
            return ShipmentPriority.HIGH
        if record.line_item_value > 100000:
            return ShipmentPriority.HIGH
        if record.freight_cost_usd > 10000:
            return ShipmentPriority.HIGH
        return ShipmentPriority.STANDARD

    def _infer_special_handling(self, record: ShipmentRecord) -> SpecialHandling:
        desc = record.item_description.lower()
        if "test" in desc or "kit" in desc:
            return SpecialHandling.NONE
        if record.product_group.upper() == "HRDT":
            return SpecialHandling.TEMPERATURE_CONTROLLED
        return SpecialHandling.NONE

    def _infer_constraints(self, record: ShipmentRecord) -> list[str]:
        constraints: list[str] = []
        if record.fulfill_via == "Direct Drop":
            constraints.append("direct_drop")
        if record.vendor_inco_term in ("EXW", "FCA"):
            constraints.append("ex_works")
        if record.weight_kg > 1000:
            constraints.append("heavy_shipment")
        return constraints

    def _compute_sla_hours(self, record: ShipmentRecord) -> float | None:
        if not record.scheduled_delivery_date or record.scheduled_delivery_date == "Date Not Captured":
            return None
        if not record.po_sent_date or record.po_sent_date == "Date Not Captured":
            return None
        try:
            from datetime import datetime
            fmt = "%d-%b-%y"
            scheduled = datetime.strptime(record.scheduled_delivery_date, fmt)
            po_sent = datetime.strptime(record.po_sent_date, fmt)
            delta = scheduled - po_sent
            return max(delta.total_seconds() / 3600, 0.0)
        except (ValueError, TypeError):
            return None

    def _infer_origin(self, record: ShipmentRecord) -> str:
        site = record.manufacturing_site
        if not site:
            return "Unknown"
        parts = site.split(",")
        return parts[-1].strip() if len(parts) > 1 else site

    def _build_report_text(self, record: ShipmentRecord) -> str:
        parts = [
            f"Shipment {record.shipment_id}",
            f"from {record.manufacturing_site}" if record.manufacturing_site else "",
            f"to {record.country}",
            f"via {record.shipment_mode}" if record.shipment_mode else "",
            f"weighing {record.weight_kg:.0f} kg" if record.weight_kg > 0 else "",
            f"valued at ${record.line_item_value:,.0f}" if record.line_item_value > 0 else "",
            f"containing {record.product_group} {record.sub_classification}",
            f"vendor: {record.vendor}" if record.vendor else "",
        ]
        return " ".join(p for p in parts if p)

    @staticmethod
    def _safe_float(val: str) -> float:
        try:
            return float(val.replace(",", "")) if val else 0.0
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(val: str) -> int:
        try:
            return int(float(val.replace(",", ""))) if val else 0
        except (ValueError, TypeError):
            return 0
