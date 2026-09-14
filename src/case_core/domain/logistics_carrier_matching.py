"""Carrier matching service — Phase 2.3."""

from typing import Any

from case_core.domain.logistics_contracts import (
    CargoType,
    Carrier,
    ShipmentProfile,
    SpecialHandling,
)


class CarrierMatching:
    """Matches shipments to capable carriers."""

    def __init__(self, carriers: list[Carrier]):
        self.carriers = carriers

    def match(self, profile: ShipmentProfile) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for carrier in self._filter_capable_carriers(profile):
            fit_score = self._calculate_fit_score(profile, carrier)
            matches.append(
                {
                    "carrier": carrier,
                    "fit_score": fit_score,
                    "capability_match": self._calculate_capability_match(profile, carrier),
                    "capacity_adequate": self._is_capacity_adequate(profile, carrier),
                    "estimated_cost": self._estimate_cost(profile, carrier),
                    "slack": self._calculate_slack(carrier, profile),
                }
            )
        matches.sort(key=lambda x: x["fit_score"], reverse=True)
        return matches

    def _filter_capable_carriers(self, profile: ShipmentProfile) -> list[Carrier]:
        capable = []
        for carrier in self.carriers:
            if not carrier.active:
                continue
            if profile.weight_kg > carrier.max_weight_kg:
                continue
            if profile.volume_m3 and profile.volume_m3 > carrier.max_volume_m3:
                continue
            if not self._accepts_cargo_type(carrier, profile.cargo_type):
                continue
            if not self._accepts_special_handling(carrier, profile.special_handling):
                continue
            capable.append(carrier)
        return capable

    def _accepts_cargo_type(self, carrier: Carrier, cargo_type: CargoType) -> bool:
        if not carrier.accepts_cargo_types:
            return True  # Accepts all by default if not specified
        return cargo_type in carrier.accepts_cargo_types

    def _accepts_special_handling(self, carrier: Carrier, special_handling: SpecialHandling) -> bool:
        if special_handling == SpecialHandling.NONE:
            return True
        if not carrier.accepts_special_handling:
            return False  # Requires explicit acceptance
        return special_handling in carrier.accepts_special_handling

    def _calculate_fit_score(self, profile: ShipmentProfile, carrier: Carrier) -> float:
        score = 0.0
        if carrier.rating >= 4.5:
            score += 0.2
        elif carrier.rating >= 4.0:
            score += 0.15
        elif carrier.rating >= 3.5:
            score += 0.1
        capacity_util_weight = (
            profile.weight_kg / carrier.max_weight_kg if carrier.max_weight_kg else 0
        )
        capacity_util_volume = (
            (profile.volume_m3 or 0) / carrier.max_volume_m3
            if carrier.max_volume_m3 and profile.volume_m3
            else 0
        )
        avg_util = (capacity_util_weight + capacity_util_volume) / 2
        score += (1 - min(avg_util, 1)) * 0.3
        if carrier.sla_hours and profile.sla_hours:
            if carrier.sla_hours <= profile.sla_hours:
                score += 0.2
            else:
                score += 0.05
        cost_per_kg = carrier.base_rate_per_kg
        if cost_per_kg <= 2.0:
            score += 0.15
        elif cost_per_kg <= 5.0:
            score += 0.1
        if "express" in carrier.service_regions and profile.priority in (
            profile.priority.RUSH,
            profile.priority.CRITICAL,
        ):
            score += 0.1
        return min(score, 1.0)

    def _calculate_capability_match(self, profile: ShipmentProfile, carrier: Carrier) -> float:
        matches = 0
        total = 0
        if profile.cargo_type:
            total += 1
            if self._accepts_cargo_type(carrier, profile.cargo_type):
                matches += 1
        if profile.special_handling != SpecialHandling.NONE:
            total += 1
            if self._accepts_special_handling(carrier, profile.special_handling):
                matches += 1
        if profile.constraints:
            total += 1
            if all(c in carrier.service_regions for c in profile.constraints):
                matches += 1
        return matches / total if total else 1.0

    def _is_capacity_adequate(self, profile: ShipmentProfile, carrier: Carrier) -> bool:
        weight_ok = profile.weight_kg <= carrier.max_weight_kg
        volume_ok = True
        if profile.volume_m3 and carrier.max_volume_m3:
            volume_ok = profile.volume_m3 <= carrier.max_volume_m3
        return weight_ok and volume_ok

    def _estimate_cost(self, profile: ShipmentProfile, carrier: Carrier) -> float:
        base = carrier.base_rate_per_kg * profile.weight_kg
        if profile.special_handling != SpecialHandling.NONE:
            base *= 1.25
        if profile.cargo_type == CargoType.HAZARDOUS:
            base *= 1.5
        if profile.cargo_type == CargoType.PERISHABLE:
            base *= 1.3
        if carrier.rating >= 4.5:
            base *= 1.1
        return base

    def _calculate_slack(self, carrier: Carrier, profile: ShipmentProfile) -> float:
        weight_slack = (carrier.max_weight_kg - profile.weight_kg) / carrier.max_weight_kg
        volume_slack = 1.0
        if profile.volume_m3 and carrier.max_volume_m3:
            volume_slack = (carrier.max_volume_m3 - profile.volume_m3) / carrier.max_volume_m3
        return (weight_slack + volume_slack) / 2
