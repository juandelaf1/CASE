"""Logistics domain contracts for Phase 2 — Logistics Intelligence."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CargoType(str, Enum):
    """Types of cargo for logistics shipments."""

    GENERAL = "GENERAL"
    PERISHABLE = "PERISHABLE"
    HAZARDOUS = "HAZARDOUS"
    FRAGILE = "FRAGILE"
    BULK = "BULK"
    CONTAINER = "CONTAINER"
    OVERSIZED = "OVERSIZED"


class ShipmentPriority(str, Enum):
    """Priority levels for logistics shipments."""

    LOW = "LOW"
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    RUSH = "RUSH"
    CRITICAL = "CRITICAL"


class SpecialHandling(str, Enum):
    """Special handling requirements."""

    NONE = "NONE"
    TEMPERATURE_CONTROLLED = "TEMPERATURE_CONTROLLED"
    INSURANCE_REQUIRED = "INSURANCE_REQUIRED"
    SIGNATURE_REQUIRED = "SIGNATURE_REQUIRED"
    WHITE_GLOVE = "WHITE_GLOVE"
    HAZMAT_COMPLIANT = "HAZMAT_COMPLIANT"


class ShipmentProfile(BaseModel):
    """Structured profile of a logistics shipment."""

    shipment_id: str
    origin: str
    destination: str
    weight_kg: float = Field(ge=0)
    volume_m3: float = Field(ge=0)
    cargo_type: CargoType = CargoType.GENERAL
    priority: ShipmentPriority = ShipmentPriority.STANDARD
    special_handling: SpecialHandling = SpecialHandling.NONE
    constraints: list[str] = Field(default_factory=list)
    sla_hours: float | None = None
    declared_value_usd: float | None = None
    origin_address: str | None = None
    destination_address: str | None = None
    pickup_datetime: str | None = None
    delivery_datetime: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Carrier(BaseModel):
    """A logistics carrier with capabilities and constraints."""

    carrier_id: str
    name: str
    capabilities: list[str] = Field(default_factory=list)
    service_regions: list[str] = Field(default_factory=list)
    max_weight_kg: float = Field(ge=0)
    max_volume_m3: float = Field(ge=0)
    accepts_cargo_types: list[CargoType] = Field(default_factory=list)
    accepts_special_handling: list[SpecialHandling] = Field(default_factory=list)
    sla_hours: float = Field(ge=0)
    base_rate_per_kg: float = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RouteSegment(BaseModel):
    """A segment of a logistics route."""

    segment_id: str
    from_location: str
    to_location: str
    transport_mode: str
    distance_km: float = Field(ge=0)
    estimated_hours: float = Field(ge=0)
    tolls_fees: float = 0.0
    notes: str | None = None


class Route(BaseModel):
    """A candidate logistics route."""

    route_id: str
    segments: list[RouteSegment] = Field(default_factory=list)
    total_distance_km: float = Field(ge=0)
    total_estimated_hours: float = Field(ge=0)
    total_tolls_fees: float = 0.0
    risk_score: float = Field(ge=0, le=1)
    notes: str | None = None


class CarrierRouteRecommendation(BaseModel):
    """A joint carrier + route recommendation with explainability."""

    recommendation_id: str
    shipment_id: str
    carrier: Carrier
    route: Route
    confidence: float = Field(ge=0, le=1)
    total_cost_usd: float = Field(ge=0)
    estimated_delivery_hours: float = Field(ge=0)
    sla_met: bool
    satisfied_constraints: list[str] = Field(default_factory=list)
    discarded_constraints: list[str] = Field(default_factory=list)
    trade_offs: list[str] = Field(default_factory=list)
    explanation: str = ""
    risk_level: str = "LOW"
    requires_hitl: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
