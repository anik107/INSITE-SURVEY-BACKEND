"""Attraction management endpoints."""
from fastapi import APIRouter, Query

from app.api.deps import SuperAdminUser, DatabaseDep, UserRepoDep, AuthServiceDep
from app.repositories.attraction_repository import AttractionRepository
from app.models.domain import Attraction, SubscriptionStatus
from app.models.schemas.auth import CreateUserRequest
from app.core.exceptions import NotFoundError, ValidationError
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


router = APIRouter(prefix="/attractions", tags=["Attractions"])


class AttractionResponse(BaseModel):
    """Attraction response."""
    id: str
    name: str
    admin_id: str | None = None
    admin_name: str | None = None
    admin_email: str | None = None
    admin_status: str | None = None  # Admin account status (active/suspended)
    monthly_fee: float = 0.0
    yearly_fee: float = 199.0
    subscription_status: str
    subscription_plan: str | None = None
    subscription_start: datetime | None = None
    subscription_end: datetime | None = None
    auto_renew: bool = True
    created_at: datetime
    updated_at: datetime


class AttractionListResponse(BaseModel):
    """Attraction list response."""
    items: list[AttractionResponse]
    total: int


class AdminData(BaseModel):
    """Admin user data for attraction creation."""
    first_name: str
    last_name: str
    email: str
    password: str
    username: str | None = None


class AttractionCreate(BaseModel):
    """Create attraction request."""
    name: str
    description: str | None = None
    location: str | None = None
    admin: AdminData  # Admin user details


@router.get("", response_model=AttractionListResponse)
async def list_attractions(
    current_user: SuperAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List all attractions (Super Admin only).
    """
    attraction_repo = AttractionRepository(db)
    attractions = await attraction_repo.find_many(
        filter=None,
        skip=skip,
        limit=limit,
        sort=[("created_at", -1)],
    )
    total = await attraction_repo.count()

    # Enrich with admin info
    items = []
    for attraction in attractions:
        admin_name = None
        admin_email = None
        admin_status = None

        if attraction.admin_id:
            admin = await user_repo.find_by_id(str(attraction.admin_id))
            if admin:
                admin_name = admin.name
                admin_email = admin.email
                admin_status = admin.status.value if admin.status else None

        items.append(AttractionResponse(
            id=str(attraction.id),
            name=attraction.name,
            admin_id=str(attraction.admin_id) if attraction.admin_id else None,
            admin_name=admin_name,
            admin_email=admin_email,
            admin_status=admin_status,
            monthly_fee=attraction.monthly_fee,
            yearly_fee=attraction.yearly_fee,
            subscription_status=attraction.subscription_status.value,
            subscription_plan=attraction.subscription_plan.value if attraction.subscription_plan else None,
            subscription_start=attraction.subscription_start,
            subscription_end=attraction.subscription_end,
            auto_renew=attraction.auto_renew,
            created_at=attraction.created_at,
            updated_at=attraction.updated_at,
        ))

    return AttractionListResponse(items=items, total=total)


@router.get("/{attraction_id}", response_model=AttractionResponse)
async def get_attraction(
    attraction_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """Get attraction by ID (Super Admin only)."""
    attraction_repo = AttractionRepository(db)
    attraction = await attraction_repo.find_by_id(attraction_id)
    
    if not attraction:
        raise NotFoundError("Attraction", attraction_id)

    admin_name = None
    admin_email = None
    admin_status = None

    if attraction.admin_id:
        admin = await user_repo.find_by_id(str(attraction.admin_id))
        if admin:
            admin_name = admin.name
            admin_email = admin.email
            admin_status = admin.status.value if admin.status else None

    return AttractionResponse(
        id=str(attraction.id),
        name=attraction.name,
        admin_id=str(attraction.admin_id) if attraction.admin_id else None,
        admin_name=admin_name,
        admin_email=admin_email,
        admin_status=admin_status,
        monthly_fee=attraction.monthly_fee,
        yearly_fee=attraction.yearly_fee,
        subscription_status=attraction.subscription_status.value,
        subscription_plan=attraction.subscription_plan.value if attraction.subscription_plan else None,
        subscription_start=attraction.subscription_start,
        subscription_end=attraction.subscription_end,
        auto_renew=attraction.auto_renew,
        created_at=attraction.created_at,
        updated_at=attraction.updated_at,
    )


@router.post("", response_model=AttractionResponse, status_code=201)
async def create_attraction(
    data: AttractionCreate,
    current_user: SuperAdminUser,
    db: DatabaseDep,
    auth_service: AuthServiceDep,
):
    """
    Create a new attraction with admin user (Super Admin only).
    """
    # Validate admin data
    admin_data = data.admin

    # Create admin user using auth service
    user_request = CreateUserRequest(
        name=f"{admin_data.first_name} {admin_data.last_name}",
        email=admin_data.email,
        username=admin_data.username or admin_data.email.split("@")[0],
        password=admin_data.password,
        role="attraction_admin",
        attraction_name=data.name,
        monthly_fee=29.0,
        yearly_fee=199.0,
    )

    user_response = await auth_service.create_user(
        request=user_request,
        created_by=str(current_user.id),
    )

    # Get the created attraction (created by auth service)
    attraction_repo = AttractionRepository(db)
    attraction = await attraction_repo.find_by_admin(str(user_response.id))

    if not attraction:
        raise NotFoundError("Attraction", "created")

    return AttractionResponse(
        id=str(attraction.id),
        name=attraction.name,
        admin_id=str(attraction.admin_id) if attraction.admin_id else None,
        admin_name=user_response.name,
        admin_email=user_response.email,
        admin_status="active",  # Newly created admins are active
        monthly_fee=attraction.monthly_fee,
        yearly_fee=attraction.yearly_fee,
        subscription_status=attraction.subscription_status.value,
        subscription_plan=attraction.subscription_plan.value if attraction.subscription_plan else None,
        subscription_start=attraction.subscription_start,
        subscription_end=attraction.subscription_end,
        auto_renew=attraction.auto_renew,
        created_at=attraction.created_at,
        updated_at=attraction.updated_at,
    )


@router.put("/{attraction_id}", response_model=AttractionResponse)
async def update_attraction(
    attraction_id: str,
    data: dict,
    current_user: SuperAdminUser,
    db: DatabaseDep,
):
    """Update attraction (Super Admin only)."""
    attraction_repo = AttractionRepository(db)
    attraction = await attraction_repo.find_by_id(attraction_id)
    
    if not attraction:
        raise NotFoundError("Attraction", attraction_id)

    # Update attraction
    updates = {}
    if "name" in data:
        updates["name"] = data["name"]
    
    updated = await attraction_repo.update(attraction_id, updates)
    
    if not updated:
        raise NotFoundError("Attraction", attraction_id)

    return AttractionResponse(
        id=str(updated.id),
        name=updated.name,
        admin_id=str(updated.admin_id) if updated.admin_id else None,
        admin_name=None,  # Would need to fetch separately
        admin_email=None,  # Would need to fetch separately
        admin_status=None,  # Would need to fetch separately
        monthly_fee=updated.monthly_fee,
        yearly_fee=updated.yearly_fee,
        subscription_status=updated.subscription_status.value,
        subscription_plan=updated.subscription_plan.value if updated.subscription_plan else None,
        subscription_start=updated.subscription_start,
        subscription_end=updated.subscription_end,
        auto_renew=updated.auto_renew,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{attraction_id}", response_model=dict)
async def delete_attraction(
    attraction_id: str,
    current_user: SuperAdminUser,
    db: DatabaseDep,
):
    """Delete attraction (Super Admin only)."""
    attraction_repo = AttractionRepository(db)
    deleted = await attraction_repo.delete(attraction_id)
    
    if not deleted:
        raise NotFoundError("Attraction", attraction_id)

    return {"message": "Attraction deleted successfully"}

