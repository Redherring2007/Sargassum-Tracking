import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import autonomous, health, operations

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Sargassum Sentinel API",
    description="Commercial-grade MVP for sargassum intelligence, forecasting, routing, and collection operations.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(operations.router, prefix=settings.api_prefix)
app.include_router(autonomous.router, prefix=settings.api_prefix)
