"""Evaluation dataset and metrics for Logistics Intelligence — Phase 2.8."""

from __future__ import annotations

import random
from typing import Any


class LogisticsEvaluation:
    """Provides evaluation datasets and metrics for logistics recommendations."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def generate_dataset(self, num_shipments: int = 100) -> list[dict[str, Any]]:
        """Generate a synthetic evaluation dataset."""
        shipments = []
        cargo_types = [
            "GENERAL", "PERISHABLE", "HAZARDOUS", "FRAGILE", "BULK", "CONTAINER", "OVERSIZED"
        ]
        priorities = ["LOW", "STANDARD", "HIGH", "RUSH", "CRITICAL"]
        origins = ["new york", "los angeles", "chicago", "houston", "atlanta", "miami", "dallas", "seattle", "denver", "phoenix"]
        destinations = ["new york", "los angeles", "chicago", "houston", "atlanta", "miami", "dallas", "seattle", "denver", "phoenix"]
        special_handling = ["NONE", "TEMPERATURE_CONTROLLED", "INSURANCE_REQUIRED", "SIGNATURE_REQUIRED", "WHITE_GLOVE", "HAZMAT_COMPLIANT"]

        for i in range(num_shipments):
            origin = random.choice(origins)
            destination = random.choice(destinations)
            if origin == destination:
                destination = random.choice(destinations)
            shipments.append({
                "shipment_id": f"eval_ship_{i}",
                "origin": origin,
                "destination": destination,
                "weight_kg": round(random.uniform(5, 8000), 2),
                "volume_m3": round(random.uniform(0.5, 250), 2),
                "cargo_type": random.choice(cargo_types),
                "priority": random.choice(priorities),
                "special_handling": random.choice(special_handling),
                "constraints": random.sample(["weather_exposed", "cross_border", "customs_brokerage", "multiple_drops"], k=random.randint(0, 2)),
                "sla_hours": random.choice([None, 6, 12, 24, 48, 72]),
                "declared_value_usd": random.choice([None, None, None, 50000, 100000, 250000]),
                "expected_risk_level": "LOW",
                "expected_logistics_class": "standard",
            })
        return shipments

    def evaluate_recommendations(
        self,
        profiles: list[dict[str, Any]],
        recommendations: list[Any],
    ) -> dict[str, Any]:
        """Evaluate recommendation quality against ground truth."""
        if not profiles:
            return {"total": 0, "accuracy": 0.0}

        total = len(profiles)
        sla_met = 0
        risk_correct = 0
        class_correct = 0
        risk_score = 0.0
        confidence_score = 0.0
        for profile, rec in zip(profiles, recommendations, strict=False):
            rec_dict = rec.model_dump() if hasattr(rec, "model_dump") else rec
            if rec_dict.get("sla_met"):
                sla_met += 1
            if rec_dict.get("risk_level") == profile.get("expected_risk_level"):
                risk_correct += 1
            if rec_dict.get("logistics_class") == profile.get("expected_logistics_class"):
                class_correct += 1
            risk_score += rec_dict.get("risk_score", 0.0)
            confidence_score += rec_dict.get("confidence", 0.0)

        return {
            "total": total,
            "sla_met": sla_met,
            "sla_met_rate": sla_met / total,
            "risk_accuracy": risk_correct / total,
            "classification_accuracy": class_correct / total,
            "average_risk_score": risk_score / total,
            "average_confidence": confidence_score / total,
        }

    def generate_evaluation_scenarios(self) -> list[dict[str, Any]]:
        """Generate specific evaluation scenarios for logistics cases."""
        scenarios = []
        base = {
            "hazmat_critical": {
                "shipment_id": "scenario_hazmat_critical",
                "origin": "new york",
                "destination": "los angeles",
                "weight_kg": 2500,
                "volume_m3": 30,
                "cargo_type": "HAZARDOUS",
                "priority": "CRITICAL",
                "special_handling": "HAZMAT_COMPLIANT",
                "constraints": ["cross_border", "customs_brokerage"],
                "sla_hours": 12,
                "declared_value_usd": 250000,
            },
            "perishable_standard": {
                "shipment_id": "scenario_perishable_standard",
                "origin": "miami",
                "destination": "chicago",
                "weight_kg": 800,
                "volume_m3": 20,
                "cargo_type": "PERISHABLE",
                "priority": "STANDARD",
                "special_handling": "TEMPERATURE_CONTROLLED",
                "constraints": ["weather_exposed"],
                "sla_hours": 24,
                "declared_value_usd": 50000,
            },
            "bulk_low": {
                "shipment_id": "scenario_bulk_low",
                "origin": "dallas",
                "destination": "seattle",
                "weight_kg": 6000,
                "volume_m3": 150,
                "cargo_type": "BULK",
                "priority": "LOW",
                "special_handling": "NONE",
                "constraints": [],
                "sla_hours": None,
                "declared_value_usd": None,
            },
            "fragile_rush": {
                "shipment_id": "scenario_fragile_rush",
                "origin": "denver",
                "destination": "phoenix",
                "weight_kg": 200,
                "volume_m3": 5,
                "cargo_type": "FRAGILE",
                "priority": "RUSH",
                "special_handling": "SIGNATURE_REQUIRED",
                "constraints": [],
                "sla_hours": 12,
                "declared_value_usd": 100000,
            },
        }
        for name, profile in base.items():
            scenarios.append({"name": name, "profile": profile})
        return scenarios
