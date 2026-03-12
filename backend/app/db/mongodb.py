from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database as SyncDatabase
from app.config import settings

# Async client (for FastAPI endpoints)
_async_client: AsyncIOMotorClient | None = None
_async_db: AsyncIOMotorDatabase | None = None

# Sync client (for Celery tasks)
_sync_client: MongoClient | None = None


async def connect_db():
    """Initialize async MongoDB connection."""
    global _async_client, _async_db
    _async_client = AsyncIOMotorClient(settings.MONGODB_URL)
    _async_db = _async_client[settings.MONGODB_DB_NAME]


async def close_db():
    """Close async MongoDB connection."""
    global _async_client
    if _async_client:
        _async_client.close()


def get_database() -> AsyncIOMotorDatabase:
    """Get the async MongoDB database instance."""
    if _async_db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _async_db


def get_collection(name: str):
    """Get an async MongoDB collection."""
    return get_database()[name]


def get_sync_database() -> SyncDatabase:
    """Get a sync MongoDB database for Celery tasks."""
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(settings.MONGODB_URL)
    return _sync_client[settings.MONGODB_DB_NAME]


def get_sync_collection(name: str):
    """Get a sync MongoDB collection for Celery tasks."""
    return get_sync_database()[name]
