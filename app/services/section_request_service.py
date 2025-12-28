"""Section request service for business logic."""
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.models.domain import SectionRequest, SectionRequestStatus, User, UserRole
from app.repositories.section_request_repository import SectionRequestRepository


class SectionRequestService:
    """Service for section request operations."""

    def __init__(
        self,
        request_repo: SectionRequestRepository,
        user_collection=None,
        attraction_collection=None,
    ):
        self.request_repo = request_repo
        self.user_collection = user_collection
        self.attraction_collection = attraction_collection

    async def submit_request(
        self,
        admin_id: str,
        attraction_id: str,
        section_name: str,
        description: str,
    ) -> SectionRequest:
        """
        Submit a new section request.

        Attraction admins can request new survey sections.
        """
        if not section_name or not section_name.strip():
            raise ValidationError("Section name is required")

        if not description or not description.strip():
            raise ValidationError("Description is required")

        request_data = {
            "attraction_id": ObjectId(attraction_id),
            "admin_id": ObjectId(admin_id),
            "section_name": section_name.strip(),
            "description": description.strip(),
            "status": SectionRequestStatus.PENDING.value,
        }

        return await self.request_repo.create(request_data)

    async def list_my_requests(
        self,
        attraction_id: str,
        status: SectionRequestStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SectionRequest], int]:
        """List section requests for the current attraction."""
        requests = await self.request_repo.find_by_attraction(
            attraction_id, status, skip, limit
        )
        total = await self.request_repo.count_by_attraction(attraction_id, status)
        return requests, total

    async def list_all_requests(
        self,
        status: SectionRequestStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List all section requests (for super admin).

        Returns enriched data with admin and attraction info.
        """
        requests = await self.request_repo.find_all_requests(status, skip, limit)
        total = await self.request_repo.count_all_requests(status)

        # Enrich with admin and attraction info
        result = []
        for req in requests:
            req_dict = req.model_dump()

            # Get admin info
            if self.user_collection:
                admin = await self.user_collection.find_one({"_id": req.admin_id})
                if admin:
                    req_dict["admin"] = {
                        "id": str(admin["_id"]),
                        "name": admin.get("name"),
                        "email": admin.get("email"),
                    }

            # Get attraction info
            if self.attraction_collection:
                attraction = await self.attraction_collection.find_one(
                    {"_id": req.attraction_id}
                )
                if attraction:
                    req_dict["attraction"] = {
                        "id": str(attraction["_id"]),
                        "name": attraction.get("name"),
                    }

            result.append(req_dict)

        return result, total

    async def get_request(
        self,
        request_id: str,
        user: User,
    ) -> SectionRequest:
        """Get section request by ID with permission check."""
        request = await self.request_repo.find_by_id(request_id)
        if not request:
            raise NotFoundError("Section Request", request_id)

        # Super admins can view any request
        if user.role == UserRole.SUPER_ADMIN:
            return request

        # Attraction admins can only view their own requests
        if str(request.attraction_id) != str(user.attraction_id):
            raise ForbiddenError("You can only view your own section requests")

        return request

    async def approve_request(
        self,
        request_id: str,
        reviewer_id: str,
    ) -> SectionRequest:
        """
        Approve a section request.

        Only super admins can approve.
        """
        request = await self.request_repo.find_by_id(request_id)
        if not request:
            raise NotFoundError("Section Request", request_id)

        if request.status != SectionRequestStatus.PENDING:
            raise ValidationError(
                f"Cannot approve request with status '{request.status.value}'"
            )

        updated = await self.request_repo.approve(request_id, reviewer_id)
        if not updated:
            raise NotFoundError("Section Request", request_id)

        return updated

    async def reject_request(
        self,
        request_id: str,
        reviewer_id: str,
    ) -> SectionRequest:
        """
        Reject a section request.

        Only super admins can reject.
        """
        request = await self.request_repo.find_by_id(request_id)
        if not request:
            raise NotFoundError("Section Request", request_id)

        if request.status != SectionRequestStatus.PENDING:
            raise ValidationError(
                f"Cannot reject request with status '{request.status.value}'"
            )

        updated = await self.request_repo.reject(request_id, reviewer_id)
        if not updated:
            raise NotFoundError("Section Request", request_id)

        return updated

    async def get_pending_count(self) -> int:
        """Get count of pending section requests."""
        return await self.request_repo.find_pending_count()
