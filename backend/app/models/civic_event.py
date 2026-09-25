from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.common import Severity


class EventSource(str, Enum):
    WEATHER = "weather"
    TRAFFIC = "traffic"
    INCIDENT = "incident"


class CivicEvent(BaseModel):
    """
    Common Civic Data Schema.
    Normalizes civic telemetry from weather sensors, traffic detectors,
    and municipal incident reports into a unified format for multi-source
    correlation, anomaly detection, and unified civic health scoring.
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        ...,
        description="Unique event identifier (e.g. weather_001_rainfall, traffic_012_congestion)",
        examples=["weather_001"],
    )
    source: EventSource = Field(
        ...,
        description="Origin source category: 'weather', 'traffic', or 'incident'",
        examples=["weather"],
    )
    type: str = Field(
        ...,
        min_length=1,
        description="Specific metric or category type (e.g. rainfall, temperature, congestion, waterlogging, road_accident)",
        examples=["rainfall"],
    )
    value: Optional[Union[float, int, str]] = Field(
        None,
        description="Quantitative measurement or categorical metric value",
        examples=[32.0],
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measurement (e.g. mm, °C, %, mins, count)",
        examples=["mm"],
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="WGS84 latitude coordinate",
        examples=[26.85],
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="WGS84 longitude coordinate",
        examples=[75.80],
    )
    zone: str = Field(
        ...,
        min_length=1,
        description="Civic zone or locality",
        examples=["Malviya Nagar"],
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the event was recorded or occurred",
        examples=["2026-09-24T15:00:00+05:30"],
    )
    severity: Severity = Field(
        ...,
        description="Normalized severity assessment: low, medium, high, critical",
        examples=["medium"],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental source-specific attributes (e.g. raw readings, road name, incident status)",
        examples=[{"sensor_id": "SN-JPR-04", "humidity": 85}],
    )

    @field_validator("id", "type", "zone")
    @classmethod
    def strip_and_validate_nonempty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s


class CivicEventCreate(BaseModel):
    """Schema for manually ingesting a normalized civic event."""
    id: Optional[str] = None
    source: EventSource
    type: str
    value: Optional[Union[float, int, str]] = None
    unit: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    zone: str = Field(..., min_length=1)
    timestamp: Optional[datetime] = None
    severity: Severity = Severity.LOW
    metadata: Dict[str, Any] = Field(default_factory=dict)
