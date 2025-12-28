"""Section request endpoints."""
from fastapi import APIRouter, Query

from app.api.deps import (
    SuperAdminUser,
    AttractionAdminUser,
    CurrentActiveUser,
    DatabaseDep,
)
from app.models.domain import SectionRequestStatus, UserRole
from app.models.schemas.section_request import (
    SectionRequestCreate,
    SectionRequestResponse,
    SectionRequestListResponse,
    SectionRequestStatusUpdate,
)
from app.repositories.section_request_repository import SectionRequestRepository
from app.services.section_request_service import SectionRequestService


router = APIRouter(prefix="/section-requests", tags=["Section Requests"])


def get_section_request_service(db: DatabaseDep) -> SectionRequestService:
    """Get section request service instance."""
    request_repo = SectionRequestRepository(db)
    return SectionRequestService(
        request_repo=request_repo,
        user_collection=db["users"],
        attraction_collection=db["attractions"],
    )


@router.post("", response_model=SectionRequestResponse, status_code=201)
async def submit_request(
    body: SectionRequestCreate,
    current_user: AttractionAdminUser,
    db: DatabaseDep,
):
    """
    Submit a new section request.

    Attraction admins can request new survey sections to be added.

    Requires Attraction Admin role.
    """
    service = get_section_request_service(db)
    request = await service.submit_request(
        admin_id=str(current_user.id),
        attraction_id=str(current_user.attraction_id),
        section_name=body.section_name,
        description=body.description,
    )

    return SectionRequestResponse(**_format_request(request.model_dump()))


@router.get("/my", response_model=SectionRequestListResponse)
async def list_my_requests(
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    status: SectionRequestStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List my section requests.

    Shows all section requests submitted by the current attraction.

    Requires Attraction Admin role.
    """
    service = get_section_request_service(db)
    requests, total = await service.list_my_requests(
        attraction_id=str(current_user.attraction_id),
        status=status,
        skip=skip,
        limit=limit,
    )

    return SectionRequestListResponse(
        items=[SectionRequestResponse(**_format_request(r.model_dump())) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("", response_model=SectionRequestListResponse)
async def list_all_requests(
    current_user: SuperAdminUser,
    db: DatabaseDep,
    status: SectionRequestStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List all section requests.

    Shows all section requests from all attractions.

    Requires Super Admin role.
    """
    service = get_section_request_service(db)
    requests, total = await service.list_all_requests(
        status=status,
        skip=skip,
        limit=limit,
    )

    return SectionRequestListResponse(
        items=[SectionRequestResponse(**_format_request(r)) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/pending/count")
async def get_pending_count(
    current_user: SuperAdminUser,
    db: DatabaseDep,
):
    """
    Get count of pending section requests.

    Requires Super Admin role.
    """
    service = get_section_request_service(db)
    count = await service.get_pending_count()
    return {"pending_count": count}


@router.get("/{request_id}", response_model=SectionRequestResponse)
async def get_request(
    request_id: str,
    current_user: CurrentActiveUser,
    db: DatabaseDep,
):
    """
    Get section request details.

    Super admins can view any request.
    Attraction admins can only view their own requests.
    """
    service = get_section_request_service(db)
    request = await service.get_request(request_id, current_user)
    return SectionRequestResponse(**_format_request(request.model_dump()))


@router.post("/{request_id}/approve", response_model=SectionRequestStatusUpdate)
async def approve_request(
    request_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
):
    """
    Approve a section request.

    Requires Super Admin role.
    """
    service = get_section_request_service(db)
    request = await service.approve_request(
        request_id=request_id,
        reviewer_id=str(current_user.id),
    )

    return SectionRequestStatusUpdate(
        id=str(request.id),
        status=request.status,
        message="Section request approved successfully",
    )


@router.post("/{request_id}/reject", response_model=SectionRequestStatusUpdate)
async def reject_request(
    request_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
):
    """
    Reject a section request.

    Requires Super Admin role.
    """
    service = get_section_request_service(db)
    request = await service.reject_request(
        request_id=request_id,
        reviewer_id=str(current_user.id),
    )

    return SectionRequestStatusUpdate(
        id=str(request.id),
        status=request.status,
        message="Section request rejected",
    )


def _format_request(req: dict) -> dict:
    """Format request dict for response."""
    # Convert ObjectId fields to strings
    if "_id" in req:
        req["_id"] = str(req["_id"])
    if "id" in req:
        req["id"] = str(req["id"])
    if "attraction_id" in req:
        req["attraction_id"] = str(req["attraction_id"])
    if "admin_id" in req:
        req["admin_id"] = str(req["admin_id"])
    if "reviewed_by" in req and req["reviewed_by"]:
        req["reviewed_by"] = str(req["reviewed_by"])
    return req
