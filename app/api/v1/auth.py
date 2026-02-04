"""Authentication API endpoints."""
import logging
from fastapi import APIRouter, Request, Depends, BackgroundTasks
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
    ResetPasswordRequest,
    RequestPasswordResetRequest,
    ResetPasswordWithTokenRequest,
)
from app.models.schemas.common import MessageResponse
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)

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


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """
    Reset password using username (no email required).

    **DEPRECATED**: Use /request-reset and /reset-password-with-token for secure email-based reset.

    - **username**: User's username
    - **new_password**: New password (min 8 characters)
    """
    await auth_service.reset_password_by_username(data.username, data.new_password)
    return MessageResponse(message="Password reset successfully")


@router.post("/request-reset", response_model=MessageResponse)
async def request_password_reset(
    data: RequestPasswordResetRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """
    Request password reset by email. Sends a reset link to the user's email.

    - **email**: User's email address

    Returns success even if email doesn't exist (security best practice).
    """
    await auth_service.request_password_reset(data.email)
    return MessageResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )


@router.post("/reset-password-with-token", response_model=MessageResponse)
async def reset_password_with_token(
    data: ResetPasswordWithTokenRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """
    Reset password using token from email link.

    - **token**: Reset token from email
    - **new_password**: New password (min 8 characters)
    """
    await auth_service.reset_password_with_token(data.token, data.new_password)
    return MessageResponse(message="Password reset successfully. You can now log in with your new password.")


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    data: CreateUserRequest,
    current_user: SuperAdminUser,
    auth_service: AuthServiceDep,
    background_tasks: BackgroundTasks,
) -> CreateUserResponse:
    """
    Create a new user (Super Admin only).

    - For **attraction_admin** role, provide **attraction_name**
    - Sets up attraction with specified subscription fees
    - Sends login credentials to the user's email
    """
    # Store plain password before it gets hashed
    plain_password = data.password

    user_response = await auth_service.create_user(
        request=data,
        created_by=str(current_user.id),
    )

    # Send credentials email in background for attraction admins
    if data.role == "attraction_admin" and data.attraction_name:
        email_service = get_email_service()
        background_tasks.add_task(
            email_service.send_admin_credentials,
            to_email=data.email,
            admin_name=data.name,
            username=data.username,
            password=plain_password,
            attraction_name=data.attraction_name,
        )
        logger.info(f"Credentials email queued for {data.email}")

    return user_response


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
