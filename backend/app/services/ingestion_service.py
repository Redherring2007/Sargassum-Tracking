from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.domain import SargassumObservation
from app.schemas.domain import ObservationCreate


class IngestionService:
    def ingest_manual_observation(self, db: Session, payload: ObservationCreate) -> SargassumObservation:
        observation = SargassumObservation(
            latitude=payload.latitude,
            longitude=payload.longitude,
            observed_at=payload.observed_at or datetime.now(UTC),
            source_type=payload.source_type,
            source_reference=payload.source_reference,
            density_level=payload.density_level,
            estimated_area_m2=payload.estimated_area_m2,
            confidence_score=payload.confidence_score,
            notes=payload.notes,
        )
        db.add(observation)
        db.commit()
        db.refresh(observation)
        return observation

    def ingest_geojson_placeholder(self, db: Session, features: list[dict]) -> int:
        accepted = 0
        for feature in features:
            geometry = feature.get("geometry", {})
            props = feature.get("properties", {})
            if geometry.get("type") != "Point":
                continue
            lon, lat = geometry.get("coordinates", [None, None])
            db.add(
                SargassumObservation(
                    latitude=lat,
                    longitude=lon,
                    observed_at=datetime.now(UTC),
                    source_type=props.get("source_type", "geojson_upload"),
                    source_reference=props.get("source_reference"),
                    density_level=props.get("density_level", "medium"),
                    estimated_area_m2=props.get("estimated_area_m2", 60000),
                    confidence_score=props.get("confidence_score", 0.65),
                    notes=props.get("notes"),
                )
            )
            accepted += 1
        db.commit()
        return accepted
