"""Shipment classification service — Phase 2.2."""

from __future__ import annotations

from case_core.domain.logistics_contracts import (
    CargoType,
    ShipmentPriority,
    ShipmentProfile,
    SpecialHandling,
)


class ShipmentClassification:
    """Classifies shipments based on deterministic rules."""

    def classify(self, profile: ShipmentProfile) -> dict[str, str | float]:
        shipment_type = self._determine_shipment_type(profile)
        risk_level = self._calculate_risk_level(profile)
        logistics_class = self._determine_logistics_class(profile)
        return {
            "shipment_type": shipment_type,
            "logistics_class": logistics_class,
            "risk_level": risk_level,
            "complexity_score": self._calculate_complexity(profile),
            "handling_category": self._determine_handling_category(profile),
        }

    def _determine_shipment_type(self, profile: ShipmentProfile) -> str:
        volume = profile.volume_m3 or 0
        if volume == 0 and profile.weight_kg > 1000:
            return "heavy_freight"
        if volume > 100:
            return "bulk_shipment"
        if profile.cargo_type == CargoType.PERISHABLE:
            return "temperature_controlled"
        if profile.cargo_type == CargoType.HAZARDOUS:
            return "dangerous_goods"
        if profile.cargo_type == CargoType.OVERSIZED:
            return "oversized"
        if profile.cargo_type == CargoType.FRAGILE:
            return "fragile_cargo"
        return "general_freight"

    def _calculate_risk_level(self, profile: ShipmentProfile) -> str:
        score = 0
        if profile.cargo_type in (CargoType.HAZARDOUS, CargoType.PERISHABLE):
            score += 30
        if profile.priority in (ShipmentPriority.CRITICAL, ShipmentPriority.RUSH):
            score += 20
        if profile.special_handling != SpecialHandling.NONE:
            score += 15
        if (profile.sla_hours is not None and profile.sla_hours < 12):
            score += 25
        if profile.weight_kg > 5000:
            score += 10
        if "weather_exposed" in profile.constraints:
            score += 20
        if "cross_border" in profile.constraints:
            score += 15
        if score >= 50:
            return "HIGH"
        if score >= 30:
            return "MEDIUM"
        return "LOW"

    def _determine_logistics_class(self, profile: ShipmentProfile) -> str:
        if profile.priority == ShipmentPriority.CRITICAL:
            return "immediate"
        if profile.priority == ShipmentPriority.RUSH:
            return "priority"
        if profile.weight_kg > 2000 or (profile.volume_m3 or 0) > 50:
            return "lager"
        if profile.sla_hours is not None and profile.sla_hours < 24:
            return "express"
        return "standard"

    def _calculate_complexity(self, profile: ShipmentProfile) -> float:
        base = 1.0
        if profile.cargo_type in (CargoType.HAZARDOUS, CargoType.PERISHABLE):
            base += 1.5
        if profile.special_handling != SpecialHandling.NONE:
            base += 0.8
        if profile.sla_hours is not None and profile.sla_hours < 12:
            base += 1.2
        if "customs_brokerage" in profile.constraints:
            base += 0.5
        if "multiple_drops" in profile.constraints:
            base += 0.7
        return min(base, 5.0)

    def _determine_handling_category(self, profile: ShipmentProfile) -> str:
        if profile.cargo_type in (CargoType.HAZARDOUS,):
            return "specialized"
        if profile.special_handling != SpecialHandling.NONE:
            return "enhanced"
        if profile.priority in (ShipmentPriority.HIGH, ShipmentPriority.CRITICAL):
            return "priority"
        return "standard"

    def needs_additional_verification(self, profile: ShipmentProfile) -> bool:
        return (
            profile.cargo_type == CargoType.HAZARDOUS
            or profile.special_handling == SpecialHandling.HAZMAT_COMPLIANT
            or "cross_border" in profile.constraints
            or profile.declared_value_usd is not None and profile.declared_value_usd > 100000
        )
