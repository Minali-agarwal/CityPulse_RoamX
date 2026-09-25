import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.database.connection import (
    close_mongo_connection,
    connect_to_mongo,
    is_mongo_connected,
)
from app.database.indexes import ensure_indexes
from app.routes import civic_events, crowd_prediction, dashboard, incidents, recommendations, traffic, weather
from app.services.crowd_prediction import crowd_prediction_service
from app.services.data_service import data_service

settings = get_settings()
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Attempts MongoDB connection and initializes data service with synthetic data fallback.
    """
    crowd_prediction_service.load()
    await connect_to_mongo()
    await ensure_indexes()
    await data_service.initialize()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Backend foundation for CityPulse Live Civic Health Dashboard. "
        "Provides normalized civic telemetry across Weather, Traffic, and Incidents "
        "for the city of Jaipur, with multi-source correlation readiness and civic health scoring."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for Pydantic Request Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "loc": list(error.get("loc", ())),
            "msg": error.get("msg", "Invalid value."),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "One or more request parameters or payload fields failed schema validation.",
            "details": details,
        },
    )


# ---------------------------------------------------------------------------
# Core Health & Status Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check and system status",
    description="Check operational health, database connectivity, and data source status.",
)
async def health_check() -> Dict[str, Any]:
    mongo_ok = is_mongo_connected()
    return {
        "status": "healthy",
        "service": "CityPulse Backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "connected": mongo_ok,
            "engine": "MongoDB (Motor)" if mongo_ok else "None",
            "activeDataSource": "MongoDB" if mongo_ok else "Local Synthetic JSON Data",
        },
        "demonstrationCity": "Jaipur, Rajasthan, India",
        "uptimeSeconds": round(time.time() - START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["System"], include_in_schema=False)
async def root_redirect():
    return {
        "message": "Welcome to CityPulse — Live Civic Health Dashboard API",
        "documentation": "/docs",
        "health": "/api/health",
        "endpoints": {
            "weather": "/api/weather",
            "traffic": "/api/traffic",
            "incidents": "/api/incidents",
            "civicEvents": "/api/civic-events",
            "dashboard": "/api/dashboard",
        },
    }


# ---------------------------------------------------------------------------
# API Routers Mount
# ---------------------------------------------------------------------------
app.include_router(weather.router, prefix=settings.API_V1_PREFIX)
app.include_router(traffic.router, prefix=settings.API_V1_PREFIX)
app.include_router(incidents.router, prefix=settings.API_V1_PREFIX)
app.include_router(civic_events.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(crowd_prediction.router, prefix=settings.API_V1_PREFIX)
app.include_router(recommendations.router, prefix=settings.API_V1_PREFIX)
