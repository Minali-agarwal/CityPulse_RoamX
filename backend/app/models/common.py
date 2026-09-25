from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Location(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude between -90 and 90 degrees",
        examples=[26.8530],
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude between -180 and 180 degrees",
        examples=[75.8150],
    )
    zone: str = Field(
        ...,
        min_length=1,
        description="Civic zone or administrative division (e.g. Malviya Nagar, Pink City)",
        examples=["Malviya Nagar"],
    )
    address: Optional[str] = Field(
        None,
        description="Human-readable address or locality description",
        examples=["Calgiri Marg, Malviya Nagar, Jaipur"],
    )
    landmark: Optional[str] = Field(
        None,
        description="Nearby landmark or point of interest",
        examples=["Gaurav Tower"],
    )
    road_name: Optional[str] = Field(
        None,
        description="Road or corridor name",
        examples=["JLN Marg"],
    )

    @field_validator("zone")
    @classmethod
    def strip_zone(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Zone cannot be empty or whitespace only")
        return v_stripped
