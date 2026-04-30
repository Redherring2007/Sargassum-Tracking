# Data Sources

MVP adapters are placeholders that do not require paid APIs.

Prepared sources:

- Manual sighting reports
- CSV and GeoJSON uploads
- Satellite detection placeholder
- NOAA/Copernicus/NASA-style current and wind placeholders
- AIS vessel location placeholder
- Drone and patrol boat observations

Production integrations should run as background jobs, retain source metadata, and store confidence scores for downstream prediction and routing.


## Live MVP Integrations

- NOAA/AOML Sargassum Inundation Report is used as an authoritative regional-risk reference.
- iNaturalist public observations provide real geotagged Sargassum sightings for MVP map ingestion. These are citizen observations, not satellite detections.
- Open-Meteo Marine provides no-key ocean current direction and velocity for live drift estimates.

Production satellite ingestion should still be added through NOAA CoastWatch/ERDDAP, USF SaWS/AFAI-derived products, or a licensed/hosted raster processing pipeline.
