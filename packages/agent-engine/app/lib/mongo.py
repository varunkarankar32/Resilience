"""
ResilienceAI Agent Engine — Database Connection
Ports the JanShakti-AI database.py graceful degradation pattern.
Uses Motor (async) + Beanie (Pydantic-style ODM).
"""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings
from app.models.incident import Incident
from app.models.service_topology import ServiceTopology

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_mongo() -> None:
    """Initialize MongoDB connection with graceful degradation fallback."""
    global _client, _db
    try:
        _client = AsyncIOMotorClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        _db = _client[settings.mongo_db_name]
        await _client.admin.command("ping")

        await init_beanie(
            database=_db,
            document_models=[Incident, ServiceTopology],
        )

        print(f"[MongoDB] Connected to '{settings.mongo_db_name}' — Beanie initialized")
    except Exception as exc:
        print(f"[MongoDB] ⚠️  Connection failed — running in degraded mode: {exc}")
        _client = None
        _db = None


async def close_mongo() -> None:
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("[MongoDB] Disconnected")


def get_db() -> AsyncIOMotorDatabase:
    """Return current database instance."""
    if _db is None:
        raise RuntimeError("[MongoDB] Database not connected. Call init_mongo() first.")
    return _db
