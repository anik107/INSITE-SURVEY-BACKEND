"""Admin management endpoints."""
from fastapi import APIRouter, Query

from app.api.deps import SuperAdminUser, DatabaseDep, UserRepoDep
from app.models.domain import UserStatus
from app.models.schemas.admin import AdminResponse, AdminListResponse, AdminStatusUpdate
from app.services.admin_service import AdminService


router = APIRouter(prefix="/admins", tags=["Admin Management"])


def get_admin_service(db: DatabaseDep, user_repo: UserRepoDep) -> AdminService:
    """Get admin service instance."""
    return AdminService(
        user_repo=user_repo,
        attraction_collection=db["attractions"],
    )


@router.get("", response_model=AdminListResponse)
async def list_admins(
    current_user: SuperAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
    status: UserStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List all attraction admins.

    Requires Super Admin role.
    """
    service = get_admin_service(db, user_repo)
    admins, total = await service.list_admins(status, skip, limit)

    return AdminListResponse(
        items=[AdminResponse(**_format_admin(a)) for a in admins],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Get admin details by ID.

    Requires Super Admin role.
    """
    service = get_admin_service(db, user_repo)
    admin = await service.get_admin_with_attraction(admin_id)
    return AdminResponse(**_format_admin(admin))


@router.post("/{admin_id}/suspend", response_model=AdminStatusUpdate)
async def suspend_admin(
    admin_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Suspend an attraction admin.

    Suspended admins cannot log in or access any system features.

    Requires Super Admin role.
    """
    service = get_admin_service(db, user_repo)
    admin = await service.suspend_admin(admin_id)

    return AdminStatusUpdate(
        id=str(admin.id),
        status=admin.status,
        message="Admin suspended successfully",
    )


@router.post("/{admin_id}/unsuspend", response_model=AdminStatusUpdate)
async def unsuspend_admin(
    admin_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Unsuspend (reactivate) an attraction admin.

    Reactivates a suspended admin account.

    Requires Super Admin role.
    """
    service = get_admin_service(db, user_repo)
    admin = await service.unsuspend_admin(admin_id)

    return AdminStatusUpdate(
        id=str(admin.id),
        status=admin.status,
        message="Admin unsuspended successfully",
    )


def _format_admin(admin: dict) -> dict:
    """Format admin dict for response."""
    # Convert ObjectId fields to strings
    if "_id" in admin:
        admin["_id"] = str(admin["_id"])
    if "id" in admin:
        admin["id"] = str(admin["id"])
    if "attraction_id" in admin and admin["attraction_id"]:
        admin["attraction_id"] = str(admin["attraction_id"])
    return admin
