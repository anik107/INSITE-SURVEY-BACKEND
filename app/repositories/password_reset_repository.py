"""Password reset token repository for database operations."""
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    """Repository for PasswordResetToken collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "password_reset_tokens", PasswordResetToken)

    async def find_valid_token(self, token: str) -> PasswordResetToken | None:
        """Find a valid (non-expired, non-used) reset token."""
        now = datetime.utcnow()
        return await self.find_one({
            "token": token,
            "used": False,
            "expires_at": {"$gt": now},
        })

    async def mark_as_used(self, token_id: str | ObjectId) -> bool:
        """Mark a reset token as used."""
        result = await self.collection.update_one(
            {"_id": self._to_object_id(token_id)},
            {"$set": {"used": True, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    async def delete_expired(self) -> int:
        """Delete all expired tokens."""
        now = datetime.utcnow()
        result = await self.collection.delete_many({"expires_at": {"$lt": now}})
        return result.deleted_count

    async def revoke_all_for_user(self, user_id: str | ObjectId) -> int:
        """Revoke all reset tokens for a user."""
        result = await self.collection.update_many(
            {"user_id": self._to_object_id(user_id), "used": False},
            {"$set": {"used": True, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count
