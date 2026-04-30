# Architecture

Sargassum Sentinel is split into a FastAPI backend, PostGIS database, and React operations dashboard.

## Backend

The backend exposes REST endpoints under `/api`. Routers stay thin and delegate prediction, ingestion, patch creation, and routing decisions to service classes. SQLAlchemy models include organisation separation fields where relevant and PostGIS geometry columns for future spatial queries.

## Frontend

The frontend is a responsive command-centre app. The overview screen is the active operational dashboard; individual pages expose map, clients, vessels, tasks, predictions, alerts, admin, and settings views.

## Database

PostgreSQL with PostGIS stores observations, patches, predicted zones, client sites, vessels, positions, routes, tasks, costs, alerts, sources, users, and organisations.

## Data Flow

Observations enter through manual reports, uploads, or future adapters. Patch services group observations into operational patches. Prediction services create drift estimates and risk signals. Routing services rank vessel-to-zone recommendations. Tasks convert recommendations into collection operations.

## Future Upgrades

Replace the MVP vector drift model with oceanographic model outputs, add raster/vector satellite detections, integrate AIS, add JWT/RBAC, and move background ingestion to Celery workers.
