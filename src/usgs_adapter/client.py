"""USGS Earthquake Hazards API adapter.

Fetches recent seismic events (M >= 4.5) from the USGS FDSNWS API.
No CASE core imports — respects I12/I13 invariants.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USGS_BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DEFAULT_MIN_MAGNITUDE = 4.5
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_TIMEOUT_SECONDS = 15
MAX_EVENTS_PER_REQUEST = 2000
RATE_LIMIT_DELAY_SECONDS = 1.0


@dataclass
class SeismicEvent:
    """Normalized seismic event from USGS."""

    event_id: str
    magnitude: float
    depth_km: float
    latitude: float
    longitude: float
    place: str
    timestamp: str
    felt_count: int
    tsunami: bool
    event_type: str = "earthquake"
    mag_type: str = ""
    significance: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "magnitude": self.magnitude,
            "depth_km": self.depth_km,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "place": self.place,
            "timestamp": self.timestamp,
            "felt_count": self.felt_count,
            "tsunami": self.tsunami,
            "event_type": self.event_type,
            "mag_type": self.mag_type,
            "significance": self.significance,
        }


class USGSClient:
    """Client for USGS Earthquake Hazards API."""

    def __init__(
        self,
        base_url: str = USGS_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._min_magnitude = min_magnitude
        self._lookback_days = lookback_days

    def _build_params(self) -> dict[str, str]:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self._lookback_days)
        return {
            "format": "geojson",
            "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "minmagnitude": str(self._min_magnitude),
            "orderby": "time",
            "limit": str(MAX_EVENTS_PER_REQUEST),
        }

    def _parse_event(self, feature: dict[str, Any]) -> SeismicEvent | None:
        try:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            return SeismicEvent(
                event_id=feature["id"],
                magnitude=props.get("mag", 0.0),
                depth_km=coords[2] if len(coords) > 2 else 0.0,
                latitude=coords[1],
                longitude=coords[0],
                place=props.get("place", "Unknown location"),
                timestamp=datetime.fromtimestamp(
                    props.get("time", 0) / 1000, tz=timezone.utc
                ).isoformat(),
                felt_count=props.get("felt", 0) or 0,
                tsunami=bool(props.get("tsunami", 0)),
                event_type=props.get("type", "earthquake"),
                mag_type=props.get("magType", ""),
                significance=props.get("sig", 0),
            )
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Failed to parse USGS event: %s", e)
            return None

    def fetch_recent(self) -> list[SeismicEvent]:
        """Fetch recent earthquakes from USGS API.

        Returns:
            List of SeismicEvent objects, empty list on error.
        """
        params = self._build_params()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(self._base_url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            logger.error("USGS API timeout after %.1fs", self._timeout)
            return []
        except httpx.HTTPStatusError as e:
            logger.error("USGS API HTTP error: %s", e.response.status_code)
            return []
        except Exception as e:
            logger.error("USGS API error: %s", e)
            return []

        features = data.get("features", [])
        events: list[SeismicEvent] = []
        for feature in features:
            event = self._parse_event(feature)
            if event is not None:
                events.append(event)

        logger.info("Fetched %d seismic events from USGS (M >= %.1f)", len(events), self._min_magnitude)
        return events

    def fetch_single(self, event_id: str) -> SeismicEvent | None:
        """Fetch a single earthquake by USGS event ID."""
        params = {"format": "geojson"}
        url = f"{self._base_url.rsplit('/', 2)[0]}/event/{event_id}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.error("Failed to fetch event %s: %s", event_id, e)
            return None

        return self._parse_event(data)

    def health_check(self) -> bool:
        """Check if USGS API is reachable."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self._base_url, params={"format": "geojson", "limit": "1"})
                return response.status_code == 200
        except Exception:
            return False
