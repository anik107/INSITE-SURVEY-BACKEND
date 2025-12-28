"""Section request schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import SectionRequestStatus


class SectionRequestCreate(BaseModel):
    """Request body for creating a section request."""
    section_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)


class AdminInfo(BaseModel):
    """Admin info embedded in request response."""
    id: str
    name: str | None = None
    email: str | None = None


class AttractionInfo(BaseModel):
    """Attraction info embedded in request response."""
    id: str
    name: str | None = None


class SectionRequestResponse(BaseModel):
    """Response for section request details."""
    id: str = Field(alias="_id")
    attraction_id: str
    admin_id: str
    section_name: str
    description: str
    status: SectionRequestStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    admin: AdminInfo | None = None
    attraction: AttractionInfo | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class SectionRequestListResponse(BaseModel):
    """Response for section request list."""
    items: list[SectionRequestResponse]
    total: int
    skip: int
    limit: int


class SectionRequestStatusUpdate(BaseModel):
    """Response after status update."""
    id: str
    status: SectionRequestStatus
    message: str
