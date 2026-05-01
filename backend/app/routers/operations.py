from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import (
    Alert,
    ClientSite,
    CollectionTask,
    CollectionZone,
    PredictedDriftZone,
    PredictionRun,
    SargassumObservation,
    SargassumPatch,
    Vessel,
    VesselPosition,
)
from app.schemas.domain import (
    AlertRead,
    ClientSiteRead,
    CollectionZoneRead,
    ObservationCreate,
    ObservationRead,
    PatchRead,
    PredictionRequest,
    PredictionResponse,
    RouteRecommendation,
    TaskCreate,
    TaskRead,
    UploadResponse,
    VesselPositionCreate,
    VesselPositionRead,
    VesselRead,
)
from app.services.demo_seed import seed_demo_data
from app.services.drift_prediction_service import DriftInputs, DriftPredictionService
from app.services.ingestion_service import IngestionService
from app.services.live_data_service import LiveDataService
from app.services.patch_service import PatchService
from app.services.routing_service import RoutingService
from app.services.spectral_detection_service import SpectralDetectionService

router = APIRouter()






@router.get("/spectral/demo", tags=["spectral-detection"])
def spectral_detection_demo():
    return SpectralDetectionService().run_mock_detection()


@router.post("/spectral/detect", tags=["spectral-detection"])
def spectral_detect(payload: dict):
    red, nir, swir = _extract_spectral_bands(payload)
    service = SpectralDetectionService()
    masks = service.masks_from_payload(payload)
    try:
        return service.run_detection(red, nir, swir, masks=masks)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/spectral/detect-and-ingest", tags=["spectral-detection"])
def spectral_detect_and_ingest(
    payload: dict,
    min_confidence: float = Query(default=0.65, ge=0, le=1),
    duplicate_distance_nm: float = Query(default=0.1, ge=0, le=5),
    duplicate_window_hours: int = Query(default=24, ge=1, le=720),
    create_patch: bool = Query(default=True),
    run_drift_prediction: bool = Query(default=False),
    drift_horizon_hours: int = Query(default=72, ge=12, le=240),
    db: Session = Depends(get_db),
):
    red, nir, swir = _extract_spectral_bands(payload)
    source_reference = payload.get("source_reference") or f"spectral_scene_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    service = SpectralDetectionService()
    masks = service.masks_from_payload(payload)
    try:
        detection = service.run_detection(red, nir, swir, masks=masks)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return service.ingest_detection_result(
        db,
        detection,
        source_reference=source_reference,
        min_confidence=min_confidence,
        duplicate_distance_nm=duplicate_distance_nm,
        duplicate_window_hours=duplicate_window_hours,
        create_patch=create_patch,
        run_drift_prediction=run_drift_prediction,
        drift_horizon_hours=drift_horizon_hours,
    )


def _extract_spectral_bands(payload: dict) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    try:
        return payload["red_band"], payload["nir_band"], payload["swir_band"]
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing required band grid: {exc.args[0]}") from exc


@router.get("/live/sources", tags=["live-data"])
def live_sources():
    return LiveDataService().available_sources()


@router.post("/live/ingest-observations", tags=["live-data"])
def ingest_live_observations(
    days: int = Query(default=120, ge=1, le=365),
    limit: int = Query(default=75, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return LiveDataService().ingest_live_observations(db, days=days, limit=limit)


@router.get("/live/environment", tags=["live-data"])
def live_environment(latitude: float, longitude: float):
    return LiveDataService().fetch_marine_current(latitude, longitude)


@router.post("/predictions/run-live/{patch_id}", response_model=PredictionResponse, tags=["predictions"])
def run_live_prediction(patch_id: int, horizon_hours: int = Query(default=72, ge=1, le=240), db: Session = Depends(get_db)):
    patch = db.get(SargassumPatch, patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    live_service = LiveDataService()
    inputs = live_service.drift_inputs_from_live_current(patch, horizon_hours=horizon_hours)
    drift_service = DriftPredictionService()
    result = drift_service.run_prediction_for_patch(patch, inputs)
    drift_service.persist_prediction_zone(
        db,
        patch,
        inputs,
        result,
        source_type="open_meteo_live",
        notes="Persisted from live Open-Meteo prediction request.",
    )
    db.commit()
    return result


@router.get("/observations", response_model=list[ObservationRead], tags=["observations"])
def list_observations(db: Session = Depends(get_db)):
    return db.query(SargassumObservation).order_by(SargassumObservation.observed_at.desc()).all()


@router.post("/observations", response_model=ObservationRead, tags=["observations"])
def create_observation(payload: ObservationCreate, db: Session = Depends(get_db)):
    return IngestionService().ingest_manual_observation(db, payload)


@router.post("/patches/from-observations", response_model=PatchRead, tags=["patches"])
def create_patch_from_observations(observation_ids: list[int], db: Session = Depends(get_db)):
    observations = db.query(SargassumObservation).filter(SargassumObservation.id.in_(observation_ids)).all()
    patch = PatchService().create_patch_from_observations(observations)
    db.add(patch)
    db.commit()
    db.refresh(patch)
    return patch


@router.get("/patches", response_model=list[PatchRead], tags=["patches"])
def list_patches(db: Session = Depends(get_db)):
    return db.query(SargassumPatch).order_by(SargassumPatch.updated_at.desc()).all()


@router.post("/predictions/run", response_model=PredictionResponse, tags=["predictions"])
def run_prediction(payload: PredictionRequest, db: Session = Depends(get_db)):
    patch = db.get(SargassumPatch, payload.patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    inputs = DriftInputs(
        wind_direction_degrees=payload.wind_direction_degrees,
        wind_speed_knots=payload.wind_speed_knots,
        ocean_current_direction_degrees=payload.ocean_current_direction_degrees,
        ocean_current_speed_knots=payload.ocean_current_speed_knots,
        horizon_hours=payload.horizon_hours,
    )
    drift_service = DriftPredictionService()
    result = drift_service.run_prediction_for_patch(patch, inputs)
    drift_service.persist_prediction_zone(
        db,
        patch,
        inputs,
        result,
        source_type="manual_prediction",
        notes="Persisted from manual prediction request.",
    )
    db.commit()
    return result




@router.get("/predictions/live-tracks", tags=["predictions"])
def live_prediction_tracks(horizon_hours: int = Query(default=72, ge=1, le=240), db: Session = Depends(get_db)):
    live_service = LiveDataService()
    drift_service = DriftPredictionService()
    tracks = []
    for patch in db.query(SargassumPatch).order_by(SargassumPatch.severity.desc(), SargassumPatch.updated_at.desc()).all():
        try:
            inputs = live_service.drift_inputs_from_live_current(patch, horizon_hours=horizon_hours)
            environment = {
                "ocean_current_direction_degrees": inputs.ocean_current_direction_degrees,
                "ocean_current_speed_knots": inputs.ocean_current_speed_knots,
                "source": "Open-Meteo Marine current",
            }
        except Exception as exc:
            inputs = DriftInputs(
                wind_direction_degrees=patch.movement_direction_degrees,
                wind_speed_knots=10,
                ocean_current_direction_degrees=patch.movement_direction_degrees,
                ocean_current_speed_knots=patch.movement_speed_knots,
                horizon_hours=horizon_hours,
            )
            environment = {
                "source": "patch movement fallback",
                "error": str(exc),
                "ocean_current_direction_degrees": inputs.ocean_current_direction_degrees,
                "ocean_current_speed_knots": inputs.ocean_current_speed_knots,
            }
        result = drift_service.run_prediction_for_patch(patch, inputs)
        tracks.append(
            {
                "patch_id": patch.id,
                "patch_reference": patch.patch_reference,
                "severity": patch.severity.value if hasattr(patch.severity, "value") else patch.severity,
                "start": {"latitude": patch.centroid_latitude, "longitude": patch.centroid_longitude},
                "future_positions": result["future_positions"],
                "drift_polygon": result["drift_polygon"],
                "possible_impacts": result["possible_impacts"],
                "confidence_score": result["confidence_score"],
                "environment": environment,
            }
        )
    return {"horizon_hours": horizon_hours, "tracks": tracks}


@router.get("/predictions", tags=["predictions"])
def list_predictions(db: Session = Depends(get_db)):
    runs = db.query(PredictionRun).order_by(PredictionRun.created_at.desc()).all()
    zones = db.query(PredictedDriftZone).order_by(PredictedDriftZone.created_at.desc()).all()
    return {"runs": runs, "zones": zones}


@router.get("/risk-zones", tags=["risk"])
def list_risk_zones(db: Session = Depends(get_db)):
    return db.query(PredictedDriftZone).order_by(PredictedDriftZone.impact_timeframe_hours.asc()).all()


@router.get("/collection-zones", response_model=list[CollectionZoneRead], tags=["collection-zones"])
def list_collection_zones(db: Session = Depends(get_db)):
    return db.query(CollectionZone).order_by(CollectionZone.priority_score.desc()).all()


@router.get("/client-sites", response_model=list[ClientSiteRead], tags=["clients"])
def list_client_sites(db: Session = Depends(get_db)):
    return db.query(ClientSite).order_by(ClientSite.priority_level.desc()).all()


@router.get("/vessels", response_model=list[VesselRead], tags=["vessels"])
def list_vessels(db: Session = Depends(get_db)):
    return db.query(Vessel).order_by(Vessel.vessel_name.asc()).all()


@router.get("/vessel-positions", response_model=list[VesselPositionRead], tags=["vessels"])
def list_vessel_positions(db: Session = Depends(get_db)):
    return db.query(VesselPosition).order_by(VesselPosition.timestamp.desc()).all()


@router.post("/vessel-positions", response_model=VesselPositionRead, tags=["vessels"])
def create_vessel_position(payload: VesselPositionCreate, db: Session = Depends(get_db)):
    position = VesselPosition(
        vessel_id=payload.vessel_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        heading=payload.heading,
        speed=payload.speed,
        timestamp=payload.timestamp or datetime.now(UTC),
        source_type=payload.source_type,
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@router.get("/routes/recommendations", response_model=list[RouteRecommendation], tags=["routes"])
def route_recommendations(db: Session = Depends(get_db)):
    vessels = db.query(Vessel).all()
    zones = db.query(CollectionZone).all()
    latest_positions = {}
    for vessel in vessels:
        position = (
            db.query(VesselPosition)
            .filter(VesselPosition.vessel_id == vessel.id)
            .order_by(VesselPosition.timestamp.desc())
            .first()
        )
        if position:
            latest_positions[vessel.id] = position
    service = RoutingService()
    recommendations = []
    for zone in zones:
        recommendations.extend(service.rank_vessels_for_zone(vessels, latest_positions, zone)[:2])
    return sorted(recommendations, key=lambda row: row["recommendation_score"], reverse=True)


@router.get("/routes", tags=["routes"])
def routes_alias(db: Session = Depends(get_db)):
    return route_recommendations(db)


@router.get("/tasks", response_model=list[TaskRead], tags=["tasks"])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(CollectionTask).order_by(CollectionTask.created_at.desc()).all()


@router.post("/tasks", response_model=TaskRead, tags=["tasks"])
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = CollectionTask(
        task_reference=f"TASK-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        collection_zone_id=payload.collection_zone_id,
        assigned_vessel_id=payload.assigned_vessel_id,
        priority=payload.priority,
        estimated_volume_kg=payload.estimated_volume_kg,
        estimated_cost=payload.estimated_cost,
        estimated_duration=payload.estimated_duration,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/alerts", response_model=list[AlertRead], tags=["alerts"])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.created_at.desc()).all()


@router.post("/uploads/geojson", response_model=UploadResponse, tags=["uploads"])
def upload_geojson(payload: dict, db: Session = Depends(get_db)):
    features = payload.get("features", [])
    accepted = IngestionService().ingest_geojson_placeholder(db, features)
    return UploadResponse(accepted=accepted, rejected=max(0, len(features) - accepted), message="GeoJSON processed")


@router.post("/demo/seed", tags=["demo"])
def seed_demo(db: Session = Depends(get_db)):
    return seed_demo_data(db)


@router.get("/dashboard/summary", tags=["dashboard"])
def dashboard_summary(db: Session = Depends(get_db)):
    return {
        "observations": db.query(SargassumObservation).count(),
        "patches": db.query(SargassumPatch).count(),
        "critical_patches": db.query(SargassumPatch).filter(SargassumPatch.severity == "critical").count(),
        "vessels": db.query(Vessel).count(),
        "active_tasks": db.query(CollectionTask).filter(CollectionTask.status.in_(["assigned", "en_route", "collecting"])).count(),
        "unread_alerts": db.query(Alert).filter(Alert.is_read.is_(False)).count(),
    }
