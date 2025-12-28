"""Common schemas shared across modules."""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
        )


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
    error_code: str | None = None


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    detail: list[ValidationErrorDetail]
