"""Live Jaipur weather from Open-Meteo; this service never falls back to seed data."""
import asyncio
from datetime import datetime, timezone, timedelta
import email.utils
import logging
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from app.models.common import Location, Severity
from app.models.weather import WeatherForecast, WeatherRecord

API_URL = "https://api.open-meteo.com/v1/forecast"
JAIPUR_LATITUDE = 26.9124
JAIPUR_LONGITUDE = 75.7873
_cache: tuple[datetime, WeatherRecord] | None = None
_CACHE_SECONDS = 600
_FAILURE_COOLDOWN_SECONDS = 600
_cache_lock = asyncio.Lock()
_retry_after: Optional[datetime] = None
_last_error: Optional[str] = None
logger = logging.getLogger("citypulse.live_weather")
_WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 56: "Freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain", 66: "Freezing rain",
    67: "Heavy freezing rain", 71: "Slight snowfall", 73: "Moderate snowfall",
    75: "Heavy snowfall", 77: "Snow grains", 80: "Rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


class LiveWeatherUnavailableError(RuntimeError):
    """Open-Meteo could not provide current conditions."""


RATE_LIMIT_MESSAGE = "Weather service rate limit reached. Please try again later."


def _cached_copy(*, warning: Optional[str] = None) -> WeatherRecord:
    assert _cache is not None
    return _cache[1].model_copy(update={"is_stale": True, "warning": warning})


def _is_cache_fresh(now: datetime) -> bool:
    return bool(_cache and (now - _cache[0]).total_seconds() < _CACHE_SECONDS)


def _retry_delay(response: httpx.Response) -> int:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(_FAILURE_COOLDOWN_SECONDS, int(value))
        except ValueError:
            try:
                when = email.utils.parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                return max(_FAILURE_COOLDOWN_SECONDS, int((when - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
    return _FAILURE_COOLDOWN_SECONDS


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata")) if parsed.tzinfo is None else parsed


def _condition(code: int | None) -> str:
    if code is None:
        return "Not reported"
    return _WMO.get(code, "Unknown weather condition")


async def _fetch_jaipur_weather() -> WeatherRecord:
    global _retry_after, _last_error
    now = datetime.now(timezone.utc)
    params = {
        "latitude": JAIPUR_LATITUDE,
        "longitude": JAIPUR_LONGITUDE,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 3,
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(API_URL, params=params)
            if response.status_code == 429:
                _retry_after = datetime.now(timezone.utc) + timedelta(seconds=_retry_delay(response))
                _last_error = RATE_LIMIT_MESSAGE
                raise LiveWeatherUnavailableError(RATE_LIMIT_MESSAGE)
            response.raise_for_status()
            payload = response.json()
        current = payload["current"]
        code = int(current["weather_code"])
        hourly = payload.get("hourly", {})
        hourly_times = hourly.get("time", [])
        forecast = []
        for idx, time_value in enumerate(hourly_times):
            timestamp = _timestamp(time_value)
            if timestamp <= _timestamp(current["time"]):
                continue
            forecast.append(WeatherForecast(
                timestamp=timestamp,
                temperature=hourly["temperature_2m"][idx],
                humidity=(hourly.get("relative_humidity_2m") or [None] * len(hourly_times))[idx],
                wind_speed_kmh=(hourly.get("wind_speed_10m") or [None] * len(hourly_times))[idx],
                precipitation=(hourly.get("precipitation") or [None] * len(hourly_times))[idx],
                precipitation_probability=(hourly.get("precipitation_probability") or [None] * len(hourly_times))[idx],
                weather_condition=_condition((hourly.get("weather_code") or [None] * len(hourly_times))[idx]),
            ))
            if len(forecast) >= 24:
                break
        record = WeatherRecord(
            id="open_meteo_jaipur_current",
            temperature=current["temperature_2m"],
            rainfall=current["precipitation"],
            humidity=current["relative_humidity_2m"],
            weather_condition=_condition(code),
            location=Location(
                latitude=payload.get("latitude", JAIPUR_LATITUDE),
                longitude=payload.get("longitude", JAIPUR_LONGITUDE),
                zone="Jaipur",
                address="Jaipur, Rajasthan, India",
            ),
            timestamp=_timestamp(current["time"]),
            wind_speed_kmh=current["wind_speed_10m"],
            air_quality_index=None,
            data_source="Open-Meteo (live forecast model)",
            fetched_at=now,
            weather_code=code,
            forecast=forecast,
            is_stale=False,
            warning=None,
        )
        return record
    except LiveWeatherUnavailableError:
        raise
    except Exception as exc:
        logger.warning("Open-Meteo request failed (%s).", type(exc).__name__)
        raise LiveWeatherUnavailableError(
            f"Open-Meteo weather data is temporarily unavailable ({type(exc).__name__})."
        ) from exc


async def get_jaipur_weather(*, refresh: bool = False) -> WeatherRecord:
    """Return cached Open-Meteo data and serialize refreshes to one request.

    ``refresh`` requests an update but never bypasses the ten-minute interval.
    An expired cache is served with a warning if the provider is unavailable.
    """
    global _cache, _retry_after, _last_error
    now = datetime.now(timezone.utc)
    if _is_cache_fresh(now):
        return _cache[1]

    async with _cache_lock:
        now = datetime.now(timezone.utc)
        if _is_cache_fresh(now):
            return _cache[1]
        if _retry_after and now < _retry_after:
            if _cache:
                return _cached_copy(warning=_last_error or "Showing cached Open-Meteo weather while the provider is unavailable.")
            raise LiveWeatherUnavailableError(_last_error or "Open-Meteo weather data is temporarily unavailable.")

        _retry_after = None
        _last_error = None
        try:
            record = await _fetch_jaipur_weather()
            _cache = (datetime.now(timezone.utc), record)
            _retry_after = None
            _last_error = None
            return record
        except LiveWeatherUnavailableError as exc:
            if _retry_after is None:
                _retry_after = datetime.now(timezone.utc) + timedelta(seconds=_FAILURE_COOLDOWN_SECONDS)
                _last_error = str(exc)
            if _cache:
                return _cached_copy(warning=_last_error)
            raise
