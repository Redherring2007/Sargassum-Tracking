# Sargassum Sentinel

Sargassum Sentinel is an API-first commercial MVP for tracking floating sargassum, forecasting drift, visualising coastline risk, routing vessels, and managing marine collection tasks.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL/PostGIS
- Frontend: React, Vite, TypeScript, Tailwind CSS, Leaflet
- Local services: Docker Compose, PostGIS, Redis placeholder

## Run Locally On Ubuntu

```bash
cd /tmp/sargassum-sentinel
cp .env.example .env
docker compose up --build
```

Seed demo data:

```bash
curl -X POST http://localhost:8000/api/demo/seed
```

Open:

- Frontend dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/api/health

## Development Without Docker

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://sentinel:sentinel@localhost:5432/sargassum
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

- `DATABASE_URL`: SQLAlchemy Postgres/PostGIS connection URL
- `CORS_ORIGINS`: JSON list of allowed frontend origins
- `VITE_API_BASE_URL`: frontend API base URL
- `ENVIRONMENT`: deployment environment label

## MVP Capabilities

- Interactive map with patches, vessels, client sites, collection zones, and recommended route
- Manual and GeoJSON ingestion endpoints
- Sentinel-2-compatible spectral detection demo using B4/B8/B11 NDVI and FAI logic
- Patch generation from observations
- Drift prediction service with replaceable vector model
- Vessel routing and cost ranking
- Collection task board
- Client, vessel, alert, prediction, admin, and settings pages
- Autonomous collection placeholder endpoints

## Deployment Notes

The project is VPS-ready: keep `.env` outside source control, run PostGIS as a managed DB or container, place FastAPI behind Nginx/Caddy, and build the Vite frontend as static assets. Add JWT authentication before exposing paid client accounts.


## Spectral Detection Demo

Run the local Sentinel-2-compatible spectral detector without paid APIs:

```bash
curl http://localhost:8000/api/spectral/demo
```

The endpoint uses mock B4/B8/B11 reflectance grids, calculates NDVI and FAI, thresholds likely floating sargassum pixels, and returns GeoJSON-compatible features. It is not yet a live Copernicus image download pipeline.
