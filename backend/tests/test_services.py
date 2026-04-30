from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.domain import CollectionTask, SargassumObservation
from app.services.drift_prediction_service import DriftInputs, DriftPredictionService
from app.services.patch_service import PatchService
from app.services.routing_service import RoutingService


def test_patch_creation_from_observations():
    observations = [
        SargassumObservation(
            latitude=13.4,
            longitude=-58.7,
            observed_at=datetime.now(UTC),
            estimated_area_m2=120000,
            confidence_score=0.75,
        ),
        SargassumObservation(
            latitude=13.5,
            longitude=-58.8,
            observed_at=datetime.now(UTC),
            estimated_area_m2=150000,
            confidence_score=0.8,
        ),
    ]
    patch = PatchService().create_patch_from_observations(observations)
    assert patch.estimated_area_m2 == 270000
    assert patch.confidence_score > 0.75


def test_drift_prediction_service():
    patch = SimpleNamespace(
        id=1,
        centroid_latitude=13.4,
        centroid_longitude=-58.7,
        movement_direction_degrees=280,
        movement_speed_knots=0.8,
        estimated_area_m2=250000,
        confidence_score=0.75,
    )
    result = DriftPredictionService().run_prediction_for_patch(patch, DriftInputs(horizon_hours=24))
    assert result["future_positions"]
    assert result["drift_polygon"]["type"] == "Polygon"
    assert 0 < result["confidence_score"] <= 1


def test_routing_score_calculation():
    vessel = SimpleNamespace(collection_capacity_kg=4000)
    zone = SimpleNamespace(severity="high", priority_score=80, confidence_score=0.75, estimated_volume_kg=3500)
    score = RoutingService().calculate_score(vessel, zone, distance_nm=18, estimated_cost=1600, client_priority=5)
    assert score.score > 0
    assert score.action in {"collect_now", "schedule", "monitor", "wait_or_redirect"}


def test_task_model_creation():
    task = CollectionTask(
        task_reference="TASK-TEST-001",
        collection_zone_id=1,
        assigned_vessel_id=2,
        priority="high",
        estimated_volume_kg=2500,
        estimated_cost=900,
        estimated_duration=4.5,
    )
    assert task.task_reference == "TASK-TEST-001"
    assert task.estimated_cost == 900
