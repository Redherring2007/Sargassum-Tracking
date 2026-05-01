# Architecture

Sargassum Sentinel is split into a FastAPI backend, PostGIS database, and React operations dashboard.

## Backend

The backend exposes REST endpoints under `/api`. Routers stay thin and delegate prediction, ingestion, patch creation, and routing decisions to service classes. SQLAlchemy models include organisation separation fields where relevant and PostGIS geometry columns for future spatial queries.

## Frontend

The frontend is a responsive command-centre app. The overview screen is the active operational dashboard; individual pages expose map, clients, vessels, tasks, predictions, alerts, admin, and settings views.

## Database

PostgreSQL with PostGIS stores observations, patches, predicted zones, client sites, vessels, positions, routes, tasks, costs, alerts, sources, users, and organisations.

## Data Flow

Observations enter through manual reports, uploads, or future adapters. Patch services group observations into operational patches. Prediction services create drift estimates and persist predicted drift zones. Routing services rank vessel-to-zone recommendations, including collection zones created from confirmed spectral patches. Tasks convert recommendations into collection operations.

## Future Upgrades

Replace the MVP vector drift model with oceanographic model outputs, add raster/vector satellite detections, integrate AIS, add JWT/RBAC, and move background ingestion to Celery workers.


## Spectral Detection

`spectral_detection_service.py` adds Sentinel-2-compatible floating algae detection using B4 red, B8 NIR, and B11 SWIR reflectance grids. It calculates NDVI and FAI, applies lightweight thresholds, emits GeoJSON-compatible point features, and clusters adjacent detections into GeoJSON Polygon features where possible. Demo detection stays read-only. Controlled persistence is exposed through `POST /api/spectral/detect-and-ingest`, which accepts the same band payload as `/api/spectral/detect`, enforces a minimum confidence threshold, writes observations with `source_type=spectral_detection`, skips recent nearby spectral duplicates, and can create one derived patch from accepted detections. The ingest response keeps backward-compatible single-patch fields and adds list/count fields, generated polygon features, spectral collection zone IDs, persisted drift zone IDs, and optional drift predictions when `run_drift_prediction=true`. Cloud, land/shoreline, and sun-glint masks are implemented as local boolean-grid interfaces so future Sentinel/Copernicus adapters can supply real masks without changing route contracts. The current implementation accepts local/mock band arrays and does not yet download Copernicus/Sentinel imagery directly.
