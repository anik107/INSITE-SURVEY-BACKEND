"""Section request repository for database operations."""
from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import SectionRequest, SectionRequestStatus
from app.repositories.base import BaseRepository


class SectionRequestRepository(BaseRepository[SectionRequest]):
    """Repository for SectionRequest collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "section_requests", SectionRequest)

    async def find_by_attraction(
        self,
        attraction_id: str | ObjectId,
        status: SectionRequestStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SectionRequest]:
        """Find section requests for an attraction."""
        filter = {"attraction_id": self._to_object_id(attraction_id)}
        if status:
            filter["status"] = status.value
        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def count_by_attraction(
        self,
        attraction_id: str | ObjectId,
        status: SectionRequestStatus | None = None,
    ) -> int:
        """Count section requests for an attraction."""
        filter = {"attraction_id": self._to_object_id(attraction_id)}
        if status:
            filter["status"] = status.value
        return await self.count(filter)

    async def find_all_requests(
        self,
        status: SectionRequestStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SectionRequest]:
        """Find all section requests (for super admin)."""
        filter = {}
        if status:
            filter["status"] = status.value
        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def count_all_requests(
        self,
        status: SectionRequestStatus | None = None,
    ) -> int:
        """Count all section requests."""
        filter = {}
        if status:
            filter["status"] = status.value
        return await self.count(filter)

    async def approve(
        self,
        request_id: str | ObjectId,
        reviewer_id: str | ObjectId,
    ) -> SectionRequest | None:
        """Approve a section request."""
        return await self.update(request_id, {
            "status": SectionRequestStatus.APPROVED.value,
            "reviewed_by": self._to_object_id(reviewer_id),
            "reviewed_at": datetime.utcnow(),
        })

    async def reject(
        self,
        request_id: str | ObjectId,
        reviewer_id: str | ObjectId,
    ) -> SectionRequest | None:
        """Reject a section request."""
        return await self.update(request_id, {
            "status": SectionRequestStatus.REJECTED.value,
            "reviewed_by": self._to_object_id(reviewer_id),
            "reviewed_at": datetime.utcnow(),
        })

    async def find_pending_count(self) -> int:
        """Count pending section requests."""
        return await self.count({"status": SectionRequestStatus.PENDING.value})
