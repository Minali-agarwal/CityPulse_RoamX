from typing import Any, Dict, List, Union
from app.models.civic_event import CivicEvent, EventSource
from app.models.common import Severity
from app.models.incident import IncidentRecord
from app.models.traffic import TrafficRecord
from app.models.weather import WeatherRecord


class NormalizationService:
    """
    Normalization Service.
    Transforms heterogeneous source-specific data (Weather, Traffic, Incidents)
    into a standardized, unified CivicEvent schema for cross-domain aggregation,
    correlation analysis, and dashboard visualization.
    """

    @staticmethod
    def _calculate_weather_severity(rainfall: float, temperature: float) -> Severity:
        """
        Determines civic severity based on meteorological intensity thresholds.
        Monsoon cloudbursts / severe downpours are flagged as high/critical.
        """
        if rainfall >= 45.0 or temperature >= 45.0:
            return Severity.CRITICAL
        elif rainfall >= 20.0 or temperature >= 41.0:
            return Severity.HIGH
        elif rainfall >= 5.0 or temperature >= 38.0:
            return Severity.MEDIUM
        return Severity.LOW

    @classmethod
    def normalize_weather_record(cls, weather: WeatherRecord) -> List[CivicEvent]:
        """
        Converts a WeatherRecord into one or more normalized CivicEvents.
        Produces a primary rainfall/precipitation event if rainfall is present,
        and an atmospheric condition event.
        """
        events: List[CivicEvent] = []
        severity = cls._calculate_weather_severity(weather.rainfall, weather.temperature)

        # 1. Rainfall / Precipitation Event
        if weather.rainfall > 0:
            events.append(
                CivicEvent(
                    id=f"{weather.id}_rainfall",
                    source=EventSource.WEATHER,
                    type="rainfall",
                    value=weather.rainfall,
                    unit="mm",
                    latitude=weather.location.latitude,
                    longitude=weather.location.longitude,
                    zone=weather.location.zone,
                    timestamp=weather.timestamp,
                    severity=severity,
                    metadata={
                        "raw_id": weather.id,
                        "condition": weather.weather_condition,
                        "temperature": weather.temperature,
                        "humidity": weather.humidity,
                        "wind_speed_kmh": weather.wind_speed_kmh,
                        "air_quality_index": weather.air_quality_index,
                        "landmark": weather.location.landmark,
                    },
                )
            )

        # 2. General Ambient Weather Event
        events.append(
            CivicEvent(
                id=f"{weather.id}_ambient",
                source=EventSource.WEATHER,
                type="weather_condition",
                value=weather.temperature,
                unit="°C",
                latitude=weather.location.latitude,
                longitude=weather.location.longitude,
                zone=weather.location.zone,
                timestamp=weather.timestamp,
                severity=severity,
                metadata={
                    "raw_id": weather.id,
                    "condition": weather.weather_condition,
                    "rainfall_mm": weather.rainfall,
                    "humidity": weather.humidity,
                    "wind_speed_kmh": weather.wind_speed_kmh,
                    "landmark": weather.location.landmark,
                },
            )
        )

        return events

    @classmethod
    def normalize_weather_to_primary(cls, weather: WeatherRecord) -> CivicEvent:
        """
        Normalizes a WeatherRecord to its single most significant CivicEvent
        (rainfall if raining, otherwise ambient condition).
        """
        events = cls.normalize_weather_record(weather)
        return events[0]  # First event is rainfall if rain > 0, otherwise ambient

    @classmethod
    def normalize_traffic_record(cls, traffic: TrafficRecord) -> CivicEvent:
        """
        Converts a TrafficRecord into a normalized CivicEvent representing corridor congestion.
        """
        return CivicEvent(
            id=f"{traffic.id}_congestion",
            source=EventSource.TRAFFIC,
            type="congestion",
            value=traffic.congestion_percentage,
            unit="%",
            latitude=traffic.location.latitude,
            longitude=traffic.location.longitude,
            zone=traffic.location.zone,
            timestamp=traffic.timestamp,
            severity=traffic.severity,
            metadata={
                "raw_id": traffic.id,
                "delay_minutes": traffic.delay,
                "road_name": traffic.location.road_name,
                "landmark": traffic.location.landmark,
                "average_speed_kmh": traffic.average_speed_kmh,
                "free_flow_speed_kmh": traffic.free_flow_speed_kmh,
            },
        )

    @classmethod
    def normalize_incident_record(cls, incident: IncidentRecord) -> CivicEvent:
        """
        Converts an IncidentRecord into a normalized CivicEvent.
        """
        return CivicEvent(
            id=f"{incident.id}_event",
            source=EventSource.INCIDENT,
            type=incident.incident_category.value,
            value=1.0,
            unit="incident",
            latitude=incident.location.latitude,
            longitude=incident.location.longitude,
            zone=incident.location.zone,
            timestamp=incident.timestamp,
            severity=incident.severity,
            metadata={
                "raw_id": incident.id,
                "status": incident.status.value,
                "description": incident.description,
                "reported_by": incident.reported_by,
                "estimated_clearance_minutes": incident.estimated_clearance_minutes,
                "landmark": incident.location.landmark,
                "road_name": incident.location.road_name,
            },
        )

    @classmethod
    def normalize_any(
        cls,
        data: Union[WeatherRecord, TrafficRecord, IncidentRecord, Dict[str, Any]],
        source_hint: str = "",
    ) -> List[CivicEvent]:
        """
        Generic dispatcher to normalize any valid model or dictionary into CivicEvents.
        """
        if isinstance(data, WeatherRecord):
            return cls.normalize_weather_record(data)
        elif isinstance(data, TrafficRecord):
            return [cls.normalize_traffic_record(data)]
        elif isinstance(data, IncidentRecord):
            return [cls.normalize_incident_record(data)]
        elif isinstance(data, dict):
            source = data.get("source", source_hint).lower()
            if source == "weather" or "rainfall" in data or "weather_condition" in data:
                return cls.normalize_weather_record(WeatherRecord.model_validate(data))
            elif source == "traffic" or "congestion_percentage" in data:
                return [cls.normalize_traffic_record(TrafficRecord.model_validate(data))]
            elif source == "incident" or "incident_category" in data:
                return [cls.normalize_incident_record(IncidentRecord.model_validate(data))]
            else:
                # If already matches CivicEvent schema
                return [CivicEvent.model_validate(data)]
        raise ValueError(f"Unsupported record type for normalization: {type(data)}")
