import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database.connection import is_mongo_connected
from app.models.common import Location
from app.models.weather import WeatherRecord
from app.services.live_weather import LiveWeatherUnavailableError
import app.routes.weather as weather_route
import app.routes.civic_events as civic_events_route
import app.routes.dashboard as dashboard_route


def sample_live_weather() -> WeatherRecord:
    return WeatherRecord(
        id="open_meteo_jaipur_current",
        temperature=29.0,
        rainfall=0.0,
        humidity=45.0,
        weather_condition="Mainly clear",
        location=Location(latitude=26.9124, longitude=75.7873, zone="Jaipur"),
        timestamp=datetime.now(timezone.utc),
        data_source="Open-Meteo (live forecast model)",
        fetched_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CityPulse Backend"
    assert "database" in data
    assert "uptimeSeconds" in data
    assert "demonstrationCity" in data
    assert "Jaipur" in data["demonstrationCity"]


@pytest.mark.anyio
async def test_weather_endpoints(client: AsyncClient, monkeypatch):
    current = sample_live_weather()

    async def get_live_weather(*, refresh=False):
        return current

    monkeypatch.setattr(weather_route, "get_jaipur_weather", get_live_weather)
    # 1. GET list
    response = await client.get("/api/weather")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    sample = data[0]
    assert "temperature" in sample
    assert "rainfall" in sample
    assert "humidity" in sample
    assert "weather_condition" in sample
    assert "location" in sample

    # 2. Filter by zone
    res_filtered = await client.get("/api/weather?zone=Jaipur")
    assert res_filtered.status_code == 200
    filtered_data = res_filtered.json()
    assert len(filtered_data) > 0
    for item in filtered_data:
        assert item["location"]["zone"].lower() == "jaipur"

    # 3. POST new weather record
    payload = {
        "temperature": 27.5,
        "rainfall": 15.0,
        "humidity": 82.0,
        "weather_condition": "Thunderstorm",
        "location": {
            "latitude": 26.8530,
            "longitude": 75.8150,
            "zone": "Malviya Nagar",
            "landmark": "Gaurav Tower",
        },
        "timestamp": "2026-09-24T16:30:00+05:30",
    }
    create_res = await client.post("/api/weather", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["temperature"] == 27.5
    assert created_data["rainfall"] == 15.0


@pytest.mark.anyio
async def test_weather_rate_limit_has_clear_service_message(client: AsyncClient, monkeypatch):
    async def rate_limited(*, refresh=False):
        raise LiveWeatherUnavailableError("Weather service rate limit reached. Please try again later.")

    monkeypatch.setattr(weather_route, "get_jaipur_weather", rate_limited)
    response = await client.get("/api/weather")
    assert response.status_code == 503
    assert response.json()["detail"] == "Weather service rate limit reached. Please try again later."


@pytest.mark.anyio
async def test_traffic_endpoints(client: AsyncClient):
    # 1. GET list
    response = await client.get("/api/traffic")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    sample = data[0]
    assert "congestion_percentage" in sample
    assert "delay" in sample
    assert "severity" in sample
    assert "location" in sample

    # 2. Filter by severity
    res_filtered = await client.get("/api/traffic?severity=critical")
    assert res_filtered.status_code == 200
    critical_records = res_filtered.json()
    assert len(critical_records) > 0
    for rec in critical_records:
        assert rec["severity"] == "critical"

    # 3. POST new traffic record
    payload = {
        "congestion_percentage": 92.0,
        "delay": 40.0,
        "location": {
            "latitude": 26.8220,
            "longitude": 75.7950,
            "zone": "Sanganer",
            "road_name": "Tonk Road",
        },
        "timestamp": "2026-09-24T16:30:00+05:30",
        "severity": "critical",
    }
    create_res = await client.post("/api/traffic", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["congestion_percentage"] == 92.0


@pytest.mark.anyio
async def test_incidents_endpoints(client: AsyncClient):
    # 1. GET list
    response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if not is_mongo_connected():
        assert data == []
        return
    assert len(data) > 0
    sample = data[0]
    assert "incident_category" in sample
    assert "description" in sample
    assert "severity" in sample
    assert "status" in sample

    # 2. Filter by category
    res_wl = await client.get("/api/incidents?category=waterlogging")
    assert res_wl.status_code == 200
    wl_items = res_wl.json()
    assert len(wl_items) > 0
    for item in wl_items:
        assert item["incident_category"] == "waterlogging"

    # 3. POST new incident
    payload = {
        "incident_category": "waterlogging",
        "description": "Culvert overflow causing street submergence on Gopalpura bypass",
        "severity": "high",
        "location": {
            "latitude": 26.8450,
            "longitude": 75.7890,
            "zone": "Mansarovar",
            "landmark": "Gopalpura Crossing",
        },
        "timestamp": "2026-09-24T16:30:00+05:30",
        "status": "reported",
    }
    create_res = await client.post("/api/incidents", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["incident_category"] == "waterlogging"


@pytest.mark.anyio
async def test_civic_events_endpoints(client: AsyncClient, monkeypatch):
    async def get_live_weather(*, refresh=False):
        return sample_live_weather()

    monkeypatch.setattr(civic_events_route, "get_jaipur_weather", get_live_weather)
    response = await client.get("/api/civic-events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) > 0

    # Verify CivicEvent schema conformity
    sample = events[0]
    expected_fields = ["id", "source", "type", "value", "unit", "latitude", "longitude", "zone", "timestamp", "severity", "metadata"]
    for field in expected_fields:
        assert field in sample, f"Missing field '{field}' in CivicEvent"

    # Filter by source
    res_weather = await client.get("/api/civic-events?source=weather")
    assert res_weather.status_code == 200
    w_events = res_weather.json()
    for ev in w_events:
        assert ev["source"] == "weather"

    res_traffic = await client.get("/api/civic-events?source=traffic")
    assert res_traffic.status_code == 200
    t_events = res_traffic.json()
    for ev in t_events:
        assert ev["source"] == "traffic"


@pytest.mark.anyio
async def test_dashboard_endpoint(client: AsyncClient, monkeypatch):
    async def get_live_weather(*, refresh=False):
        return sample_live_weather()

    async def no_recommendations():
        return {"recommendations": [], "data_sources": {"crowd_prediction": "test model"}}

    monkeypatch.setattr(dashboard_route, "get_jaipur_weather", get_live_weather)
    monkeypatch.setattr(dashboard_route, "get_recommendations", no_recommendations)
    response = await client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()

    # Validate high level fields
    assert "healthScore" in data
    assert 0 <= data["healthScore"] <= 100
    assert "weather" in data
    assert "traffic" in data
    assert "incidents" in data
    assert "alerts" in data
    assert "latestEvents" in data
    assert "anomalies" in data
    assert "correlations" in data
    assert "summary" in data

    # Validate weather summary
    assert "average_temperature" in data["weather"]
    assert "average_rainfall" in data["weather"]
    assert "dominant_condition" in data["weather"]

    # Validate traffic summary
    assert "average_congestion" in data["weather"] or "average_congestion" in data["traffic"]
    assert "most_congested_corridor" in data["traffic"]

    # Validate incident summary
    assert "total_incidents" in data["incidents"]
    assert "active_incidents" in data["incidents"]
    assert "breakdown_by_category" in data["incidents"]

    # Validate ML placeholders are empty / null
    assert data["anomalies"] == []
    assert data["correlations"] == []
    assert isinstance(data["summary"], str)
    assert data["data_sources"]["weather"].startswith("Live")


@pytest.mark.anyio
async def test_validation_errors(client: AsyncClient):
    # 1. Invalid coordinates: latitude > 90
    bad_payload = {
        "temperature": 25.0,
        "rainfall": 10.0,
        "humidity": 60.0,
        "weather_condition": "Rain",
        "location": {
            "latitude": 125.0,  # Invalid!
            "longitude": 75.0,
            "zone": "Malviya Nagar",
        },
        "timestamp": "2026-09-24T15:00:00+05:30",
    }
    res = await client.post("/api/weather", json=bad_payload)
    assert res.status_code == 422
    err = res.json()
    assert "error" in err

    # 2. Invalid negative rainfall
    bad_rain = {
        "temperature": 25.0,
        "rainfall": -5.0,  # Invalid!
        "humidity": 60.0,
        "weather_condition": "Rain",
        "location": {
            "latitude": 26.85,
            "longitude": 75.80,
            "zone": "Malviya Nagar",
        },
        "timestamp": "2026-09-24T15:00:00+05:30",
    }
    res_rain = await client.post("/api/weather", json=bad_rain)
    assert res_rain.status_code == 422

    # 3. Invalid congestion > 100
    bad_traffic = {
        "congestion_percentage": 150.0,  # Invalid!
        "delay": 10.0,
        "location": {
            "latitude": 26.85,
            "longitude": 75.80,
            "zone": "Malviya Nagar",
        },
        "timestamp": "2026-09-24T15:00:00+05:30",
        "severity": "high",
    }
    res_tr = await client.post("/api/traffic", json=bad_traffic)
    assert res_tr.status_code == 422

    # 4. Invalid severity string
    bad_severity = {
        "congestion_percentage": 50.0,
        "delay": 10.0,
        "location": {
            "latitude": 26.85,
            "longitude": 75.80,
            "zone": "Malviya Nagar",
        },
        "timestamp": "2026-09-24T15:00:00+05:30",
        "severity": "super_extreme",  # Invalid enum!
    }
    res_sev = await client.post("/api/traffic", json=bad_severity)
    assert res_sev.status_code == 422


@pytest.mark.anyio
async def test_single_resource_lookups_and_patch(client: AsyncClient, monkeypatch):
    async def get_live_weather(*, refresh=False):
        return sample_live_weather()

    monkeypatch.setattr(weather_route, "get_jaipur_weather", get_live_weather)
    # 1. Weather by ID
    w_list = (await client.get("/api/weather")).json()
    first_w_id = w_list[0]["id"]
    w_single = await client.get(f"/api/weather/{first_w_id}")
    assert w_single.status_code == 200
    assert w_single.json()["id"] == first_w_id

    w_not_found = await client.get("/api/weather/non_existent_weather_id")
    assert w_not_found.status_code == 404

    # 2. Traffic by ID
    t_list = (await client.get("/api/traffic")).json()
    first_t_id = t_list[0]["id"]
    t_single = await client.get(f"/api/traffic/{first_t_id}")
    assert t_single.status_code == 200
    assert t_single.json()["id"] == first_t_id

    t_not_found = await client.get("/api/traffic/non_existent_traffic_id")
    assert t_not_found.status_code == 404

    # 3. Incident by ID & PATCH
    inc_list = (await client.get("/api/incidents")).json()
    if is_mongo_connected() and inc_list:
        first_inc_id = inc_list[0]["id"]
        inc_single = await client.get(f"/api/incidents/{first_inc_id}")
        assert inc_single.status_code == 200
        assert inc_single.json()["id"] == first_inc_id

        patch_res = await client.patch(
            f"/api/incidents/{first_inc_id}",
            json={"status": "in_progress", "estimated_clearance_minutes": 45},
        )
        assert patch_res.status_code == 200
        patched_data = patch_res.json()
        assert patched_data["status"] == "in_progress"
        assert patched_data["estimated_clearance_minutes"] == 45

    # 4. Civic Event POST & GET by ID
    event_payload = {
        "source": "incident",
        "type": "waterlogging",
        "value": 1.0,
        "unit": "incident",
        "latitude": 26.8220,
        "longitude": 75.7950,
        "zone": "Sanganer",
        "severity": "critical",
        "metadata": {"test": True},
    }
    create_ev_res = await client.post("/api/civic-events", json=event_payload)
    assert create_ev_res.status_code == 201
    created_ev = create_ev_res.json()
    assert "id" in created_ev
    ev_id = created_ev["id"]

    ev_fetch = await client.get(f"/api/civic-events/{ev_id}")
    assert ev_fetch.status_code == 200
    assert ev_fetch.json()["id"] == ev_id
