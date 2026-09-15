# Integration Candidates

**Date:** 2026-09-15
**Objective:** Select exactly ONE integration for Phase 4.

---

## Candidate Matrix

| Candidate | Problem | Data | CASE Fit | Value | Complexity | Risk | Measurable | Decision |
|-----------|---------|------|----------|-------|------------|------|------------|----------|
| GeoRisk seismic risk | Real seismic events → risk assessment | USGS earthquakes (79M rows, public domain) | HIGH (infrastructure domain) | HIGH | MEDIUM | LOW | YES (latency, accuracy, routing) | **SELECTED** |
| DashLogistics freight cost | Logistics cost prediction | STB/EIA/USDA freight data (public, MIT) | HIGH (logistics domain) | HIGH | MEDIUM | LOW | YES (R2, cost accuracy) | DEFERRED |
| EnRuta freight matching | Rural freight matching | Synthetic data (no real operational data) | MEDIUM | MEDIUM | LOW | MEDIUM | NO (synthetic) | DEFERRED |

---

## Selection: GeoRisk Seismic Risk Integration

### Why This One

1. **Real operational problem:** Seismic risk assessment is a concrete, measurable task
2. **Real public data:** USGS earthquake catalog — 79M rows, public domain, authoritative source
3. **Measurable outcome:** Risk classification accuracy, latency, routing impact
4. **Clean CASE boundary:** Adapter → Pydantic contract → CASE Core → Validation → Risk → Decision
5. **Portfolio value:** Demonstrates CASE handling real-world geospatial risk data
6. **Domain alignment:** Maps directly to CASE infrastructure domain

### Why NOT DashLogistics

- MIT license is better than Academic
- But logistics cost prediction is less dramatic for portfolio
- Can be Phase 5 candidate

### Why NOT EnRuta

- Synthetic data — no real operational value
- No license — legal risk
- Matching logic is interesting but not ready for integration

---

## Data Legality / Provenance

### USGS Earthquake Data

| Field | Value |
|-------|-------|
| Source | USGS Earthquake Hazards Program |
| URL | https://earthquake.usgs.gov/earthquakes/feed/ |
| License | Public domain (US Government work) |
| Provenance | Seismic sensors, global network |
| Version | Real-time feed + historical catalog |
| Access Method | REST API (JSON) + CSV download |
| Personal Data? | NO |
| Sensitive? | NO |
| Commercial Restriction? | NO — public domain |
| Publication Allowed? | YES |
| Transformations | Magnitude normalization, deduplication, H3 cell assignment |

### CASE Integration Scope

- **Ingestion:** Fetch recent earthquakes (M >= 4.5) from USGS API
- **Normalization:** Map to CASE OperationalCase with seismic evidence
- **Risk Assessment:** Use magnitude, depth, location for risk scoring
- **Decision:** Route through CASE pipeline → approve/escalate based on risk level
- **Audit:** Full traceability from USGS data → CASE decision

### What We Will NOT Do

- NOT copy the entire 79M row dataset
- NOT train ML models on seismic data
- NOT introduce PostGIS or geospatial databases
- NOT create a full disaster response system
- ONLY: demonstrate CASE handling real seismic risk data through its existing pipeline
