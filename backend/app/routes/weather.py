import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.models.weather import WeatherCreate, WeatherRecord
from app.services.data_service import data_service
from app.services.live_weather import LiveWeatherUnavailableError, get_jaipur_weather

router = APIRouter(prefix="/weather", tags=["Weather"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=List[WeatherRecord],
    summary="Get weather observations",
    description="Retrieve current Jaipur conditions and hourly forecast from Open-Meteo. Stored sensor ingestion remains available through POST.",
)
async def get_weather_records(
    zone: Optional[str] = Query(
        None,
        description="Filter by civic zone (e.g. 'Malviya Nagar', 'Sanganer', 'Pink City', 'C-Scheme')",
    ),
    min_rainfall: Optional[float] = Query(
        None,
        ge=0.0,
        description="Filter observations with rainfall >= min_rainfall in mm",
    ),
    condition: Optional[str] = Query(
        None,
        description="Filter by condition keyword (e.g. 'Rain', 'Thunderstorm', 'Clear')",
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    refresh: bool = Query(False, description="Request refresh after the minimum ten-minute cache interval; does not bypass rate limiting"),
) -> List[WeatherRecord]:
    try:
        if zone and zone.strip().lower() not in {"jaipur", "jaipur city"}:
            return []
        record = await get_jaipur_weather(refresh=refresh)
        if min_rainfall is not None and record.rainfall < min_rainfall:
            return []
        if condition and condition.lower() not in record.weather_condition.lower():
            return []
        return [record][skip : skip + limit]
    except LiveWeatherUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Failed to retrieve weather data")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather data.",
        )


@router.post(
    "",
    response_model=WeatherRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest weather observation",
    description="Ingest a new meteorological sensor reading. Automatically validates coordinates, humidity, rainfall, and triggers normalization into CivicEvent.",
)
async def create_weather_record(payload: WeatherCreate) -> WeatherRecord:
    try:
        return await data_service.create_weather(payload)
    except Exception:
        logger.exception("Failed to ingest weather record")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to ingest weather record.",
        )


@router.get(
    "/{record_id}",
    response_model=WeatherRecord,
    summary="Get single weather observation",
    description="Retrieve a specific meteorological observation record by ID.",
)
async def get_weather_record_by_id(record_id: str) -> WeatherRecord:
    if record_id == "open_meteo_jaipur_current":
        try:
            return await get_jaipur_weather()
        except LiveWeatherUnavailableError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    record = await data_service.get_weather_by_id(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weather record '{record_id}' not found.",
        )
    return record
