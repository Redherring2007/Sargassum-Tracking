from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.domain import (
    Alert,
    ClientSite,
    CollectionTask,
    CollectionZone,
    DataSource,
    Organisation,
    PredictedDriftZone,
    PredictionRun,
    SargassumObservation,
    SargassumPatch,
    Vessel,
    VesselPosition,
)


def seed_demo_data(db: Session) -> dict:
    if db.query(Organisation).count() > 0:
        return {"status": "already_seeded"}

    org = Organisation(name="Caribbean Coastal Response Network", organisation_type="marine_operator")
    db.add(org)
    db.flush()

    db.add_all(
        [
            DataSource(name="Manual Field Reports", source_type="manual", provider="Sentinel MVP"),
            DataSource(name="Satellite Detection Placeholder", source_type="satellite", provider="Open future adapter"),
            DataSource(name="Ocean Current Placeholder", source_type="ocean_current", provider="NOAA/Copernicus adapter"),
            DataSource(name="AIS Placeholder", source_type="ais", provider="Future feed"),
        ]
    )

    sites = [
        ClientSite(
            organisation_id=org.id,
            site_name="Azure Bay Resort",
            site_type="resort",
            priority_level=5,
            latitude=13.196,
            longitude=-59.438,
            current_risk="high",
            notes="Premium resort frontage with active beach cleaning contract.",
        ),
        ClientSite(
            organisation_id=org.id,
            site_name="Crane Beach Operations",
            site_type="beach",
            priority_level=4,
            latitude=13.104,
            longitude=-59.448,
            current_risk="medium",
        ),
        ClientSite(
            organisation_id=org.id,
            site_name="Port Castries Authority",
            site_type="port",
            priority_level=5,
            latitude=14.015,
            longitude=-60.992,
            current_risk="medium",
        ),
    ]
    db.add_all(sites)

    now = datetime.now(UTC)
    observations = [
        SargassumObservation(latitude=13.42, longitude=-58.63, observed_at=now - timedelta(hours=3), density_level="high", estimated_area_m2=180000, confidence_score=0.82, source_type="manual", notes="Dense windrows visible from patrol boat."),
        SargassumObservation(latitude=13.34, longitude=-58.75, observed_at=now - timedelta(hours=5), density_level="medium", estimated_area_m2=90000, confidence_score=0.74, source_type="drone", notes="Drone transect confirms patch edge."),
        SargassumObservation(latitude=14.22, longitude=-60.25, observed_at=now - timedelta(hours=2), density_level="high", estimated_area_m2=240000, confidence_score=0.78, source_type="satellite_placeholder", notes="Mock chlorophyll/texture detection."),
    ]
    db.add_all(observations)

    patches = [
        SargassumPatch(patch_reference="PATCH-BGI-001", severity="high", centroid_latitude=13.39, centroid_longitude=-58.68, estimated_area_m2=420000, density_level="high", movement_direction_degrees=282, movement_speed_knots=0.9, last_observed_at=now - timedelta(hours=3), confidence_score=0.78, source_type="derived", notes="Likely Barbados east coast impact within 48-72h."),
        SargassumPatch(patch_reference="PATCH-LCA-002", severity="medium", centroid_latitude=14.12, centroid_longitude=-60.18, estimated_area_m2=260000, density_level="medium", movement_direction_degrees=265, movement_speed_knots=0.65, last_observed_at=now - timedelta(hours=2), confidence_score=0.69, source_type="satellite_placeholder", notes="Tracking westward toward Windward Islands."),
        SargassumPatch(patch_reference="PATCH-OFF-003", severity="critical", centroid_latitude=12.86, centroid_longitude=-57.95, estimated_area_m2=900000, density_level="very_high", movement_direction_degrees=290, movement_speed_knots=1.1, last_observed_at=now - timedelta(hours=1), confidence_score=0.72, source_type="model_placeholder", notes="Large offshore mass, high collection potential if intercepted."),
    ]
    db.add_all(patches)
    db.flush()

    run = PredictionRun(patch_id=patches[0].id, horizon_hours=72, confidence_score=0.62, input_summary={"wind": "ESE 12kt", "current": "west-northwest 0.7kt"})
    db.add(run)
    db.flush()
    db.add_all(
        [
            PredictedDriftZone(prediction_run_id=run.id, patch_id=patches[0].id, center_latitude=13.30, center_longitude=-59.18, severity="high", impact_timeframe_hours=48, confidence_score=0.64, notes="Primary forecast envelope."),
            PredictedDriftZone(prediction_run_id=run.id, patch_id=patches[0].id, center_latitude=13.22, center_longitude=-59.42, severity="critical", impact_timeframe_hours=72, confidence_score=0.58, notes="Possible landfall zone near Barbados east coast."),
        ]
    )

    zones = [
        CollectionZone(zone_name="Interception Box Alpha", center_latitude=13.33, center_longitude=-59.05, severity="high", estimated_volume_kg=6200, priority_score=86, confidence_score=0.76, notes="Best current offshore interception zone."),
        CollectionZone(zone_name="Nearshore Cleanup Bravo", center_latitude=13.18, center_longitude=-59.41, severity="critical", estimated_volume_kg=3400, priority_score=94, confidence_score=0.71, notes="Protect resort coastline before beaching."),
        CollectionZone(zone_name="Windward Sweep Charlie", center_latitude=14.06, center_longitude=-60.55, severity="medium", estimated_volume_kg=2800, priority_score=61, confidence_score=0.63, notes="Schedule if vessel capacity remains available."),
    ]
    db.add_all(zones)
    db.flush()

    vessels = [
        Vessel(vessel_name="Sentinel One", vessel_type="skimmer", operator="BlueCurrent Marine", home_port="Bridgetown", fuel_cost_per_hour=55, operating_cost_per_hour=145, max_speed_knots=20, working_speed_knots=8, collection_capacity_kg=4200, status="idle"),
        Vessel(vessel_name="Pelagic Runner", vessel_type="support_boat", operator="BlueCurrent Marine", home_port="Oistins", fuel_cost_per_hour=48, operating_cost_per_hour=118, max_speed_knots=24, working_speed_knots=10, collection_capacity_kg=2300, status="assigned"),
        Vessel(vessel_name="Reef Guardian", vessel_type="nearshore_collector", operator="Coastal Response Unit", home_port="Castries", fuel_cost_per_hour=38, operating_cost_per_hour=95, max_speed_knots=16, working_speed_knots=7, collection_capacity_kg=1800, status="collecting"),
    ]
    db.add_all(vessels)
    db.flush()
    db.add_all(
        [
            VesselPosition(vessel_id=vessels[0].id, latitude=13.10, longitude=-59.62, heading=82, speed=0, timestamp=now, source_type="gps"),
            VesselPosition(vessel_id=vessels[1].id, latitude=13.03, longitude=-59.51, heading=70, speed=8.2, timestamp=now, source_type="gps"),
            VesselPosition(vessel_id=vessels[2].id, latitude=14.01, longitude=-60.91, heading=124, speed=4.5, timestamp=now, source_type="gps"),
        ]
    )

    db.add_all(
        [
            CollectionTask(task_reference="TASK-ALPHA-001", collection_zone_id=zones[0].id, assigned_vessel_id=vessels[0].id, priority="high", status="assigned", estimated_volume_kg=4200, estimated_cost=1680, estimated_duration=7.4, recommended_start_time=now + timedelta(hours=1)),
            CollectionTask(task_reference="TASK-BRAVO-002", collection_zone_id=zones[1].id, assigned_vessel_id=vessels[1].id, priority="critical", status="proposed", estimated_volume_kg=2300, estimated_cost=1210, estimated_duration=5.1, recommended_start_time=now + timedelta(hours=3)),
        ]
    )
    db.add_all(
        [
            Alert(alert_type="high_risk_patch_approaching", severity="critical", message="Patch BGI-001 is forecast near Barbados east coast within 72 hours.", related_object_type="patch", related_object_id=patches[0].id, recommended_action="Approve Nearshore Cleanup Bravo and notify resort clients."),
            Alert(alert_type="vessel_task_recommended", severity="high", message="Sentinel One is the best available vessel for Interception Box Alpha.", related_object_type="collection_zone", related_object_id=zones[0].id, recommended_action="Dispatch within the next operating window."),
            Alert(alert_type="prediction_confidence_low", severity="medium", message="LCA-002 requires updated current/wind data before final routing.", related_object_type="patch", related_object_id=patches[1].id, recommended_action="Request updated observation or rerun model."),
        ]
    )
    db.commit()
    return {"status": "seeded", "organisations": 1, "patches": len(patches), "vessels": len(vessels)}
