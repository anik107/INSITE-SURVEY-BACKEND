"""Shared dependencies for API endpoints."""
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_database
from app.core.security import decode_token
from app.core.exceptions import (
    UnauthorizedError,
    InvalidTokenError,
    ForbiddenError,
    AccountSuspendedError,
    SubscriptionRequiredError,
)
from app.models.domain import User, UserRole, UserStatus, SubscriptionStatus
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.template_repository import TemplateRepository
from app.repositories.survey_repository import SurveyRepository
from app.repositories.response_repository import ResponseRepository
from app.services.auth_service import AuthService
from app.services.template_service import TemplateService
from app.services.survey_service import SurveyService
from app.services.response_service import ResponseService


# Security scheme
security = HTTPBearer(auto_error=False)


# Database dependency
DatabaseDep = Annotated[AsyncIOMotorDatabase, Depends(get_database)]


# Repository dependencies
def get_user_repository(db: DatabaseDep) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(db)


def get_session_repository(db: DatabaseDep) -> SessionRepository:
    """Get session repository instance."""
    return SessionRepository(db)


def get_template_repository(db: DatabaseDep) -> TemplateRepository:
    """Get template repository instance."""
    return TemplateRepository(db)


def get_survey_repository(db: DatabaseDep) -> SurveyRepository:
    """Get survey repository instance."""
    return SurveyRepository(db)


def get_response_repository(db: DatabaseDep) -> ResponseRepository:
    """Get response repository instance."""
    return ResponseRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]
TemplateRepoDep = Annotated[TemplateRepository, Depends(get_template_repository)]
SurveyRepoDep = Annotated[SurveyRepository, Depends(get_survey_repository)]
ResponseRepoDep = Annotated[ResponseRepository, Depends(get_response_repository)]


# Service dependencies
def get_auth_service(
    db: DatabaseDep,
    user_repo: UserRepoDep,
    session_repo: SessionRepoDep,
) -> AuthService:
    """Get auth service instance."""
    return AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        attraction_collection=db["attractions"],
    )


def get_template_service(
    template_repo: TemplateRepoDep,
) -> TemplateService:
    """Get template service instance."""
    return TemplateService(template_repo)


def get_survey_service(
    db: DatabaseDep,
    survey_repo: SurveyRepoDep,
    template_repo: TemplateRepoDep,
) -> SurveyService:
    """Get survey service instance."""
    return SurveyService(
        survey_repo=survey_repo,
        template_repo=template_repo,
        attraction_collection=db["attractions"],
    )


def get_response_service(
    response_repo: ResponseRepoDep,
    survey_repo: SurveyRepoDep,
    template_repo: TemplateRepoDep,
) -> ResponseService:
    """Get response service instance."""
    return ResponseService(
        response_repo=response_repo,
        survey_repo=survey_repo,
        template_repo=template_repo,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]
ResponseServiceDep = Annotated[ResponseService, Depends(get_response_service)]


# Authentication dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    user_repo: UserRepoDep = None,
) -> User:
    """
    Extract and validate user from JWT token.

    Raises:
        UnauthorizedError: If no token provided
        InvalidTokenError: If token is invalid
    """
    if not credentials:
        raise UnauthorizedError("Authorization header required")

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise InvalidTokenError()

    if payload.type != "access":
        raise InvalidTokenError("Invalid token type")

    user = await user_repo.find_by_id(payload.sub)
    if not user:
        raise InvalidTokenError("User not found")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensure user is active (not suspended).

    Raises:
        AccountSuspendedError: If user is suspended
    """
    if current_user.status == UserStatus.SUSPENDED:
        raise AccountSuspendedError()
    return current_user


async def require_super_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Require Super Admin role.

    Raises:
        ForbiddenError: If user is not super admin
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError("Super Admin access required")
    return current_user


async def require_attraction_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Require Attraction Admin role.

    Raises:
        ForbiddenError: If user is not attraction admin
    """
    if current_user.role != UserRole.ATTRACTION_ADMIN:
        raise ForbiddenError("Attraction Admin access required")
    return current_user


async def require_any_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require any admin role (super or attraction)."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ATTRACTION_ADMIN]:
        raise ForbiddenError("Admin access required")
    return current_user


async def require_active_subscription(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Require active subscription for attraction admins.

    Raises:
        SubscriptionRequiredError: If subscription is not active
    """
    # Super admins don't need subscription
    if current_user.role == UserRole.SUPER_ADMIN:
        return current_user

    # Check subscription status
    if current_user.subscription_status != SubscriptionStatus.ACTIVE:
        raise SubscriptionRequiredError()

    return current_user


# Type aliases for route dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
AttractionAdminUser = Annotated[User, Depends(require_attraction_admin)]
AnyAdminUser = Annotated[User, Depends(require_any_admin)]
SubscribedUser = Annotated[User, Depends(require_active_subscription)]


# Request helpers
def get_client_ip(request: Request) -> str | None:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    """Get user agent from request."""
    return request.headers.get("User-Agent")
