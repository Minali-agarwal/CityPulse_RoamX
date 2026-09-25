import logging
from fastapi import APIRouter, HTTPException, status
from app.models.dashboard import DashboardResponse
from app.services.data_service import data_service
from app.services.live_weather import LiveWeatherUnavailableError, get_jaipur_weather
from app.services.recommendations import get_recommendations

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get aggregated civic health dashboard snapshot",
    description="Returns high-level civic health score, aggregated weather, traffic congestion, municipal incidents, active urgent alerts, and recent normalized events. Includes empty structures for ML anomalies and correlations.",
)
async def get_dashboard() -> DashboardResponse:
    try:
        try:
            weather = await get_jaipur_weather()
            weather_records = [weather]
        except LiveWeatherUnavailableError:
            weather_records = []
        snapshot = await data_service.get_dashboard_summary(live_weather_records=weather_records)
        snapshot.summary = (
            "Provisional city-health estimate based on live Open-Meteo weather and user-reported MongoDB incidents; stored traffic data is development-only."
            if weather_records
            else "Provisional city-health estimate based on available user-reported MongoDB incidents. Live weather is unavailable and stored traffic data is development-only."
        )
        recommendation_data = await get_recommendations()
        snapshot.recommendations = recommendation_data["recommendations"]
        snapshot.data_sources.update(recommendation_data["data_sources"])
        return snapshot
    except Exception:
        logger.exception("Failed to generate dashboard aggregation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dashboard aggregation.",
        )
