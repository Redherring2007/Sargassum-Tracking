import enum
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    assigned = "assigned"
    en_route = "en_route"
    collecting = "collecting"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class VesselStatus(str, enum.Enum):
    idle = "idle"
    assigned = "assigned"
    en_route = "en_route"
    collecting = "collecting"
    returning = "returning"
    offline = "offline"


class Organisation(Base, TimestampMixin):
    __tablename__ = "organisations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    organisation_type: Mapped[str] = mapped_column(String(80), default="operator")
    subscription_plan: Mapped[str] = mapped_column(String(80), default="mvp")
    api_access_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(80), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    source_type: Mapped[str] = mapped_column(String(80))
    provider: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80), default="active")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ClientSite(Base, TimestampMixin):
    __tablename__ = "client_sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"))
    site_name: Mapped[str] = mapped_column(String(180), index=True)
    site_type: Mapped[str] = mapped_column(String(80), default="resort")
    priority_level: Mapped[int] = mapped_column(Integer, default=3)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    geometry = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    current_risk: Mapped[str] = mapped_column(String(40), default="low")
    notes: Mapped[str | None] = mapped_column(Text)


class SargassumObservation(Base, TimestampMixin):
    __tablename__ = "sargassum_observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"))
    source_type: Mapped[str] = mapped_column(String(80), default="manual")
    source_reference: Mapped[str | None] = mapped_column(String(255))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    geometry = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    density_level: Mapped[str] = mapped_column(String(40), default="medium")
    estimated_area_m2: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.7)
    notes: Mapped[str | None] = mapped_column(Text)


class SargassumPatch(Base, TimestampMixin):
    __tablename__ = "sargassum_patches"
    id: Mapped[int] = mapped_column(primary_key=True)
    patch_reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.medium)
    geometry = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    centroid_latitude: Mapped[float] = mapped_column(Float)
    centroid_longitude: Mapped[float] = mapped_column(Float)
    estimated_area_m2: Mapped[float] = mapped_column(Float, default=0)
    density_level: Mapped[str] = mapped_column(String(40), default="medium")
    movement_direction_degrees: Mapped[float] = mapped_column(Float, default=275)
    movement_speed_knots: Mapped[float] = mapped_column(Float, default=0.7)
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence_score: Mapped[float] = mapped_column(Float, default=0.65)
    source_type: Mapped[str] = mapped_column(String(80), default="derived")
    source_reference: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class PredictionRun(Base, TimestampMixin):
    __tablename__ = "prediction_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    patch_id: Mapped[int | None] = mapped_column(ForeignKey("sargassum_patches.id"))
    model_name: Mapped[str] = mapped_column(String(120), default="mvp_vector_drift")
    horizon_hours: Mapped[int] = mapped_column(Integer, default=72)
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.6)
    status: Mapped[str] = mapped_column(String(60), default="completed")
    patch = relationship("SargassumPatch")


class PredictedDriftZone(Base, TimestampMixin):
    __tablename__ = "predicted_drift_zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_run_id: Mapped[int] = mapped_column(ForeignKey("prediction_runs.id"))
    patch_id: Mapped[int | None] = mapped_column(ForeignKey("sargassum_patches.id"))
    geometry = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    center_latitude: Mapped[float] = mapped_column(Float)
    center_longitude: Mapped[float] = mapped_column(Float)
    impact_timeframe_hours: Mapped[int] = mapped_column(Integer, default=72)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.medium)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.6)
    source_type: Mapped[str] = mapped_column(String(80), default="prediction")
    notes: Mapped[str | None] = mapped_column(Text)


class CoastlineRiskZone(Base, TimestampMixin):
    __tablename__ = "coastline_risk_zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(160))
    geometry = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.medium)
    predicted_arrival_hours: Mapped[int | None] = mapped_column(Integer)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.6)
    source_type: Mapped[str] = mapped_column(String(80), default="prediction")
    source_reference: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class CollectionZone(Base, TimestampMixin):
    __tablename__ = "collection_zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(160), index=True)
    geometry = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    center_latitude: Mapped[float] = mapped_column(Float)
    center_longitude: Mapped[float] = mapped_column(Float)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.medium)
    estimated_volume_kg: Mapped[float] = mapped_column(Float, default=0)
    priority_score: Mapped[float] = mapped_column(Float, default=50)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.65)
    source_type: Mapped[str] = mapped_column(String(80), default="derived")
    source_reference: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class Vessel(Base, TimestampMixin):
    __tablename__ = "vessels"
    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_name: Mapped[str] = mapped_column(String(160), index=True)
    vessel_type: Mapped[str] = mapped_column(String(80), default="collection_boat")
    operator: Mapped[str] = mapped_column(String(160))
    home_port: Mapped[str] = mapped_column(String(160))
    fuel_cost_per_hour: Mapped[float] = mapped_column(Float, default=45)
    operating_cost_per_hour: Mapped[float] = mapped_column(Float, default=120)
    max_speed_knots: Mapped[float] = mapped_column(Float, default=18)
    working_speed_knots: Mapped[float] = mapped_column(Float, default=8)
    collection_capacity_kg: Mapped[float] = mapped_column(Float, default=2500)
    gps_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[VesselStatus] = mapped_column(Enum(VesselStatus), default=VesselStatus.idle)


class VesselPosition(Base, TimestampMixin):
    __tablename__ = "vessel_positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"))
    geometry = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    heading: Mapped[float] = mapped_column(Float, default=0)
    speed: Mapped[float] = mapped_column(Float, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_type: Mapped[str] = mapped_column(String(80), default="gps")
    vessel = relationship("Vessel")


class BoatRoute(Base, TimestampMixin):
    __tablename__ = "boat_routes"
    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"))
    collection_zone_id: Mapped[int | None] = mapped_column(ForeignKey("collection_zones.id"))
    geometry = mapped_column(Geometry("LINESTRING", srid=4326), nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="recommended")
    distance_nm: Mapped[float] = mapped_column(Float, default=0)
    estimated_travel_hours: Mapped[float] = mapped_column(Float, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    recommendation_score: Mapped[float] = mapped_column(Float, default=0)
    reasoning_summary: Mapped[str | None] = mapped_column(Text)


class CollectionTask(Base, TimestampMixin):
    __tablename__ = "collection_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    collection_zone_id: Mapped[int] = mapped_column(ForeignKey("collection_zones.id"))
    assigned_vessel_id: Mapped[int | None] = mapped_column(ForeignKey("vessels.id"))
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.proposed)
    estimated_volume_kg: Mapped[float] = mapped_column(Float, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    estimated_duration: Mapped[float] = mapped_column(Float, default=0)
    recommended_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_notes: Mapped[str | None] = mapped_column(Text)
    zone = relationship("CollectionZone")
    vessel = relationship("Vessel")


class TaskAssignment(Base, TimestampMixin):
    __tablename__ = "task_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("collection_tasks.id"))
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"))
    assigned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(60), default="active")


class OperationalCost(Base, TimestampMixin):
    __tablename__ = "operational_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int | None] = mapped_column(ForeignKey("vessels.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("collection_tasks.id"))
    cost_type: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    notes: Mapped[str | None] = mapped_column(Text)


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.medium)
    message: Mapped[str] = mapped_column(Text)
    related_object_type: Mapped[str | None] = mapped_column(String(100))
    related_object_id: Mapped[int | None] = mapped_column(Integer)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class ApiLog(Base, TimestampMixin):
    __tablename__ = "api_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(255))
    method: Mapped[str] = mapped_column(String(20))
    status_code: Mapped[int] = mapped_column(Integer)
    organisation_id: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
