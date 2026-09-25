from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


CrowdLevel = Literal["low", "moderate", "high"]


class CrowdPredictionRequest(BaseModel):
    """Weather, traffic, incident, zone, and timestamp inputs used by the model."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="Timezone-aware ISO-8601 observation time")
    zone: str = Field(..., min_length=1, max_length=100)
    temperature_c: Optional[float] = Field(None, ge=-40, le=65)
    rainfall_mm: Optional[float] = Field(None, ge=0, le=500)
    humidity_pct: Optional[float] = Field(None, ge=0, le=100)
    wind_speed_kmh: Optional[float] = Field(None, ge=0)
    air_quality_index: Optional[float] = Field(None, ge=0, le=1000)
    weather_condition: Optional[str] = Field(None, min_length=1, max_length=80)
    congestion_percentage: Optional[float] = Field(None, ge=0, le=100)
    traffic_delay_minutes: Optional[float] = Field(None, ge=0)
    average_speed_kmh: Optional[float] = Field(None, ge=0, le=200)
    incident_count: Optional[int] = Field(None, ge=0)
    active_incident_count: Optional[int] = Field(None, ge=0)
    high_critical_incident_count: Optional[int] = Field(None, ge=0)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone offset")
        return value

    @field_validator("zone", "weather_condition")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned


class CrowdPredictionResponse(BaseModel):
    crowd_level: CrowdLevel
    confidence: float = Field(..., ge=0, le=1)
    probabilities: Dict[str, float]
