from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.domain import PredictedDriftZone, PredictionRun, SargassumPatch
from app.utils.geo import bbox_polygon, destination_point, haversine_nm


@dataclass
class DriftInputs:
    wind_direction_degrees: float = 275
    wind_speed_knots: float = 12
    ocean_current_direction_degrees: float = 285
    ocean_current_speed_knots: float = 0.7
    horizon_hours: int = 72


class DriftPredictionService:
    """Simple vector drift model that can later be replaced by oceanographic model output."""

    def run_prediction_for_patch(self, patch: SargassumPatch, inputs: DriftInputs) -> dict:
        future_positions = [
            self.estimate_future_position(patch, inputs, hour)
            for hour in range(12, inputs.horizon_hours + 1, 12)
        ]
        drift_polygon = self.create_prediction_polygon(future_positions, patch.estimated_area_m2)
        confidence = self.calculate_confidence(patch.confidence_score, inputs.horizon_hours)
        impacts = self.identify_possible_coastline_impacts(future_positions)
        return {
            "patch_id": patch.id,
            "horizon_hours": inputs.horizon_hours,
            "future_positions": future_positions,
            "drift_polygon": drift_polygon,
            "possible_impacts": impacts,
            "confidence_score": confidence,
        }


    def persist_prediction_zone(
        self,
        db: Session,
        patch: SargassumPatch,
        inputs: DriftInputs,
        result: dict,
        source_type: str = "prediction",
        notes: str | None = None,
    ) -> tuple[PredictionRun, PredictedDriftZone | None]:
        run = PredictionRun(
            patch_id=patch.id,
            horizon_hours=inputs.horizon_hours,
            input_summary={
                "wind_direction_degrees": inputs.wind_direction_degrees,
                "wind_speed_knots": inputs.wind_speed_knots,
                "ocean_current_direction_degrees": inputs.ocean_current_direction_degrees,
                "ocean_current_speed_knots": inputs.ocean_current_speed_knots,
                "source_type": source_type,
            },
            confidence_score=result["confidence_score"],
        )
        db.add(run)
        db.flush()

        future_positions = result.get("future_positions") or []
        if not future_positions:
            return run, None

        center = future_positions[-1]
        zone = PredictedDriftZone(
            prediction_run_id=run.id,
            patch_id=patch.id,
            center_latitude=center["latitude"],
            center_longitude=center["longitude"],
            impact_timeframe_hours=inputs.horizon_hours,
            severity=patch.severity,
            confidence_score=result["confidence_score"],
            source_type=source_type,
            notes=notes or f"Persisted drift zone for patch {patch.patch_reference}.",
        )
        db.add(zone)
        db.flush()
        return run, zone

    def estimate_future_position(self, patch: SargassumPatch, inputs: DriftInputs, hours: int) -> dict:
        patch_distance = patch.movement_speed_knots * hours
        current_distance = inputs.ocean_current_speed_knots * hours
        wind_leeway_distance = inputs.wind_speed_knots * 0.025 * hours
        lat, lon = destination_point(
            patch.centroid_latitude, patch.centroid_longitude, patch.movement_direction_degrees, patch_distance
        )
        lat, lon = destination_point(lat, lon, inputs.ocean_current_direction_degrees, current_distance)
        lat, lon = destination_point(lat, lon, inputs.wind_direction_degrees, wind_leeway_distance)
        return {"hour": float(hours), "latitude": round(lat, 5), "longitude": round(lon, 5)}

    def create_prediction_polygon(self, future_positions: list[dict], patch_area_m2: float) -> dict:
        if not future_positions:
            return {"type": "Polygon", "coordinates": []}
        center = future_positions[-1]
        uncertainty_nm = max(3.0, min(22.0, (patch_area_m2 or 100000) ** 0.5 / 900))
        return bbox_polygon(center["latitude"], center["longitude"], uncertainty_nm)

    def calculate_confidence(self, patch_confidence: float, horizon_hours: int) -> float:
        horizon_penalty = min(0.35, horizon_hours / 240)
        return round(max(0.2, patch_confidence - horizon_penalty), 2)

    def identify_possible_coastline_impacts(self, future_positions: list[dict]) -> list[dict]:
        # MVP placeholder for geospatial coastline intersection. Demo sites approximate eastern Caribbean.
        watched_coasts = [
            {"name": "Barbados East Coast", "latitude": 13.19, "longitude": -59.43},
            {"name": "Saint Lucia Atlantic Coast", "latitude": 13.91, "longitude": -60.88},
            {"name": "Martinique Southeast Coast", "latitude": 14.47, "longitude": -60.86},
        ]
        impacts: list[dict] = []
        for pos in future_positions:
            for coast in watched_coasts:
                distance = haversine_nm(pos["latitude"], pos["longitude"], coast["latitude"], coast["longitude"])
                if distance < 65:
                    impacts.append(
                        {
                            "zone_name": coast["name"],
                            "distance_nm": round(distance, 1),
                            "estimated_arrival_hours": int(pos["hour"]),
                            "risk": "critical" if distance < 25 else "high",
                        }
                    )
        return impacts
