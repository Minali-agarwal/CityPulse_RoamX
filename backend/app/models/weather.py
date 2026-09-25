from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.common import Location


class WeatherBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    temperature: float = Field(
        ...,
        ge=-40.0,
        le=65.0,
        description="Ambient air temperature in degrees Celsius (°C)",
        examples=[28.5],
    )
    rainfall: float = Field(
        ...,
        ge=0.0,
        le=500.0,
        description="Accumulated or current rainfall intensity in millimeters (mm)",
        examples=[32.0],
    )
    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative atmospheric humidity percentage (%)",
        examples=[88.0],
    )
    weather_condition: str = Field(
        ...,
        min_length=1,
        description="Descriptive weather condition (e.g. Thunderstorm, Heavy Rain, Clear, Haze)",
        examples=["Heavy Rain"],
    )
    location: Location
    timestamp: datetime = Field(
        ...,
        description="Observation timestamp (ISO 8601)",
        examples=["2026-09-24T15:00:00+05:30"],
    )
    wind_speed_kmh: Optional[float] = Field(
        None,
        ge=0.0,
        description="Wind speed in kilometers per hour",
        examples=[35.2],
    )
    air_quality_index: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Air Quality Index (AQI)",
        examples=[115],
    )

    @field_validator("weather_condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("weather_condition cannot be empty")
        return s


class WeatherForecast(BaseModel):
    timestamp: datetime
    temperature: float
    humidity: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    precipitation: Optional[float] = None
    precipitation_probability: Optional[float] = None
    weather_condition: str


class WeatherRecord(WeatherBase):
    id: str = Field(
        ...,
        description="Unique weather observation ID",
        examples=["weather_jpr_001"],
    )
    data_source: Optional[str] = None
    fetched_at: Optional[datetime] = None
    weather_code: Optional[int] = None
    forecast: List[WeatherForecast] = Field(default_factory=list)
    is_stale: bool = False
    warning: Optional[str] = None


class WeatherCreate(WeatherBase):
    id: Optional[str] = Field(
        None,
        description="Optional unique identifier (auto-generated if omitted)",
        examples=["weather_jpr_099"],
    )
