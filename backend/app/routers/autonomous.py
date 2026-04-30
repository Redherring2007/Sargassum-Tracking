from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/autonomous", tags=["autonomous"])


class AutonomousTelemetry(BaseModel):
    device_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    heading: float = 0
    speed_knots: float = 0
    battery_percent: float | None = Field(default=None, ge=0, le=100)
    status: str = "reporting"


@router.get("/tasks")
def autonomous_tasks():
    return {
        "tasks": [],
        "message": "Placeholder endpoint for robotic collectors to request GPS/polygon tasking.",
    }


@router.post("/status")
def autonomous_status(payload: dict):
    return {"accepted": True, "received_at": datetime.now(UTC), "status": payload.get("status", "unknown")}


@router.post("/telemetry")
def autonomous_telemetry(payload: AutonomousTelemetry):
    return {"accepted": True, "device_id": payload.device_id, "received_at": datetime.now(UTC)}
