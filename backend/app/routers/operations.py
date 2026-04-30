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

router = APIRouter()




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
    result = DriftPredictionService().run_prediction_for_patch(patch, inputs)
    run = PredictionRun(
        patch_id=patch.id,
        horizon_hours=horizon_hours,
        input_summary={
            "source": "Open-Meteo Marine current",
            "ocean_current_direction_degrees": inputs.ocean_current_direction_degrees,
            "ocean_current_speed_knots": inputs.ocean_current_speed_knots,
        },
        confidence_score=result["confidence_score"],
    )
    db.add(run)
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
    result = DriftPredictionService().run_prediction_for_patch(patch, inputs)
    run = PredictionRun(
        patch_id=patch.id,
        horizon_hours=payload.horizon_hours,
        input_summary=payload.model_dump(),
        confidence_score=result["confidence_score"],
    )
    db.add(run)
    db.commit()
    return result


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
