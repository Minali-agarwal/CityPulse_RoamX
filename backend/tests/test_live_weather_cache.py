import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import httpx

import app.services.live_weather as live_weather
from app.models.common import Location
from app.models.weather import WeatherRecord


def make_weather() -> WeatherRecord:
    return WeatherRecord(
        id="cached-open-meteo-test",
        temperature=30.0,
        rainfall=0.0,
        humidity=40.0,
        weather_condition="Clear sky",
        location=Location(latitude=26.9124, longitude=75.7873, zone="Jaipur"),
        timestamp=datetime.now(timezone.utc),
        data_source="Open-Meteo (live forecast model)",
        fetched_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def reset_cache(monkeypatch):
    monkeypatch.setattr(live_weather, "_cache", None)
    monkeypatch.setattr(live_weather, "_retry_after", None)
    monkeypatch.setattr(live_weather, "_last_error", None)
    monkeypatch.setattr(live_weather, "_cache_lock", asyncio.Lock())


@pytest.mark.anyio
async def test_fresh_cache_and_refresh_do_not_call_provider(monkeypatch, reset_cache):
    record = make_weather()
    monkeypatch.setattr(live_weather, "_cache", (datetime.now(timezone.utc), record))
    calls = 0

    async def provider():
        nonlocal calls
        calls += 1
        return record

    monkeypatch.setattr(live_weather, "_fetch_jaipur_weather", provider)
    assert await live_weather.get_jaipur_weather() is record
    assert await live_weather.get_jaipur_weather(refresh=True) is record
    assert calls == 0


@pytest.mark.anyio
async def test_concurrent_refreshes_make_one_provider_request(monkeypatch, reset_cache):
    calls = 0
    record = make_weather()

    async def provider():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return record

    monkeypatch.setattr(live_weather, "_fetch_jaipur_weather", provider)
    results = await asyncio.gather(*(live_weather.get_jaipur_weather(refresh=True) for _ in range(6)))
    assert calls == 1
    assert all(item.temperature == record.temperature for item in results)


@pytest.mark.anyio
async def test_rate_limit_uses_expired_cache_and_throttles_retries(monkeypatch, reset_cache):
    record = make_weather()
    monkeypatch.setattr(live_weather, "_cache", (datetime.now(timezone.utc) - timedelta(minutes=11), record))
    calls = 0

    async def rate_limited_provider():
        nonlocal calls
        calls += 1
        raise live_weather.LiveWeatherUnavailableError(live_weather.RATE_LIMIT_MESSAGE)

    monkeypatch.setattr(live_weather, "_fetch_jaipur_weather", rate_limited_provider)
    first = await live_weather.get_jaipur_weather(refresh=True)
    second = await live_weather.get_jaipur_weather(refresh=True)
    assert calls == 1
    assert first.is_stale and second.is_stale
    assert first.warning == live_weather.RATE_LIMIT_MESSAGE
    assert first.temperature == record.temperature


@pytest.mark.anyio
async def test_rate_limit_without_cache_returns_clear_message_and_throttles(monkeypatch, reset_cache):
    calls = 0

    async def rate_limited_provider():
        nonlocal calls
        calls += 1
        raise live_weather.LiveWeatherUnavailableError(live_weather.RATE_LIMIT_MESSAGE)

    monkeypatch.setattr(live_weather, "_fetch_jaipur_weather", rate_limited_provider)
    for _ in range(2):
        with pytest.raises(live_weather.LiveWeatherUnavailableError, match="Weather service rate limit reached"):
            await live_weather.get_jaipur_weather(refresh=True)
    assert calls == 1


@pytest.mark.anyio
async def test_http_429_is_converted_to_clear_error_and_not_retried(monkeypatch, reset_cache):
    calls = 0

    class RateLimitedClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, *_args, **_kwargs):
            nonlocal calls
            calls += 1
            request = httpx.Request("GET", live_weather.API_URL)
            return httpx.Response(429, request=request)

    monkeypatch.setattr(live_weather.httpx, "AsyncClient", lambda **_kwargs: RateLimitedClient())
    for _ in range(2):
        with pytest.raises(live_weather.LiveWeatherUnavailableError, match="Weather service rate limit reached"):
            await live_weather.get_jaipur_weather()
    assert calls == 1
