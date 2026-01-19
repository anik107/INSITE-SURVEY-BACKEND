"""User repository for database operations."""
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import User, UserRole, UserStatus
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "users", User)

    async def find_by_username(self, username: str) -> User | None:
        """Find user by username (case-insensitive)."""
        return await self.find_one({
            "username": {"$regex": f"^{username}$", "$options": "i"}
        })

    async def find_by_email(self, email: str) -> User | None:
        """Find user by email (case-insensitive)."""
        return await self.find_one({
            "email": {"$regex": f"^{email}$", "$options": "i"}
        })

    async def find_by_attraction(
        self,
        attraction_id: str | ObjectId,
    ) -> list[User]:
        """Find all users for an attraction."""
        return await self.find_all({
            "attraction_id": self._to_object_id(attraction_id)
        })

    async def find_attraction_admins(
        self,
        status: UserStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Find all attraction admins with optional status filter."""
        filter = {"role": UserRole.ATTRACTION_ADMIN.value}
        if status:
            filter["status"] = status.value
        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def count_attraction_admins(self, status: UserStatus | None = None) -> int:
        """Count attraction admins with optional status filter."""
        filter = {"role": UserRole.ATTRACTION_ADMIN.value}
        if status:
            filter["status"] = status.value
        return await self.count(filter)

    async def find_all_admins(
        self,
        status: UserStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Find all admins (super and attraction) with optional status filter."""
        filter: dict = {}
        if status:
            filter["status"] = status.value
        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("role", 1), ("created_at", -1)],  # Super admins first
        )

    async def count_all_admins(self, status: UserStatus | None = None) -> int:
        """Count all admins with optional status filter."""
        filter: dict = {}
        if status:
            filter["status"] = status.value
        return await self.count(filter)

    async def update_last_login(self, user_id: str | ObjectId) -> None:
        """Update last login timestamp."""
        await self.collection.update_one(
            {"_id": self._to_object_id(user_id)},
            {"$set": {"last_login_at": datetime.utcnow()}}
        )

    async def update_password(
        self,
        user_id: str | ObjectId,
        password_hash: str,
    ) -> None:
        """Update user password hash."""
        await self.update(user_id, {"password_hash": password_hash})

    async def update_status(
        self,
        user_id: str | ObjectId,
        status: UserStatus,
    ) -> User | None:
        """Update user status (active/suspended)."""
        return await self.update(user_id, {"status": status.value})

    async def update_subscription_info(
        self,
        user_id: str | ObjectId,
        subscription_status: str,
        subscription_end: datetime | None,
    ) -> User | None:
        """Update user subscription info."""
        return await self.update(user_id, {
            "subscription_status": subscription_status,
            "subscription_end": subscription_end,
        })

    async def username_exists(self, username: str, exclude_id: str | None = None) -> bool:
        """Check if username is already taken."""
        filter = {"username": {"$regex": f"^{username}$", "$options": "i"}}
        if exclude_id:
            filter["_id"] = {"$ne": ObjectId(exclude_id)}
        return await self.exists(filter)

    async def email_exists(self, email: str, exclude_id: str | None = None) -> bool:
        """Check if email is already taken."""
        filter = {"email": {"$regex": f"^{email}$", "$options": "i"}}
        if exclude_id:
            filter["_id"] = {"$ne": ObjectId(exclude_id)}
        return await self.exists(filter)
