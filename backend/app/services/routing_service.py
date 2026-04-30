from dataclasses import dataclass

from app.models.domain import CollectionZone, Vessel, VesselPosition
from app.utils.geo import haversine_nm, linestring


@dataclass
class RouteScore:
    score: float
    action: str
    reasoning: str


class RoutingService:
    severity_weight = {"low": 15, "medium": 35, "high": 65, "critical": 90}

    def recommend_route(
        self, vessel: Vessel, position: VesselPosition, zone: CollectionZone, client_priority: int = 3
    ) -> dict:
        distance_nm = haversine_nm(position.latitude, position.longitude, zone.center_latitude, zone.center_longitude)
        speed = max(vessel.working_speed_knots, 1)
        travel_hours = distance_nm / speed
        collection_hours = min(8.0, max(1.0, zone.estimated_volume_kg / max(vessel.collection_capacity_kg, 1) * 4))
        estimated_cost = (travel_hours + collection_hours) * (
            vessel.fuel_cost_per_hour + vessel.operating_cost_per_hour
        )
        score = self.calculate_score(vessel, zone, distance_nm, estimated_cost, client_priority)
        return {
            "vessel_id": vessel.id,
            "vessel_name": vessel.vessel_name,
            "collection_zone_id": zone.id,
            "zone_name": zone.zone_name,
            "distance_nm": round(distance_nm, 2),
            "estimated_travel_hours": round(travel_hours, 2),
            "estimated_cost": round(estimated_cost, 2),
            "estimated_collection_quantity_kg": min(vessel.collection_capacity_kg, zone.estimated_volume_kg),
            "estimated_time_to_complete": round(travel_hours + collection_hours, 2),
            "recommendation_score": round(score.score, 1),
            "action": score.action,
            "reasoning_summary": score.reasoning,
            "route_geojson": linestring(
                [(position.latitude, position.longitude), (zone.center_latitude, zone.center_longitude)]
            ),
        }

    def calculate_score(
        self, vessel: Vessel, zone: CollectionZone, distance_nm: float, estimated_cost: float, client_priority: int = 3
    ) -> RouteScore:
        severity = self.severity_weight.get(str(zone.severity.value if hasattr(zone.severity, "value") else zone.severity), 35)
        capacity_fit = min(25, (vessel.collection_capacity_kg / max(zone.estimated_volume_kg, 1)) * 20)
        priority = zone.priority_score * 0.4 + client_priority * 6
        distance_penalty = min(35, distance_nm * 1.5)
        cost_penalty = min(35, estimated_cost / 250)
        confidence_bonus = zone.confidence_score * 15
        score = severity + capacity_fit + priority + confidence_bonus - distance_penalty - cost_penalty
        if score >= 85:
            action = "collect_now"
            reason = "High operational value with acceptable travel and cost profile."
        elif score >= 55:
            action = "schedule"
            reason = "Worth collecting, but timing should be coordinated with vessel availability."
        elif score >= 35:
            action = "monitor"
            reason = "Keep under watch; current cost or confidence does not justify immediate dispatch."
        else:
            action = "wait_or_redirect"
            reason = "Cost outweighs likely benefit unless risk increases."
        return RouteScore(score=max(0, score), action=action, reasoning=reason)

    def rank_vessels_for_zone(
        self, vessels: list[Vessel], positions: dict[int, VesselPosition], zone: CollectionZone
    ) -> list[dict]:
        recommendations = [
            self.recommend_route(vessel, positions[vessel.id], zone)
            for vessel in vessels
            if vessel.id in positions and str(vessel.status.value if hasattr(vessel.status, "value") else vessel.status) != "offline"
        ]
        return sorted(recommendations, key=lambda item: item["recommendation_score"], reverse=True)
