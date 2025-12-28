"""MongoDB connection management for the FastAPI application."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class MongoDB:
    """Simple MongoDB client wrapper that keeps a singleton connection."""

    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Create a MongoDB client if it does not already exist."""

        if self._client is None:
            self._client = AsyncIOMotorClient(settings.mongodb_uri)
            self._db = self._client[settings.mongodb_db]

    async def close(self) -> None:
        """Close the MongoDB client."""

        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise RuntimeError("MongoDB client is not initialized. Call connect() first.")
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("MongoDB database is not initialized. Call connect() first.")
        return self._db


mongodb = MongoDB()


async def connect_to_mongo() -> None:
    """Connect to MongoDB."""
    await mongodb.connect()


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    await mongodb.close()


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency to retrieve the MongoDB database instance."""
    return mongodb.db


@asynccontextmanager
async def lifespan(app):  # type: ignore[annotation-unchecked]
    """FastAPI lifespan hook that connects to MongoDB on startup and closes on shutdown."""

    await mongodb.connect()
    try:
        yield
    finally:
        await mongodb.close()
