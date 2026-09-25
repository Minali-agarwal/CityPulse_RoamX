import logging
from datetime import timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.models.civic_event import CivicEvent, CivicEventCreate, EventSource
from app.models.common import Severity
from app.services.data_service import data_service
from app.services.live_weather import LiveWeatherUnavailableError, get_jaipur_weather
from app.services.normalization import NormalizationService
from app.database.connection import is_mongo_connected

router = APIRouter(prefix="/civic-events", tags=["Civic Events (Normalized)"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=List[CivicEvent],
    summary="Get normalized civic events",
    description="Retrieve unified, normalized civic events across Weather, Traffic, and Incident domains. Ideal for multi-source correlation, geospatial mapping, and ML ingestion.",
)
async def get_civic_events(
    source: Optional[EventSource] = Query(
        None,
        description="Filter by origin domain ('weather', 'traffic', 'incident')",
    ),
    event_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by event type (e.g. 'rainfall', 'congestion', 'waterlogging', 'road_accident')",
    ),
    zone: Optional[str] = Query(
        None,
        description="Filter by civic zone (e.g. 'Sanganer', 'Malviya Nagar', 'Pink City')",
    ),
    severity: Optional[Severity] = Query(
        None,
        description="Filter by normalized severity level ('low', 'medium', 'high', 'critical')",
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum events to return"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[CivicEvent]:
    try:
        events: List[CivicEvent] = []
        if source in (None, EventSource.TRAFFIC):
            traffic = await data_service.get_civic_events(source=EventSource.TRAFFIC, limit=100)
            for event in traffic:
                event.metadata["data_source"] = "Stored development observation · not live traffic"
                events.append(event)
        if source in (None, EventSource.INCIDENT) and is_mongo_connected():
            incidents = await data_service.get_incidents(limit=100)
            for incident in incidents:
                event = NormalizationService.normalize_incident_record(incident)
                event.metadata["data_source"] = "MongoDB user-reported · not independently verified"
                events.append(event)
        if source in (None, EventSource.WEATHER):
            try:
                weather = await get_jaipur_weather()
                events.extend(NormalizationService.normalize_weather_record(weather))
                for event in events:
                    if event.source == EventSource.WEATHER:
                        event.metadata["data_source"] = "Cached Open-Meteo weather" if weather.is_stale else "Open-Meteo live forecast model"
                        if weather.warning:
                            event.metadata["warning"] = weather.warning
            except LiveWeatherUnavailableError:
                if source == EventSource.WEATHER:
                    raise HTTPException(status_code=503, detail="Live Open-Meteo weather is currently unavailable.")
        if event_type:
            events = [event for event in events if event.type.lower() == event_type.lower()]
        if zone:
            events = [event for event in events if event.zone.lower() == zone.lower()]
        if severity:
            events = [event for event in events if event.severity == severity]
        def normalized_timestamp(event: CivicEvent):
            value = event.timestamp
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        events.sort(key=normalized_timestamp, reverse=True)
        return events[skip : skip + limit]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to retrieve normalized civic events")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve normalized civic events.",
        )


@router.post(
    "",
    response_model=CivicEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Directly ingest normalized civic event",
    description="Ingest a pre-normalized CivicEvent record directly. Validates coordinates, severity, and schema constraints.",
)
async def create_civic_event(payload: CivicEventCreate) -> CivicEvent:
    try:
        return await data_service.create_civic_event(payload)
    except Exception:
        logger.exception("Failed to ingest normalized civic event")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to ingest civic event.",
        )


@router.get(
    "/{event_id}",
    response_model=CivicEvent,
    summary="Get single normalized civic event",
    description="Retrieve a specific normalized civic event by its unique identifier.",
)
async def get_civic_event_by_id(event_id: str) -> CivicEvent:
    event = await data_service.get_civic_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Civic event '{event_id}' not found.",
        )
    return event
