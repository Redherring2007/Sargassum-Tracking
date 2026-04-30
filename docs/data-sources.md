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
