from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.common import Location, Severity


class TrafficBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    congestion_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Traffic volume congestion percentage (0% = free flow, 100% = standstill gridlock)",
        examples=[84.5],
    )
    delay: float = Field(
        ...,
        ge=0.0,
        description="Estimated vehicular delay in minutes above normal travel time",
        examples=[22.0],
    )
    location: Location
    timestamp: datetime = Field(
        ...,
        description="Timestamp of traffic measurement (ISO 8601)",
        examples=["2026-09-24T15:30:00+05:30"],
    )
    severity: Severity = Field(
        ...,
        description="Assessed severity level: low, medium, high, critical",
        examples=[Severity.HIGH],
    )
    average_speed_kmh: Optional[float] = Field(
        None,
        ge=0.0,
        le=200.0,
        description="Observed average vehicle speed in km/h",
        examples=[12.4],
    )
    free_flow_speed_kmh: Optional[float] = Field(
        None,
        ge=0.0,
        le=200.0,
        description="Expected free-flow speed for corridor in km/h",
        examples=[50.0],
    )


class TrafficRecord(TrafficBase):
    id: str = Field(
        ...,
        description="Unique traffic observation ID",
        examples=["traffic_jpr_001"],
    )


class TrafficCreate(TrafficBase):
    id: Optional[str] = Field(
        None,
        description="Optional unique identifier (auto-generated if omitted)",
        examples=["traffic_jpr_099"],
    )
