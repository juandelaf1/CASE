"""Route recommendation service — Phase 2.4."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from case_core.domain.logistics_contracts import (
    Route,
    RouteSegment,
    ShipmentProfile,
    SpecialHandling,
)

GraphProvider = Callable[[str, str], float | None]


class RouteRecommendation:
    """Generates and scores candidate routes for a shipment."""

    def __init__(self, graph_provider: GraphProvider | None = None):
        self.graph_provider = graph_provider if graph_provider is not None else None

    def recommend_routes(
        self, profile: ShipmentProfile, max_routes: int = 5
    ) -> list[dict[str, Any]]:
        candidates = self._generate_candidate_routes(profile)
        scored: list[dict[str, Any]] = []
        for route in candidates:
            score = self._score_route(profile, route)
            scored.append(
                {
                    "route": route,
                    "score": score,
                    "distance_km": route.total_distance_km,
                    "estimated_hours": route.total_estimated_hours,
                    "risk_score": route.risk_score,
                    "estimated_cost": self._estimate_route_cost(route),
                    "traffic_factor": self._estimate_traffic_factor(route),
                    "weather_risk": self._estimate_weather_risk(route),
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:max_routes]

    def _generate_candidate_routes(self, profile: ShipmentProfile) -> list[Route]:
        routes: list[Route] = []
        if not profile.origin or not profile.destination:
            return routes
        direct = self._create_direct_route(profile)
        if direct:
            routes.append(direct)
        waypoint_sets: list[list[tuple[str, ...]]] = [
            [("hub1", "hub2")],
            [("hub3",)],
            [("rail_terminal", "border_crossing")],
        ]
        for waypoints in waypoint_sets:
            route = self._create_waypoint_route(profile, waypoints)
            if route:
                routes.append(route)
        return routes

    def _create_direct_route(self, profile: ShipmentProfile) -> Route | None:
        distance = self._haversine_distance(profile.origin, profile.destination)
        if distance is None:
            return None
        estimated_hours = distance / 60.0
        segment = RouteSegment(
            segment_id="direct",
            from_location=profile.origin,
            to_location=profile.destination,
            transport_mode="truck",
            distance_km=distance,
            estimated_hours=estimated_hours,
            tolls_fees=self._estimate_tolls(distance),
        )
        return Route(
            route_id=f"direct_{profile.shipment_id}",
            segments=[segment],
            total_distance_km=distance,
            total_estimated_hours=estimated_hours,
            total_tolls_fees=segment.tolls_fees,
            risk_score=self._calculate_route_risk([segment]),
            notes="Direct origin-destination",
        )

    def _create_waypoint_route(
        self, profile: ShipmentProfile, waypoints: list[tuple[str, ...]]
    ) -> Route | None:
        try:
            stops: list[str] = [profile.origin]
            for wp in waypoints:
                if isinstance(wp, tuple):
                    stops.extend(list(wp))
                else:
                    stops.append(str(wp))
            stops.append(profile.destination)
            segments: list[RouteSegment] = []
            total_distance = 0.0
            total_hours = 0.0
            total_tolls = 0.0
            for i in range(len(stops) - 1):
                dist = self._haversine_distance(stops[i], stops[i + 1])
                if dist is None:
                    return None
                hours = dist / 55.0
                segment = RouteSegment(
                    segment_id=f"seg_{i}",
                    from_location=stops[i],
                    to_location=stops[i + 1],
                    transport_mode="truck",
                    distance_km=dist,
                    estimated_hours=hours,
                    tolls_fees=self._estimate_tolls(dist),
                )
                segments.append(segment)
                total_distance += dist
                total_hours += hours
                total_tolls += segment.tolls_fees
            return Route(
                route_id=f"waypoint_{profile.shipment_id}_{hash(tuple(stops))}",
                segments=segments,
                total_distance_km=total_distance,
                total_estimated_hours=total_hours,
                total_tolls_fees=total_tolls,
                risk_score=self._calculate_route_risk(segments),
                notes=f"Via waypoints: {' -> '.join(stops)}",
            )
        except Exception:
            return None

    def _score_route(self, profile: ShipmentProfile, route: Route) -> float:
        score = 0.0
        max_dist = 5000.0
        dist_score = max(0, 1 - (route.total_distance_km / max_dist))
        score += dist_score * 0.3
        time_score = 0.0
        if profile.sla_hours is not None:
            if route.total_estimated_hours <= profile.sla_hours:
                time_score = 1.0
            else:
                excess = route.total_estimated_hours - profile.sla_hours
                time_score = max(0, 1 - (excess / profile.sla_hours))
        else:
            time_score = max(0, 1 - (route.total_estimated_hours / 168))
        score += time_score * 0.25
        risk_score = 1 - route.risk_score
        score += risk_score * 0.2
        cost = self._estimate_route_cost(route)
        max_cost_per_km = 10.0
        cost_per_km = cost / max(route.total_distance_km, 1.0)
        cost_score = max(0, 1 - (cost_per_km / max_cost_per_km))
        score += cost_score * 0.15
        if profile.special_handling != SpecialHandling.NONE:
            special_ok = all(
                not any(
                    kw in (seg.notes or "").lower()
                    for kw in ["border", "rough", "mountain"]
                )
                for seg in route.segments
            )
            if special_ok:
                score += 0.1
        return min(score, 1.0)

    def _haversine_distance(self, origin: str, destination: str) -> float | None:
        coords = {
            "new york": (40.7128, -74.0060),
            "los angeles": (34.0522, -118.2437),
            "chicago": (41.8781, -87.6298),
            "houston": (29.7604, -95.3698),
            "atlanta": (33.7490, -84.3880),
            "miami": (25.7617, -80.1918),
            "dallas": (32.7767, -96.7970),
            "seattle": (47.6062, -122.3321),
            "denver": (39.7392, -104.9903),
            "phoenix": (33.4484, -112.0740),
        }
        o_key = origin.lower().strip()
        d_key = destination.lower().strip()
        if o_key not in coords or d_key not in coords:
            if origin == destination:
                return 0.0
            import random
            return random.uniform(100, 3000)
        lat1, lon1 = coords[o_key]
        lat2, lon2 = coords[d_key]
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _estimate_tolls(self, distance_km: float) -> float:
        return distance_km * 0.05

    def _calculate_route_risk(self, segments: list[RouteSegment]) -> float:
        risk = 0.0
        for seg in segments:
            if seg.transport_mode == "rail":
                risk += 0.1
            elif seg.transport_mode == "air":
                risk += 0.05
            else:
                risk += 0.15
            if seg.distance_km > 500:
                risk += 0.05
            if seg.tolls_fees > 50:
                risk += 0.02
        return min(risk / max(len(segments), 1), 1.0)

    def _estimate_route_cost(self, route: Route) -> float:
        base_cost = route.total_distance_km * 0.8
        toll_cost = route.total_tolls_fees
        time_cost = route.total_estimated_hours * 10
        risk_premium = route.risk_score * 50
        return base_cost + toll_cost + time_cost + risk_premium

    def _estimate_traffic_factor(self, route: Route) -> float:
        return 1.0 + (route.risk_score * 0.3)

    def _estimate_weather_risk(self, route: Route) -> float:
        return route.risk_score * 0.5
