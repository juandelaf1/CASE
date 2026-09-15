# Portfolio Discovery

**Date:** 2026-09-15
**Objective:** Inspect author's GitHub repos for reusable data, models, APIs, and domain logic.

---

## 1. GeoRisk_Finder

| Field | Value |
|-------|-------|
| URL | https://github.com/juandelaf1/GeoRisk_Finder |
| Purpose | Climate risk intelligence with 3D globe, H3 cells, actuarial model |
| Domain | Geological/climate risk |
| Data | USGS earthquakes (79M rows), IBTrACS cyclones (46M rows), volcanoes (7.5K rows), GDACS live alerts |
| Models | K-Means clustering, DBSCAN, preprocessing pipeline (Log1p + OneHot + Scaler + PCA) |
| APIs | USGS Earthquake Hazards API, GDACS, Uber H3 |
| Business Logic | Multi-hazard risk classification, H3 spatial grid, feature engineering (15 features), financial ROI model |
| License | Academic/Open (no formal OSS license) |
| Data License | USGS/NOAA/IGN (public domain — US Government work) |
| Reusability | HIGH — USGS ingestion module, H3 grid, preprocessing pipeline are cleanly separated |
| CASE Relevance | HIGH — real seismic risk data maps to CASE infrastructure domain |
| Potential Adapter | USGS ingestion → CASE OperationalCase with seismic evidence |
| Value | HIGH — real public data, measurable outcomes, clean boundary |
| Complexity | MEDIUM — data ingestion + feature engineering + risk scoring |
| Risk | LOW — public data, well-documented provenance |

---

## 2. DashLogistics

| Field | Value |
|-------|-------|
| URL | https://github.com/juandelaf1/DashLogistics |
| Purpose | Multi-market logistics intelligence for US freight |
| Domain | Logistics |
| Data | STB freight data, AAA fuel prices, EIA fuel prices, FAF freight flows, USDA truck rates, weather |
| Models | ML cost prediction (R2=0.987), 15+ KPIs, efficiency scoring |
| APIs | EIA API, weather API, OSRM routing |
| Business Logic | ETL pipeline (9 steps), dbt transformations, cost estimation, regional benchmarking |
| License | MIT |
| Data License | Public government data (STB, EIA, USDA, Census, FAF) |
| Reusability | HIGH — ETL pipeline, KPIs, cost prediction model |
| CASE Relevance | HIGH — logistics domain matches CASE LogisticsPolicy |
| Potential Adapter | Logistics data → CASE OperationalCase with freight/logistics evidence |
| Value | HIGH — real public data, MIT license, clean ETL |
| Complexity | MEDIUM — data ingestion + cost model + KPI computation |
| Risk | LOW — public data, MIT license, well-structured |

---

## 3. EnRuta

| Field | Value |
|-------|-------|
| URL | https://github.com/juandelaf1/EnRuta |
| Purpose | Collaborative rural logistics platform |
| Domain | Rural logistics (Spain) |
| Data | Spanish provinces/municipalities (real), producers/truckers/offers/demands (synthetic) |
| Models | Matching engine (offer × demand scoring), detour calculation, CO2 estimation |
| APIs | OSRM routing, OpenWeatherMap, INE population API |
| Business Logic | Freight matching, detour analysis, weather-aware routing, CO2 savings |
| License | None declared |
| Data License | INE (public), synthetic for operational data |
| Reusability | MEDIUM — matching engine is interesting but data is synthetic |
| CASE Relevance | MEDIUM — rural logistics is niche, synthetic data limits value |
| Potential Adapter | Matching engine → CASE offer-demand matching |
| Value | MEDIUM — interesting logic but synthetic data |
| Complexity | LOW — simple matching algorithm |
| Risk | MEDIUM — no license, synthetic data |

---

## Summary

| Repo | Data Quality | License | CASE Fit | Value | Complexity | Risk |
|------|-------------|---------|----------|-------|------------|------|
| GeoRisk_Finder | HIGH (real public data) | Academic | HIGH | HIGH | MEDIUM | LOW |
| DashLogistics | HIGH (real public data) | MIT | HIGH | HIGH | MEDIUM | LOW |
| EnRuta | LOW (synthetic) | None | MEDIUM | MEDIUM | LOW | MEDIUM |
