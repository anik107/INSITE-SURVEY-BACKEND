"""Session repository for refresh token management."""
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for Session collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "sessions", Session)

    async def find_by_jti(self, jti: str) -> Session | None:
        """Find active session by token JTI."""
        return await self.find_one({
            "token_jti": jti,
            "revoked": False,
            "expires_at": {"$gt": datetime.utcnow()},
        })

    async def find_user_sessions(
        self,
        user_id: str | ObjectId,
        include_revoked: bool = False,
    ) -> list[Session]:
        """Find all sessions for a user."""
        filter = {"user_id": self._to_object_id(user_id)}
        if not include_revoked:
            filter["revoked"] = False
            filter["expires_at"] = {"$gt": datetime.utcnow()}
        return await self.find_all(filter, sort=[("created_at", -1)])

    async def revoke(self, jti: str) -> bool:
        """Revoke session by JTI."""
        result = await self.collection.update_one(
            {"token_jti": jti},
            {"$set": {"revoked": True, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def revoke_by_id(self, session_id: str | ObjectId) -> bool:
        """Revoke session by ID."""
        result = await self.collection.update_one(
            {"_id": self._to_object_id(session_id)},
            {"$set": {"revoked": True, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def revoke_all_for_user(self, user_id: str | ObjectId) -> int:
        """Revoke all active sessions for user."""
        result = await self.collection.update_many(
            {
                "user_id": self._to_object_id(user_id),
                "revoked": False,
            },
            {"$set": {"revoked": True, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count

    async def cleanup_expired(self) -> int:
        """Remove expired sessions (called periodically or by TTL index)."""
        result = await self.collection.delete_many({
            "expires_at": {"$lt": datetime.utcnow()}
        })
        return result.deleted_count

    async def is_valid(self, jti: str) -> bool:
        """Check if session with JTI is valid (not revoked, not expired)."""
        return await self.exists({
            "token_jti": jti,
            "revoked": False,
            "expires_at": {"$gt": datetime.utcnow()},
        })
