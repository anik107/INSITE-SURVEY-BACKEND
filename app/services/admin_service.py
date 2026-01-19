"""Admin service for managing attraction admins."""
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.exceptions import NotFoundError, ValidationError, BusinessRuleError
from app.models.domain import User, UserRole, UserStatus, Attraction
from app.repositories.user_repository import UserRepository


class AdminService:
    """Service for admin management operations."""

    def __init__(
        self,
        user_repo: UserRepository,
        attraction_collection=None,
    ):
        self.user_repo = user_repo
        self.attraction_collection = attraction_collection

    async def list_admins(
        self,
        status: UserStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List all admins (super and attraction) with their attraction info.

        Returns list of admins with attraction details.
        """
        admins = await self.user_repo.find_all_admins(status, skip, limit)
        total = await self.user_repo.count_all_admins(status)

        # Enrich with attraction info
        result = []
        for admin in admins:
            admin_dict = admin.model_dump()

            # Get attraction info if exists
            if admin.attraction_id and self.attraction_collection is not None:
                attraction = await self.attraction_collection.find_one(
                    {"_id": admin.attraction_id}
                )
                if attraction:
                    admin_dict["attraction"] = {
                        "id": str(attraction["_id"]),
                        "name": attraction.get("name"),
                        "subscription_status": attraction.get("subscription_status"),
                    }

            result.append(admin_dict)

        return result, total

    async def get_admin(self, admin_id: str) -> User:
        """Get admin by ID."""
        user = await self.user_repo.find_by_id(admin_id)
        if not user:
            raise NotFoundError("Admin", admin_id)

        if user.role != UserRole.ATTRACTION_ADMIN:
            raise NotFoundError("Admin", admin_id)

        return user

    async def suspend_admin(self, admin_id: str) -> User:
        """
        Suspend an attraction admin.

        Business Rules:
        - BR-ADM-001: Suspended admins cannot access the system
        - Cannot suspend super admins
        - Cannot suspend already suspended admins
        """
        user = await self.get_admin(admin_id)

        if user.status == UserStatus.SUSPENDED:
            raise ValidationError("Admin is already suspended")

        updated = await self.user_repo.update_status(admin_id, UserStatus.SUSPENDED)
        if not updated:
            raise NotFoundError("Admin", admin_id)

        return updated

    async def unsuspend_admin(self, admin_id: str) -> User:
        """
        Unsuspend (reactivate) an attraction admin.

        Business Rules:
        - Only suspended admins can be unsuspended
        """
        user = await self.get_admin(admin_id)

        if user.status == UserStatus.ACTIVE:
            raise ValidationError("Admin is already active")

        updated = await self.user_repo.update_status(admin_id, UserStatus.ACTIVE)
        if not updated:
            raise NotFoundError("Admin", admin_id)

        return updated

    async def get_admin_with_attraction(self, admin_id: str) -> dict[str, Any]:
        """Get admin details with attraction info."""
        user = await self.get_admin(admin_id)
        admin_dict = user.model_dump()

        if user.attraction_id and self.attraction_collection is not None:
            attraction = await self.attraction_collection.find_one(
                {"_id": user.attraction_id}
            )
            if attraction:
                admin_dict["attraction"] = {
                    "id": str(attraction["_id"]),
                    "name": attraction.get("name"),
                    "subscription_status": attraction.get("subscription_status"),
                    "subscription_plan": attraction.get("subscription_plan"),
                    "subscription_end": attraction.get("subscription_end"),
                }

        return admin_dict
