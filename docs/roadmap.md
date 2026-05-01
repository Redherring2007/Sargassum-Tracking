# Roadmap

## Phase 1: MVP Map/Data/Tasking

Operational dashboard, database schema, demo data, manual ingestion, patch tracking, drift foundation, vessel routing, and collection tasks.

## Phase 2: Real Data Integrations

Add production Sentinel-2/Copernicus scene download, cloud/glint/land masking, NOAA/Copernicus/NASA ocean data, weather, drone, patrol vessel, and CSV/GeoJSON production adapters.

## Phase 3: Better Prediction Models

Use real current vectors, wind leeway, uncertainty cones, historical validation, and coastline intersection analysis.

## Phase 4: AIS/Live Vessel Tracking

Integrate AIS and onboard GPS telemetry with background jobs and stale-position alerts.

## Phase 5: Client Subscriptions

JWT auth, role-based dashboards, billing, paid alerts, exports, and white-label client portals.

## Phase 6: Robotic/Autonomous Collection

GPS tasking, polygon mission upload, safe operating boundaries, live telemetry, remote abort, and return-to-dock workflows.

## Phase 7: Commercial API

API keys, rate limits, licensed data feeds, webhooks, and enterprise integrations.


### Spectral Detection Upgrade

Current foundation: local Sentinel-2-compatible B4/B8/B11 NDVI/FAI detection service with mock/demo arrays. Next step: implement authenticated or public Copernicus/ESA/NOAA scene discovery, download, atmospheric correction assumptions, masking, tiling, and scheduled ingestion into observations/patches.
