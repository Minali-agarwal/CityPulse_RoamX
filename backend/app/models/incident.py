from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.common import Location, Severity


class IncidentCategory(str, Enum):
    WATERLOGGING = "waterlogging"
    ROAD_ACCIDENT = "road_accident"
    ROAD_DAMAGE = "road_damage"
    FALLEN_TREE = "fallen_tree"
    STREETLIGHT_OUTAGE = "streetlight_outage"
    TRAFFIC_SIGNAL_FAILURE = "traffic_signal_failure"
    OTHER = "other"


class IncidentStatus(str, Enum):
    REPORTED = "reported"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    RESOLVED = "resolved"


class IncidentBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    incident_category: IncidentCategory = Field(
        ...,
        description="Category of the civic incident",
        examples=[IncidentCategory.WATERLOGGING],
    )
    description: str = Field(
        ...,
        min_length=3,
        description="Human-readable description of the incident condition and impact",
        examples=["Severe waterlogging under Durgapura flyover, 2.5 ft water depth"],
    )
    severity: Severity = Field(
        ...,
        description="Severity level: low, medium, high, critical",
        examples=[Severity.CRITICAL],
    )
    location: Location
    timestamp: datetime = Field(
        ...,
        description="Timestamp when the incident occurred or was reported (ISO 8601)",
        examples=["2026-09-24T15:15:00+05:30"],
    )
    status: IncidentStatus = Field(
        default=IncidentStatus.REPORTED,
        description="Operational resolution status: reported, in_progress, verified, resolved",
        examples=[IncidentStatus.IN_PROGRESS],
    )
    reported_by: Optional[str] = Field(
        "Citizen Report",
        description="Source of report (e.g. Citizen App, Traffic Police, Municipal Patrol)",
        examples=["Traffic Police Control Room"],
    )
    estimated_clearance_minutes: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated time to clear or resolve the incident in minutes",
        examples=[60],
    )

    @field_validator("description")
    @classmethod
    def validate_desc(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("description cannot be empty or whitespace only")
        return s


class IncidentRecord(IncidentBase):
    id: str = Field(
        ...,
        description="Unique incident record ID",
        examples=["inc_jpr_001"],
    )


class IncidentCreate(IncidentBase):
    id: Optional[str] = Field(
        None,
        description="Optional unique identifier (auto-generated if omitted)",
        examples=["inc_jpr_099"],
    )


class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[Severity] = None
    description: Optional[str] = None
    estimated_clearance_minutes: Optional[int] = None
