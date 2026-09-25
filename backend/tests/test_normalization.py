from datetime import datetime, timezone
from app.models.common import Location, Severity
from app.models.incident import IncidentCategory, IncidentRecord, IncidentStatus
from app.models.traffic import TrafficRecord
from app.models.weather import WeatherRecord
from app.services.normalization import NormalizationService


def test_weather_normalization_heavy_rain():
    weather = WeatherRecord(
        id="test_w_01",
        temperature=24.0,
        rainfall=48.0,
        humidity=95.0,
        weather_condition="Torrential Downpour",
        location=Location(
            latitude=26.8220,
            longitude=75.7950,
            zone="Sanganer",
            road_name="Tonk Road",
        ),
        timestamp=datetime.now(timezone.utc),
    )

    events = NormalizationService.normalize_weather_record(weather)
    assert len(events) == 2

    # Event 1: Rainfall
    rain_event = events[0]
    assert rain_event.source == "weather"
    assert rain_event.type == "rainfall"
    assert rain_event.value == 48.0
    assert rain_event.unit == "mm"
    assert rain_event.severity == Severity.CRITICAL
    assert rain_event.zone == "Sanganer"
    assert rain_event.latitude == 26.8220
    assert rain_event.longitude == 75.7950

    # Event 2: Ambient
    ambient_event = events[1]
    assert ambient_event.type == "weather_condition"
    assert ambient_event.value == 24.0
    assert ambient_event.unit == "°C"


def test_weather_normalization_dry_day():
    weather = WeatherRecord(
        id="test_w_02",
        temperature=32.0,
        rainfall=0.0,
        humidity=50.0,
        weather_condition="Clear",
        location=Location(
            latitude=26.9080,
            longitude=75.8010,
            zone="C-Scheme",
        ),
        timestamp=datetime.now(timezone.utc),
    )

    events = NormalizationService.normalize_weather_record(weather)
    # Rainfall is 0, so only ambient event is produced
    assert len(events) == 1
    assert events[0].type == "weather_condition"
    assert events[0].severity == Severity.LOW


def test_traffic_normalization():
    traffic = TrafficRecord(
        id="test_tr_01",
        congestion_percentage=89.5,
        delay=35.0,
        location=Location(
            latitude=26.8530,
            longitude=75.8150,
            zone="Malviya Nagar",
            road_name="JLN Marg",
        ),
        timestamp=datetime.now(timezone.utc),
        severity=Severity.CRITICAL,
    )

    event = NormalizationService.normalize_traffic_record(traffic)
    assert event.source == "traffic"
    assert event.type == "congestion"
    assert event.value == 89.5
    assert event.unit == "%"
    assert event.severity == Severity.CRITICAL
    assert event.metadata["delay_minutes"] == 35.0
    assert event.metadata["road_name"] == "JLN Marg"


def test_incident_normalization():
    incident = IncidentRecord(
        id="test_inc_01",
        incident_category=IncidentCategory.WATERLOGGING,
        description="Underpass flooded with 3ft water",
        severity=Severity.CRITICAL,
        location=Location(
            latitude=26.8220,
            longitude=75.7950,
            zone="Sanganer",
            landmark="Durgapura Underpass",
        ),
        timestamp=datetime.now(timezone.utc),
        status=IncidentStatus.IN_PROGRESS,
    )

    event = NormalizationService.normalize_incident_record(incident)
    assert event.source == "incident"
    assert event.type == "waterlogging"
    assert event.value == 1.0
    assert event.unit == "incident"
    assert event.severity == Severity.CRITICAL
    assert event.metadata["status"] == "in_progress"
    assert event.metadata["landmark"] == "Durgapura Underpass"
