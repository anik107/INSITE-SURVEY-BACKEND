"""Authentication schemas for request/response."""
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr

from app.models.domain import UserRole, UserStatus, SubscriptionStatus


class LoginRequest(BaseModel):
    """Login request payload."""
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenUserInfo(BaseModel):
    """User info included in token response."""
    id: str
    name: str
    email: str
    username: str
    role: str


class TokenResponse(BaseModel):
    """Token response after successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")
    user: TokenUserInfo


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request payload."""
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordRequest(BaseModel):
    """Reset password request payload (minimal - no email)."""
    username: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class UserProfileResponse(BaseModel):
    """User profile response."""
    id: str
    name: str
    email: str
    username: str
    role: UserRole
    status: UserStatus
    attraction_id: str | None = None
    attraction_name: str | None = None
    subscription_status: SubscriptionStatus | None = None
    subscription_end: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class UserProfileUpdate(BaseModel):
    """User profile update request."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None


class CreateUserRequest(BaseModel):
    """Create user request (Super Admin only)."""
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    attraction_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Required for attraction_admin role"
    )
    monthly_fee: float = Field(default=29.0, ge=0)
    yearly_fee: float = Field(default=199.0, ge=0)


class CreateUserResponse(BaseModel):
    """Create user response."""
    id: str
    name: str
    email: str
    username: str
    role: UserRole
    status: UserStatus
    attraction_id: str | None = None
    created_at: datetime


class UserListItem(BaseModel):
    """User list item for admin views."""
    id: str
    name: str
    email: str
    username: str
    role: UserRole
    status: UserStatus
    attraction_id: str | None = None
    attraction_name: str | None = None
    subscription_status: SubscriptionStatus | None = None
    last_login_at: datetime | None = None
    created_at: datetime
