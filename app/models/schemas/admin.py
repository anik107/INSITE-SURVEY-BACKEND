"""Admin management schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import UserStatus


class AttractionInfo(BaseModel):
    """Attraction info embedded in admin response."""
    id: str
    name: str | None = None
    subscription_status: str | None = None


class AdminResponse(BaseModel):
    """Response for admin details."""
    id: str = Field(alias="_id")
    name: str
    email: str
    username: str
    status: UserStatus
    attraction_id: str | None = None
    subscription_status: str | None = None
    subscription_end: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    attraction: AttractionInfo | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class AdminListResponse(BaseModel):
    """Response for admin list."""
    items: list[AdminResponse]
    total: int
    skip: int
    limit: int


class AdminStatusUpdate(BaseModel):
    """Response after status update."""
    id: str
    status: UserStatus
    message: str
