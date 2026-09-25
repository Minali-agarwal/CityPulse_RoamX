"""Recommendations derived only from current provider data and stored user reports."""
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.database.connection import is_mongo_connected
from app.models.crowd_prediction import CrowdPredictionRequest
from app.models.common import Severity
from app.services.crowd_prediction import PredictionUnavailableError, crowd_prediction_service
from app.services.data_service import data_service
from app.services.live_weather import LiveWeatherUnavailableError, get_jaipur_weather


async def get_recommendations() -> Dict[str, Any]:
    recommendations: List[Dict[str, str]] = []
    sources = {
        "weather": "unavailable",
        "traffic": "development only; excluded from live recommendations",
        "incidents": "MongoDB user reports" if is_mongo_connected() else "unavailable; MongoDB disconnected",
        "crowd_prediction": "existing model; synthetic development training data",
    }
    weather = None
    try:
        weather = await get_jaipur_weather()
        sources["weather"] = (
            "Cached Open-Meteo weather · " + (weather.warning or "last successful observation")
            if weather.is_stale else weather.data_source or "Open-Meteo"
        )
    except LiveWeatherUnavailableError:
        pass

    incidents = await data_service.get_incidents(limit=100)
    active = [item for item in incidents if str(item.status.value if hasattr(item.status, "value") else item.status).lower() != "resolved"]
    urgent = [item for item in active if item.severity in (Severity.HIGH, Severity.CRITICAL)]
    for item in urgent:
        location = item.location.zone
        recommendations.append({
            "id": f"incident-{item.id}",
            "type": "incident_priority",
            "severity": "high" if item.severity == Severity.HIGH else "critical",
            "title": f"Review reported {item.incident_category.value.replace('_', ' ')} in {location}",
            "message": "A user-reported incident is marked " + item.severity.value + ". Verify its current status before dispatch or travel decisions.",
            "source": "MongoDB user-reported incident",
            "incident_id": item.id,
        })

    if weather:
        rain = float(weather.rainfall or 0)
        storms = "thunderstorm" in weather.weather_condition.lower()
        if (rain >= 2.0 or storms) and active:
            for item in active:
                recommendations.append({
                    "id": f"weather-incident-{item.id}",
                    "type": "weather_incident",
                    "severity": "high" if rain >= 5 or storms else "medium",
                    "title": f"Use caution near {item.location.zone}",
                    "message": f"Open-Meteo reports {weather.weather_condition.lower()} with {rain:g} mm current precipitation; a user-reported incident is recorded for this area. The report is unverified.",
                    "source": "Open-Meteo + MongoDB user report",
                    "incident_id": item.id,
                })
                if len(recommendations) >= 10:
                    break
        elif rain >= 5 or storms:
            recommendations.append({
                "id": "weather-travel-caution",
                "type": "weather",
                "severity": "high" if storms else "medium",
                "title": "Weather may affect travel",
                "message": f"Open-Meteo reports {weather.weather_condition.lower()} and {rain:g} mm current precipitation. Allow extra time and check local conditions.",
                "source": "Open-Meteo",
            })

    try:
        prediction_input = CrowdPredictionRequest(
            timestamp=datetime.now(timezone.utc),
            zone="Jaipur",
            temperature_c=weather.temperature if weather else None,
            rainfall_mm=weather.rainfall if weather else None,
            humidity_pct=weather.humidity if weather else None,
            wind_speed_kmh=weather.wind_speed_kmh if weather else None,
            weather_condition=weather.weather_condition if weather else None,
            incident_count=len(incidents),
            active_incident_count=len(active),
            high_critical_incident_count=len(urgent),
            # Traffic inputs deliberately omitted: current stored traffic is not live.
        )
        prediction = crowd_prediction_service.predict(prediction_input)
        level = prediction["crowd_level"]
        sources["crowd_prediction"] = "existing model; synthetic development training data; not validated"
        if level == "high":
            recommendations.append({
                "id": "crowd-high",
                "type": "crowd",
                "severity": "medium",
                "title": "Model predicts high crowd level",
                "message": "The existing development model predicts high crowd level for Jaipur. Consider an alternate time or check conditions locally; this model is not real-world validated.",
                "source": "Existing crowd model · synthetic training data",
            })
    except Exception:
        sources["crowd_prediction"] = "unavailable"

    return {
        "generated_at": datetime.now(timezone.utc),
        "recommendations": recommendations,
        "data_sources": sources,
        "traffic_live": False,
        "traffic_note": "Stored traffic observations are development data and were excluded from recommendations.",
    }
