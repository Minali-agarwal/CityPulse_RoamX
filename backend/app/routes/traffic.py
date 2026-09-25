import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.models.common import Severity
from app.models.traffic import TrafficCreate, TrafficRecord
from app.services.data_service import data_service

router = APIRouter(prefix="/traffic", tags=["Traffic"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=List[TrafficRecord],
    summary="Get traffic observations",
    description="Retrieve live or synthetic traffic congestion and delay measurements across Jaipur road corridors. Supports filtering by zone, severity, and minimum congestion percentage.",
)
async def get_traffic_records(
    zone: Optional[str] = Query(
        None,
        description="Filter by zone (e.g. 'Sanganer', 'Malviya Nagar', 'Pink City', 'Mansarovar')",
    ),
    severity: Optional[Severity] = Query(
        None,
        description="Filter by assessed severity (low, medium, high, critical)",
    ),
    min_congestion: Optional[float] = Query(
        None,
        ge=0.0,
        le=100.0,
        description="Filter records with congestion percentage >= min_congestion",
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[TrafficRecord]:
    try:
        return await data_service.get_traffic(
            zone=zone,
            severity=severity,
            min_congestion=min_congestion,
            limit=limit,
            skip=skip,
        )
    except Exception:
        logger.exception("Failed to retrieve traffic data")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve traffic data.",
        )


@router.post(
    "",
    response_model=TrafficRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest traffic observation",
    description="Ingest a new traffic observation reading. Automatically validates congestion percentage, coordinates, delay, and triggers normalization into CivicEvent.",
)
async def create_traffic_record(payload: TrafficCreate) -> TrafficRecord:
    try:
        return await data_service.create_traffic(payload)
    except Exception:
        logger.exception("Failed to ingest traffic record")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to ingest traffic record.",
        )


@router.get(
    "/{record_id}",
    response_model=TrafficRecord,
    summary="Get single traffic observation",
    description="Retrieve a specific traffic corridor observation record by ID.",
)
async def get_traffic_record_by_id(record_id: str) -> TrafficRecord:
    record = await data_service.get_traffic_by_id(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Traffic record '{record_id}' not found.",
        )
    return record
