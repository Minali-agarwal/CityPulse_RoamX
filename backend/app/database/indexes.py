import logging
from app.database.connection import get_database, is_mongo_connected

logger = logging.getLogger("citypulse.indexes")


async def ensure_indexes() -> None:
    """
    Creates MongoDB indexes for all CityPulse collections.
    Called once during application startup after the connection is established.
    Skips silently if MongoDB is not connected.
    """
    if not is_mongo_connected():
        return

    db = get_database()
    if db is None:
        return

    try:
        # weather: query by zone, timestamp, condition
        await db.weather.create_index("id", unique=True, background=True)
        await db.weather.create_index("location.zone", background=True)
        await db.weather.create_index("timestamp", background=True)
        await db.weather.create_index("weather_condition", background=True)

        # traffic: query by zone, severity, congestion
        await db.traffic.create_index("id", unique=True, background=True)
        await db.traffic.create_index("location.zone", background=True)
        await db.traffic.create_index("timestamp", background=True)
        await db.traffic.create_index("severity", background=True)
        await db.traffic.create_index("congestion_percentage", background=True)

        # incidents: query by zone, category, severity, status
        await db.incidents.create_index("id", unique=True, background=True)
        await db.incidents.create_index("location.zone", background=True)
        await db.incidents.create_index("timestamp", background=True)
        await db.incidents.create_index("severity", background=True)
        await db.incidents.create_index("status", background=True)
        await db.incidents.create_index("incident_category", background=True)

        # civic_events: query by source, type, zone, severity
        await db.civic_events.create_index("id", unique=True, background=True)
        await db.civic_events.create_index("source", background=True)
        await db.civic_events.create_index("zone", background=True)
        await db.civic_events.create_index("timestamp", background=True)
        await db.civic_events.create_index("severity", background=True)

        logger.info("MongoDB indexes ensured for all CityPulse collections.")
    except Exception as exc:
        logger.warning(f"Non-fatal: could not create MongoDB indexes: {exc}")
