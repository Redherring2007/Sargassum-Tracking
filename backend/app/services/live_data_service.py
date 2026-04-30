from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.domain import SargassumObservation, SargassumPatch
from app.services.drift_prediction_service import DriftInputs


DEFAULT_BBOX = {
    "swlat": 5.0,
    "swlng": -90.0,
    "nelat": 30.0,
    "nelng": -45.0,
}


class LiveDataService:
    inaturalist_url = "https://api.inaturalist.org/v1/observations"
    open_meteo_url = "https://marine-api.open-meteo.com/v1/marine"
    sir_report_url = "https://www.aoml.noaa.gov/phod/sargassum_inundation_report"

    def available_sources(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "NOAA/AOML Sargassum Inundation Report",
                "source_type": "regional_risk_reference",
                "url": self.sir_report_url,
                "status": "reference",
                "notes": "Authoritative SIR product for regional inundation context; used as advisory context in the MVP.",
            },
            {
                "name": "iNaturalist public Sargassum observations",
                "source_type": "citizen_science_observations",
                "url": "https://api.inaturalist.org/v1/observations",
                "status": "live",
                "notes": "Public geotagged observations; useful for current sightings but not a satellite detection feed.",
            },
            {
                "name": "Open-Meteo Marine Forecast",
                "source_type": "ocean_current_forecast",
                "url": self.open_meteo_url,
                "status": "live",
                "notes": "No-key marine current direction and velocity used to improve drift estimates.",
            },
        ]

    def fetch_inaturalist_observations(self, days: int = 120, limit: int = 75, bbox: dict[str, float] | None = None) -> list[dict[str, Any]]:
        bbox = bbox or DEFAULT_BBOX
        start_date = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
        params = {
            "taxon_name": "Sargassum",
            "geo": "true",
            "mappable": "true",
            "d1": start_date,
            "order_by": "observed_on",
            "order": "desc",
            "per_page": min(limit, 200),
            **bbox,
        }
        with httpx.Client(timeout=20, headers={"User-Agent": "SargassumSentinel/0.1"}) as client:
            response = client.get(self.inaturalist_url, params=params)
            response.raise_for_status()
            payload = response.json()
        records = []
        for item in payload.get("results", []):
            coords = (item.get("geojson") or {}).get("coordinates")
            if not coords or len(coords) < 2:
                continue
            observed_at = self._parse_observed_at(item.get("observed_on") or item.get("time_observed_at"))
            taxon = item.get("taxon") or {}
            records.append(
                {
                    "external_id": str(item.get("id")),
                    "latitude": float(coords[1]),
                    "longitude": float(coords[0]),
                    "observed_at": observed_at,
                    "source_reference": item.get("uri") or f"https://www.inaturalist.org/observations/{item.get('id')}",
                    "taxon_name": taxon.get("name") or "Sargassum",
                    "common_name": taxon.get("preferred_common_name") or "Sargassum",
                    "place_guess": item.get("place_guess"),
                    "quality_grade": item.get("quality_grade"),
                }
            )
        return records

    def ingest_live_observations(self, db: Session, days: int = 120, limit: int = 75) -> dict[str, Any]:
        records = self.fetch_inaturalist_observations(days=days, limit=limit)
        created = 0
        skipped = 0
        for record in records:
            exists = (
                db.query(SargassumObservation)
                .filter(SargassumObservation.source_reference == record["source_reference"])
                .first()
            )
            if exists:
                skipped += 1
                continue
            db.add(
                SargassumObservation(
                    latitude=record["latitude"],
                    longitude=record["longitude"],
                    observed_at=record["observed_at"],
                    source_type="inaturalist_public_observation",
                    source_reference=record["source_reference"],
                    density_level="unknown",
                    estimated_area_m2=2500,
                    confidence_score=0.45,
                    notes=f"{record['common_name']} public observation near {record.get('place_guess') or 'unknown location'}; grade={record.get('quality_grade')}",
                )
            )
            created += 1
        db.commit()
        return {
            "source": "iNaturalist",
            "fetched": len(records),
            "created": created,
            "skipped_duplicates": skipped,
            "bbox": DEFAULT_BBOX,
            "notes": "Citizen observations are real public sightings, not satellite-derived offshore mats.",
        }

    def fetch_marine_current(self, latitude: float, longitude: float) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "ocean_current_velocity,ocean_current_direction,wave_height,sea_surface_temperature",
            "timezone": "GMT",
            "cell_selection": "sea",
        }
        with httpx.Client(timeout=20, headers={"User-Agent": "SargassumSentinel/0.1"}) as client:
            response = client.get(self.open_meteo_url, params=params)
            response.raise_for_status()
            payload = response.json()
        current = payload.get("current") or {}
        units = payload.get("current_units") or {}
        velocity = current.get("ocean_current_velocity")
        velocity_knots = self._velocity_to_knots(velocity, units.get("ocean_current_velocity")) if velocity is not None else None
        return {
            "latitude": payload.get("latitude", latitude),
            "longitude": payload.get("longitude", longitude),
            "time": current.get("time"),
            "ocean_current_velocity": velocity,
            "ocean_current_velocity_unit": units.get("ocean_current_velocity"),
            "ocean_current_speed_knots": velocity_knots,
            "ocean_current_direction_degrees": current.get("ocean_current_direction"),
            "wave_height_m": current.get("wave_height"),
            "sea_surface_temperature_c": current.get("sea_surface_temperature"),
            "source": "Open-Meteo Marine",
        }

    def drift_inputs_from_live_current(self, patch: SargassumPatch, horizon_hours: int = 72) -> DriftInputs:
        current = self.fetch_marine_current(patch.centroid_latitude, patch.centroid_longitude)
        return DriftInputs(
            wind_direction_degrees=patch.movement_direction_degrees,
            wind_speed_knots=10,
            ocean_current_direction_degrees=current.get("ocean_current_direction_degrees") or patch.movement_direction_degrees,
            ocean_current_speed_knots=current.get("ocean_current_speed_knots") or patch.movement_speed_knots,
            horizon_hours=horizon_hours,
        )

    def _parse_observed_at(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)
        try:
            if len(value) == 10:
                return datetime.fromisoformat(value).replace(tzinfo=UTC)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(UTC)

    def _velocity_to_knots(self, value: float, unit: str | None) -> float:
        unit = (unit or "").lower()
        if "km/h" in unit or "kmh" in unit:
            return round(value * 0.539957, 3)
        if "m/s" in unit:
            return round(value * 1.94384, 3)
        if "kn" in unit or "kt" in unit:
            return round(value, 3)
        return round(value * 0.539957, 3)
