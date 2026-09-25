from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.civic_event import CivicEvent


class WeatherSummary(BaseModel):
    average_temperature: Optional[float] = None
    average_rainfall: Optional[float] = None
    max_rainfall: Optional[float] = None
    dominant_condition: Optional[str] = None
    average_humidity: Optional[float] = None
    active_rain_zones: List[str] = Field(default_factory=list, description="Zones currently experiencing rainfall > 0 mm")
    total_reporting_stations: int = Field(..., description="Count of weather observation stations")


class TrafficSummary(BaseModel):
    average_congestion: float = Field(..., description="Average congestion percentage across all corridors")
    average_delay_minutes: float = Field(..., description="Average vehicular delay in minutes")
    most_congested_corridor: Optional[str] = Field(None, description="Corridor with the highest congestion level")
    most_congested_zone: Optional[str] = Field(None, description="Zone experiencing the highest average congestion")
    severe_congestion_corridors_count: int = Field(..., description="Count of roads with high or critical congestion")
    congestion_breakdown_by_severity: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of traffic corridors grouped by severity level",
    )


class IncidentSummary(BaseModel):
    total_incidents: int = Field(..., description="Total incidents recorded")
    active_incidents: int = Field(..., description="Count of unresolved incidents (reported, in_progress, verified)")
    resolved_incidents: int = Field(..., description="Count of resolved incidents")
    critical_incidents: int = Field(..., description="Count of active critical-severity incidents")
    breakdown_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Incident counts grouped by category (e.g. waterlogging, road_accident)",
    )
    breakdown_by_severity: Dict[str, int] = Field(
        default_factory=dict,
        description="Incident counts grouped by severity",
    )


class DashboardResponse(BaseModel):
    """
    CityPulse Unified Civic Health Dashboard Response.
    Designed for frontend consumption and future ML anomaly & correlation integration.
    """
    healthScore: int = Field(
        ...,
        ge=0,
        le=100,
        description="Provisional civic-health estimate (0-100), based on available live weather and user-reported incidents; stored traffic observations are excluded",
        examples=[72],
    )
    city: str = Field("Jaipur", description="Monitored municipality")
    timestamp: datetime = Field(..., description="Snapshot generation timestamp (ISO 8601)")
    weather: WeatherSummary = Field(..., description="Aggregated meteorological conditions")
    traffic: TrafficSummary = Field(..., description="Aggregated traffic congestion & corridor delays")
    incidents: IncidentSummary = Field(..., description="Aggregated municipal incidents status")
    alerts: List[CivicEvent] = Field(
        default_factory=list,
        description="Active high and critical civic alerts requiring immediate attention",
    )
    latestEvents: List[CivicEvent] = Field(
        default_factory=list,
        description="Most recent normalized civic events across all sources",
    )
    anomalies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detected anomalies (Placeholder for future ML pipeline; returns empty list for MVP)",
    )
    correlations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detected multi-source cross-correlations (Placeholder for future ML pipeline; returns empty list for MVP)",
    )
    summary: Optional[str] = Field(
        None,
        description="Natural language situational briefing (Placeholder for future LLM summary; returns null for MVP)",
    )
    data_sources: Dict[str, str] = Field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
