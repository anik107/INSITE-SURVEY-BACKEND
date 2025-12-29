"""Authentication API endpoints."""
from fastapi import APIRouter, Request, Depends
from typing import Annotated

from app.api.deps import (
    AuthServiceDep,
    CurrentActiveUser,
    SuperAdminUser,
    UserRepoDep,
    get_client_ip,
    get_user_agent,
)
from app.models.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UserProfileResponse,
    CreateUserRequest,
    CreateUserResponse,
)
from app.models.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Authenticate user and return access/refresh tokens.

    - **username**: User's username
    - **password**: User's password
    """
    return await auth_service.login(
        request=data,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    data: RefreshTokenRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    return await auth_service.refresh_tokens(
        refresh_token=data.refresh_token,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: CurrentActiveUser,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """Logout current user (revoke all sessions)."""
    await auth_service.logout_all(str(current_user.id))
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: CurrentActiveUser,
    auth_service: AuthServiceDep,
) -> UserProfileResponse:
    """Get current user profile."""
    return await auth_service.get_user_profile(str(current_user.id))


@router.put("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentActiveUser,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """
    Change current user's password.

    - **current_password**: Current password
    - **new_password**: New password (min 8 characters)
    """
    await auth_service.change_password(str(current_user.id), data)
    return MessageResponse(message="Password changed successfully")


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    data: CreateUserRequest,
    current_user: SuperAdminUser,
    auth_service: AuthServiceDep,
) -> CreateUserResponse:
    """
    Create a new user (Super Admin only).

    - For **attraction_admin** role, provide **attraction_name**
    - Sets up attraction with specified subscription fees
    """
    return await auth_service.create_user(
        request=data,
        created_by=str(current_user.id),
    )


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: str,
    current_user: SuperAdminUser,
    auth_service: AuthServiceDep,
) -> UserProfileResponse:
    """Get user by ID (Super Admin only)."""
    return await auth_service.get_user_profile(user_id)


@router.put("/users/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: str,
    data: dict,
    current_user: SuperAdminUser,
    user_repo: UserRepoDep,
    auth_service: AuthServiceDep,
) -> UserProfileResponse:
    """Update user (Super Admin only)."""
    from app.core.exceptions import NotFoundError
    
    updated = await user_repo.update(user_id, data)
    
    if not updated:
        raise NotFoundError("User", user_id)
    
    return await auth_service.get_user_profile(user_id)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    current_user: SuperAdminUser,
    user_repo: UserRepoDep,
) -> MessageResponse:
    """Delete user (Super Admin only)."""
    from app.core.exceptions import NotFoundError, ValidationError
    from app.models.domain import UserRole
    
    # Check if user exists
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    
    # Prevent deletion of super admins
    if user.role == UserRole.SUPER_ADMIN:
        raise ValidationError("Super admins cannot be deleted")
    
    # Delete user
    deleted = await user_repo.delete(user_id)
    if not deleted:
        raise NotFoundError("User", user_id)
    
    return MessageResponse(message="User deleted successfully")
