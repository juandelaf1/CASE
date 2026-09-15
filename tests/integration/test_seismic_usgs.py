"""Integration tests for seismic risk domain with live USGS API.

Requires: network access to earthquake.usgs.gov.
Skipped automatically when USGS API is unreachable.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, "src")

from usgs_adapter.client import USGSClient


def _usgs_available() -> bool:
    try:
        client = USGSClient(timeout=10.0)
        return client.health_check()
    except Exception:
        return False


REQUIRES_USGS = pytest.mark.skipif(
    not _usgs_available(),
    reason="USGS API unreachable — skipping live integration test",
)


@pytest.fixture
def usgs_client():
    return USGSClient(timeout=15.0, min_magnitude=4.5, lookback_days=7)


@REQUIRES_USGS
class TestUSGSLiveFetchRecent:
    @pytest.mark.asyncio
    async def test_fetch_returns_events(self, usgs_client):
        events = usgs_client.fetch_recent()
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_events_have_valid_data(self, usgs_client):
        events = usgs_client.fetch_recent()
        for event in events[:5]:
            assert event.event_id != ""
            assert event.magnitude >= 4.5
            assert event.depth_km >= 0
            assert event.place != ""
            assert event.timestamp != ""

    @pytest.mark.asyncio
    async def test_events_are_sorted_by_time(self, usgs_client):
        events = usgs_client.fetch_recent()
        if len(events) >= 2:
            timestamps = [e.timestamp for e in events]
            assert timestamps == sorted(timestamps, reverse=True)


@REQUIRES_USGS
class TestUSGSLivePipeline:
    @pytest.mark.asyncio
    async def test_seismic_event_to_case(self, usgs_client):
        from case_core.contracts.evidence import EvidenceItem, EvidenceType
        from case_core.contracts.operational_case import OperationalCase

        events = usgs_client.fetch_recent()
        assert len(events) > 0

        event = events[0]
        case = OperationalCase(
            case_id=f"SEISMIC-LIVE-{event.event_id[:8]}",
            report_text=f"M{event.magnitude} earthquake at {event.place}",
            domain="seismic_risk",
            urgency="MEDIUM",
            evidence=[
                EvidenceItem(
                    id="ev-live-001",
                    type=EvidenceType.METRIC,
                    content=f"magnitude={event.magnitude},depth={event.depth_km}",
                    source="usgs",
                    confidence=0.95,
                    extracted_at=event.timestamp,
                )
            ],
            metadata={
                "magnitude": event.magnitude,
                "depth_km": event.depth_km,
                "tsunami": event.tsunami,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "place": event.place,
                "usgs_event_id": event.event_id,
            },
        )

        assert case.domain == "seismic_risk"
        assert case.metadata["magnitude"] == event.magnitude

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mock_provider(self, usgs_client):
        from case_core.composition import create_app_dependencies
        from case_core.contracts.evidence import EvidenceItem, EvidenceType
        from case_core.contracts.operational_case import OperationalCase

        os.environ["CASE_PROVIDER"] = "mock"
        deps = create_app_dependencies()
        os.environ.pop("CASE_PROVIDER", None)

        events = usgs_client.fetch_recent()
        assert len(events) > 0

        event = events[0]
        case = OperationalCase(
            case_id=f"SEISMIC-PIPELINE-{event.event_id[:8]}",
            report_text=f"M{event.magnitude} earthquake at {event.place}",
            domain="seismic_risk",
            urgency="MEDIUM",
            evidence=[
                EvidenceItem(
                    id="ev-pipeline-001",
                    type=EvidenceType.METRIC,
                    content=f"magnitude={event.magnitude},depth={event.depth_km}",
                    source="usgs",
                    confidence=0.95,
                    extracted_at=event.timestamp,
                )
            ],
            metadata={
                "magnitude": event.magnitude,
                "depth_km": event.depth_km,
                "tsunami": event.tsunami,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "place": event.place,
            },
        )

        result = await deps.engine.execute(case)

        assert result.decision is not None
        assert result.decision.action in ["approve", "reject", "escalate"]
        assert result.decision.urgency in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert 0 <= result.decision.confidence <= 1
        assert result.decision.processing_time_ms > 0
