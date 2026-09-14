"""Joint recommendation and explainability — Phase 2.5 + 2.6."""

from __future__ import annotations

from typing import Any

from case_core.domain.logistics_carrier_matching import CarrierMatching
from case_core.domain.logistics_contracts import (
    Carrier,
    CarrierRouteRecommendation,
    Route,
    ShipmentProfile,
)
from case_core.domain.logistics_route_recommendation import RouteRecommendation


class JointRecommendation:
    """Combines carrier and route matching into an explainable recommendation."""

    def __init__(
        self,
        carrier_matching: CarrierMatching,
        route_recommendation: RouteRecommendation,
    ):
        self.carrier_matching = carrier_matching
        self.route_recommendation = route_recommendation

    def recommend(
        self, profile: ShipmentProfile, max_recommendations: int = 3
    ) -> list[CarrierRouteRecommendation]:
        carrier_matches = self.carrier_matching.match(profile)
        route_matches = self.route_recommendation.recommend_routes(profile)
        recommendations: list[CarrierRouteRecommendation] = []
        for carrier_match in carrier_matches:
            for route_match in route_matches:
                recommendation = self._build_recommendation(
                    profile, carrier_match, route_match
                )
                recommendations.append(recommendation)
        recommendations.sort(
            key=lambda r: (
                r.confidence,
                -r.total_cost_usd,
                r.estimated_delivery_hours,
            ),
            reverse=True,
        )
        return recommendations[:max_recommendations]

    def _build_recommendation(
        self, profile: ShipmentProfile, carrier_match: dict[str, Any], route_match: dict[str, Any]
    ) -> CarrierRouteRecommendation:
        carrier = carrier_match["carrier"]
        route = route_match["route"]
        confidence = self._calculate_confidence(profile, carrier_match, route_match)
        estimated_cost = (
            carrier_match["estimated_cost"] + route_match["estimated_cost"]
        )
        estimated_hours = route_match["estimated_hours"]
        sla_met = profile.sla_hours is None or estimated_hours <= profile.sla_hours
        satisfied_constraints = self._satisfied_constraints(profile, carrier, route)
        discarded_constraints = self._discarded_constraints(profile, carrier, route)
        trade_offs = self._trade_offs(profile, carrier, route, confidence)
        risk_level = self._risk_level(profile, route)
        requires_hitl = self._requires_hitl(profile, confidence, risk_level)
        explanation = self._build_explanation(
            profile, carrier, route, confidence, estimated_cost, estimated_hours
        )
        return CarrierRouteRecommendation(
            recommendation_id=f"rec_{profile.shipment_id}_{carrier.carrier_id}_{route.route_id}",
            shipment_id=profile.shipment_id,
            carrier=carrier,
            route=route,
            confidence=confidence,
            total_cost_usd=estimated_cost,
            estimated_delivery_hours=estimated_hours,
            sla_met=sla_met,
            satisfied_constraints=satisfied_constraints,
            discarded_constraints=discarded_constraints,
            trade_offs=trade_offs,
            explanation=explanation,
            risk_level=risk_level,
            requires_hitl=requires_hitl,
        )

    def _calculate_confidence(
        self,
        profile: ShipmentProfile,
        carrier_match: dict[str, Any],
        route_match: dict[str, Any],
    ) -> float:
        confidence = 0.0
        confidence += carrier_match["fit_score"] * 0.4
        confidence += route_match["score"] * 0.35
        confidence += carrier_match["capability_match"] * 0.15
        confidence += min(carrier_match["slack"], 1.0) * 0.1
        return float(min(confidence, 1.0))

    def _satisfied_constraints(
        self, profile: ShipmentProfile, carrier: Carrier, route: Route
    ) -> list[str]:
        constraints = []
        if profile.cargo_type:
            constraints.append(f"cargo_type:{profile.cargo_type.value}")
        if profile.special_handling:
            constraints.append(f"special_handling:{profile.special_handling.value}")
        if profile.sla_hours is not None and route.total_estimated_hours <= profile.sla_hours:
            constraints.append("sla")
        if carrier.max_weight_kg >= profile.weight_kg:
            constraints.append("weight_capacity")
        if carrier.max_volume_m3 and profile.volume_m3 <= carrier.max_volume_m3:
            constraints.append("volume_capacity")
        return constraints

    def _discarded_constraints(
        self, profile: ShipmentProfile, carrier: Carrier, route: Route
    ) -> list[str]:
        discarded = []
        if profile.sla_hours is not None and route.total_estimated_hours > profile.sla_hours:
            discarded.append("sla")
        if profile.special_handling not in carrier.accepts_special_handling and profile.special_handling:
            discarded.append("special_handling")
        return discarded

    def _trade_offs(
        self, profile: ShipmentProfile, carrier: Carrier, route: Route, confidence: float
    ) -> list[str]:
        trade_offs = []
        if confidence < 0.7:
            trade_offs.append("Lower confidence due to limited carrier or route options")
        if route.risk_score > 0.5:
            trade_offs.append("Route carries elevated transit risk")
        if profile.sla_hours is not None and route.total_estimated_hours > profile.sla_hours:
            trade_offs.append("SLA cannot be fully met by this route")
        if route.total_tolls_fees > 100:
            trade_offs.append("Higher toll fees increase total cost")
        if not trade_offs:
            trade_offs.append("No significant trade-offs identified")
        return trade_offs

    def _risk_level(self, profile: ShipmentProfile, route: Route) -> str:
        risk_score = route.risk_score
        if profile.priority == "CRITICAL":
            risk_score += 0.1
        if profile.cargo_type.value in ("HAZARDOUS", "PERISHABLE"):
            risk_score += 0.15
        if risk_score >= 0.6:
            return "HIGH"
        if risk_score >= 0.3:
            return "MEDIUM"
        return "LOW"

    def _requires_hitl(self, profile: ShipmentProfile, confidence: float, risk_level: str) -> bool:
        return (
            confidence < 0.7
            or risk_level == "HIGH"
            or profile.cargo_type.value == "HAZARDOUS"
        )

    def _build_explanation(
        self,
        profile: ShipmentProfile,
        carrier: Carrier,
        route: Route,
        confidence: float,
        estimated_cost: float,
        estimated_hours: float,
    ) -> str:
        explanation = (
            f"Recommended {carrier.name} ({carrier.carrier_id}) with "
            f"{route.route_id} for shipment {profile.shipment_id}. "
            f"Carrier fit score: {confidence:.2f}. "
            f"Estimated cost: ${estimated_cost:.2f}. "
            f"Estimated delivery time: {estimated_hours:.1f} hours. "
            f"Route risk score: {route.risk_score:.2f}. "
            f"The carrier supports the shipment's cargo type and special handling requirements. "
            f"The route is scored based on distance, estimated time, risk, and cost."
        )
        return explanation
