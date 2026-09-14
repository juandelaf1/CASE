"""Shipment understanding service — Phase 2.1."""

from __future__ import annotations

import re

from case_core.domain.logistics_contracts import (
    CargoType,
    ShipmentPriority,
    ShipmentProfile,
    SpecialHandling,
)


class ShipmentUnderstanding:
    """Transforms raw shipment data into a structured ShipmentProfile."""

    CARGO_KEYWORDS: dict[str, CargoType] = {
        "perishable": CargoType.PERISHABLE,
        "food": CargoType.PERISHABLE,
        "hazardous": CargoType.HAZARDOUS,
        "dangerous": CargoType.HAZARDOUS,
        "fragile": CargoType.FRAGILE,
        "bulk": CargoType.BULK,
        "container": CargoType.CONTAINER,
        "oversized": CargoType.OVERSIZED,
        "heavy": CargoType.GENERAL,
        "general": CargoType.GENERAL,
    }

    PRIORITY_KEYWORDS: dict[str, ShipmentPriority] = {
        "critical": ShipmentPriority.CRITICAL,
        "rush": ShipmentPriority.RUSH,
        "urgent": ShipmentPriority.RUSH,
        "high": ShipmentPriority.HIGH,
        "standard": ShipmentPriority.STANDARD,
        "low": ShipmentPriority.LOW,
    }

    SPECIAL_HANDLING_KEYWORDS: dict[str, SpecialHandling] = {
        "temperature": SpecialHandling.TEMPERATURE_CONTROLLED,
        "cold chain": SpecialHandling.TEMPERATURE_CONTROLLED,
        "refrigerated": SpecialHandling.TEMPERATURE_CONTROLLED,
        "insurance": SpecialHandling.INSURANCE_REQUIRED,
        "signature": SpecialHandling.SIGNATURE_REQUIRED,
        "white glove": SpecialHandling.WHITE_GLOVE,
        "whiteglove": SpecialHandling.WHITE_GLOVE,
        "hazmat": SpecialHandling.HAZMAT_COMPLIANT,
        "hazardous material": SpecialHandling.HAZMAT_COMPLIANT,
    }

    def understand(
        self,
        report_text: str,
        shipment_id: str,
        weight_kg: float | None = None,
        volume_m3: float | None = None,
        constraints: list[str] | None = None,
        sla_hours: float | None = None,
        declared_value_usd: float | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ShipmentProfile:
        text = report_text.lower()
        return ShipmentProfile(
            shipment_id=shipment_id,
            origin=self._extract_location(text, "from", "origin", "source") or "",
            destination=self._extract_location(text, "to", "destination", "target") or "",
            weight_kg=weight_kg or self._extract_weight(text) or 0.0,
            volume_m3=volume_m3 or self._extract_volume(text) or 0.0,
            cargo_type=self._detect_cargo_type(text),
            priority=self._detect_priority(text),
            special_handling=self._detect_special_handling(text),
            constraints=constraints or self._extract_constraints(text),
            sla_hours=sla_hours or self._extract_sla(text),
            declared_value_usd=declared_value_usd,
            origin_address=self._extract_address(text, "origin"),
            destination_address=self._extract_address(text, "destination"),
            pickup_datetime=self._extract_datetime(text, "pickup"),
            delivery_datetime=self._extract_datetime(text, "delivery"),
            metadata=metadata or {},
        )

    def _extract_location(
        self, text: str, *keywords: str
    ) -> str | None:
        for kw in keywords:
            match = re.search(rf"{kw}[:\s]+([A-Za-z0-9\s,.-]+?)(?:\n|$|\bto\b)", text, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip(",")
        return None

    def _extract_address(self, text: str, keyword: str) -> str | None:
        match = re.search(rf"{keyword}[:\s]+([^\n]+?)(?:\n|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_datetime(self, text: str, keyword: str) -> str | None:
        match = re.search(rf"{keyword}[:\s]+(\d{{4}}-\d{{2}}-\d{{2}}[ T]\d{{2}}:\d{{2}})", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_weight(self, text: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilogram)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_volume(self, text: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(m³|m3|cubic meters)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_sla(self, text: str) -> float | None:
        match = re.search(r"sla[:\s]+(\d+(?:\.\d+)?)\s*(hours|hrs|h)\b", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_constraints(self, text: str) -> list[str]:
        constraints: list[str] = []
        for kw in ["temperature-controlled", "hazmat", "fragile", "express", "insurance"]:
            if kw in text:
                constraints.append(kw)
        return constraints

    def _detect_cargo_type(self, text: str) -> CargoType:
        for keyword, cargo_type in self.CARGO_KEYWORDS.items():
            if keyword in text:
                return cargo_type
        return CargoType.GENERAL

    def _detect_priority(self, text: str) -> ShipmentPriority:
        for keyword, priority in self.PRIORITY_KEYWORDS.items():
            if keyword in text:
                return priority
        return ShipmentPriority.STANDARD

    def _detect_special_handling(self, text: str) -> SpecialHandling:
        for keyword, handling in self.SPECIAL_HANDLING_KEYWORDS.items():
            if keyword in text:
                return handling
        return SpecialHandling.NONE
