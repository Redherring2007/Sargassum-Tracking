from datetime import UTC, datetime

from app.models.domain import SargassumObservation, SargassumPatch


class PatchService:
    def create_patch_from_observations(self, observations: list[SargassumObservation]) -> SargassumPatch:
        if not observations:
            raise ValueError("At least one observation is required")
        lat = sum(o.latitude for o in observations) / len(observations)
        lon = sum(o.longitude for o in observations) / len(observations)
        area = sum(o.estimated_area_m2 or 60000 for o in observations)
        confidence = min(0.95, sum(o.confidence_score for o in observations) / len(observations) + 0.08)
        severity = "critical" if area > 750000 else "high" if area > 350000 else "medium" if area > 100000 else "low"
        return SargassumPatch(
            patch_reference=f"PATCH-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            severity=severity,
            centroid_latitude=lat,
            centroid_longitude=lon,
            estimated_area_m2=area,
            density_level="high" if area > 350000 else "medium",
            movement_direction_degrees=280,
            movement_speed_knots=0.8,
            last_observed_at=max(o.observed_at for o in observations),
            confidence_score=round(confidence, 2),
            source_type="derived_observations",
            source_reference="manual_grouping",
            notes=f"Generated from {len(observations)} nearby observations.",
        )
