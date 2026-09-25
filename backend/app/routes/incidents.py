import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.models.common import Severity
from app.models.incident import (
    IncidentCreate,
    IncidentRecord,
    IncidentStatus,
    IncidentUpdate,
)
from app.services.data_service import data_service

router = APIRouter(prefix="/incidents", tags=["Civic Incidents"])
logger = logging.getLogger("citypulse.routes.incidents")


@router.get(
    "",
    response_model=List[IncidentRecord],
    summary="Get civic incidents",
    description="Retrieve validated MongoDB user-reported incidents. Returns no substitute demo records when MongoDB is disconnected. Supports filtering by zone, category, severity, and status.",
)
async def get_incident_records(
    zone: Optional[str] = Query(
        None,
        description="Filter by zone (e.g. 'Sanganer', 'Mansarovar', 'Malviya Nagar', 'Pink City')",
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by incident category (e.g. 'waterlogging', 'road_accident', 'road_damage', 'fallen_tree')",
    ),
    severity: Optional[Severity] = Query(
        None,
        description="Filter by severity level (low, medium, high, critical)",
    ),
    incident_status: Optional[IncidentStatus] = Query(
        None,
        alias="status",
        description="Filter by operational status (reported, in_progress, verified, resolved)",
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[IncidentRecord]:
    try:
        return await data_service.get_incidents(
            zone=zone,
            category=category,
            severity=severity,
            status=incident_status,
            limit=limit,
            skip=skip,
        )
    except Exception:
        logger.exception("Failed to retrieve civic incidents")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve incidents.",
        )


@router.post(
    "",
    response_model=IncidentRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Report new civic incident",
    description="Report a new civic or municipal incident. Validates category, coordinates, severity, and automatically normalizes into CivicEvent.",
)
async def create_incident_record(payload: IncidentCreate) -> IncidentRecord:
    try:
        return await data_service.create_incident(payload)
    except Exception as exc:
        logger.exception("Failed to create civic incident")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The incident could not be saved because of a server error.",
        ) from exc


@router.get(
    "/{incident_id}",
    response_model=IncidentRecord,
    summary="Get single civic incident",
    description="Retrieve detailed information for a specific municipal incident by ID.",
)
async def get_incident_record_by_id(incident_id: str) -> IncidentRecord:
    record = await data_service.get_incident_by_id(incident_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return record


@router.patch(
    "/{incident_id}",
    response_model=IncidentRecord,
    summary="Update civic incident status or details",
    description="Update an incident's resolution status (e.g. reported -> in_progress -> resolved), severity, clearance estimate, or description. Automatically synchronizes normalized CivicEvents.",
)
async def update_incident_record(
    incident_id: str,
    payload: IncidentUpdate,
) -> IncidentRecord:
    updated = await data_service.update_incident(incident_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return updated
