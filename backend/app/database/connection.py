import asyncio
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.config import get_settings

logger = logging.getLogger("citypulse.database")


class MongoDBConnection:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    connected: bool = False


mongo_conn = MongoDBConnection()


async def connect_to_mongo() -> bool:
    """
    Initializes connection to MongoDB using Motor.
    If MongoDB is unreachable or timeout occurs, gracefully falls back to synthetic data
    without halting application startup.
    """
    settings = get_settings()

    if not settings.MONGODB_URI:
        logger.info("MONGODB_URI is not set. Operating in Synthetic/Local Data mode.")
        mongo_conn.connected = False
        return False

    try:
        logger.info(
            f"Attempting to connect to MongoDB ({settings.DATABASE_NAME}) with {settings.MONGODB_CONNECT_TIMEOUT_MS}ms timeout..."
        )
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
        )

        # Non-blocking ping check with strict timeout
        await asyncio.wait_for(
            client.admin.command("ping"),
            timeout=(settings.MONGODB_CONNECT_TIMEOUT_MS / 1000.0),
        )

        mongo_conn.client = client
        mongo_conn.database = client[settings.DATABASE_NAME]
        mongo_conn.connected = True
        logger.info(f"Successfully connected to MongoDB database: '{settings.DATABASE_NAME}'")
        return True

    except (ServerSelectionTimeoutError, ConnectionFailure, asyncio.TimeoutError, Exception) as exc:
        logger.warning(
            f"MongoDB connection failed: {exc}. "
            f"CityPulse is operating seamlessly with local synthetic JSON data."
        )
        mongo_conn.client = None
        mongo_conn.database = None
        mongo_conn.connected = False
        return False


async def close_mongo_connection() -> None:
    """Closes active MongoDB Motor client on shutdown."""
    if mongo_conn.client:
        logger.info("Closing MongoDB connection...")
        mongo_conn.client.close()
        mongo_conn.client = None
        mongo_conn.database = None
        mongo_conn.connected = False
        logger.info("MongoDB connection closed.")


def get_database() -> Optional[AsyncIOMotorDatabase]:
    """Returns database instance if connected, else None."""
    if mongo_conn.connected and mongo_conn.database is not None:
        return mongo_conn.database
    return None


def is_mongo_connected() -> bool:
    """Returns boolean indicating if MongoDB is actively connected."""
    return mongo_conn.connected
