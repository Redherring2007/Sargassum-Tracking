from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Severity


class ObservationCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observed_at: datetime | None = None
    source_type: str = "manual"
    source_reference: str | None = None
    density_level: str = "medium"
    estimated_area_m2: float | None = None
    confidence_score: float = Field(default=0.7, ge=0, le=1)
    notes: str | None = None


class ObservationRead(ObservationCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PatchRead(BaseModel):
    id: int
    patch_reference: str
    severity: Severity
    centroid_latitude: float
    centroid_longitude: float
    estimated_area_m2: float
    density_level: str
    movement_direction_degrees: float
    movement_speed_knots: float
    confidence_score: float
    source_type: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientSiteRead(BaseModel):
    id: int
    site_name: str
    site_type: str
    priority_level: int
    latitude: float
    longitude: float
    current_risk: str
    notes: str | None = None
    model_config = ConfigDict(from_attributes=True)


class VesselRead(BaseModel):
    id: int
    vessel_name: str
    vessel_type: str
    operator: str
    home_port: str
    fuel_cost_per_hour: float
    operating_cost_per_hour: float
    max_speed_knots: float
    working_speed_knots: float
    collection_capacity_kg: float
    gps_enabled: bool
    status: str
    model_config = ConfigDict(from_attributes=True)


class VesselPositionCreate(BaseModel):
    vessel_id: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    heading: float = 0
    speed: float = 0
    timestamp: datetime | None = None
    source_type: str = "gps"


class VesselPositionRead(VesselPositionCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CollectionZoneRead(BaseModel):
    id: int
    zone_name: str
    center_latitude: float
    center_longitude: float
    severity: Severity
    estimated_volume_kg: float
    priority_score: float
    confidence_score: float
    notes: str | None = None
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    collection_zone_id: int
    assigned_vessel_id: int | None = None
    priority: str = "medium"
    estimated_volume_kg: float = 0
    estimated_cost: float = 0
    estimated_duration: float = 0


class TaskRead(TaskCreate):
    id: int
    task_reference: str
    status: str
    recommended_start_time: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AlertRead(BaseModel):
    id: int
    alert_type: str
    severity: Severity
    message: str
    related_object_type: str | None = None
    related_object_id: int | None = None
    recommended_action: str | None = None
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PredictionRequest(BaseModel):
    patch_id: int
    horizon_hours: int = Field(default=72, ge=1, le=240)
    wind_direction_degrees: float = 275
    wind_speed_knots: float = 12
    ocean_current_direction_degrees: float = 285
    ocean_current_speed_knots: float = 0.7


class PredictionResponse(BaseModel):
    patch_id: int
    horizon_hours: int
    future_positions: list[dict[str, float]]
    drift_polygon: dict[str, Any]
    possible_impacts: list[dict[str, Any]]
    confidence_score: float


class RouteRecommendation(BaseModel):
    vessel_id: int
    vessel_name: str
    collection_zone_id: int
    zone_name: str
    distance_nm: float
    estimated_travel_hours: float
    estimated_cost: float
    estimated_collection_quantity_kg: float
    estimated_time_to_complete: float
    recommendation_score: float
    action: str
    reasoning_summary: str


class UploadResponse(BaseModel):
    accepted: int
    rejected: int
    message: str
