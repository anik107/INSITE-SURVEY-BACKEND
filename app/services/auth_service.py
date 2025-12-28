"""Authentication service for login, logout, and token management."""
from datetime import datetime

from bson import ObjectId

from app.core.security import (
    hash_password,
    verify_password,
    create_token_pair,
    decode_token,
    TokenPair,
)
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    AccountSuspendedError,
    NotFoundError,
    DuplicateError,
    ValidationError,
)
from app.models.domain import User, UserRole, UserStatus, Session, Attraction, SubscriptionStatus
from app.models.schemas.auth import (
    LoginRequest,
    TokenResponse,
    CreateUserRequest,
    CreateUserResponse,
    UserProfileResponse,
    ChangePasswordRequest,
)
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository


class AuthService:
    """Service for authentication operations."""

    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        attraction_collection=None,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.attraction_collection = attraction_collection

    async def login(
        self,
        request: LoginRequest,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """
        Authenticate user and return tokens.

        Args:
            request: Login credentials
            user_agent: Client user agent
            ip_address: Client IP address

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountSuspendedError: If account is suspended
        """
        # Find user by username
        user = await self.user_repo.find_by_username(request.username)
        if not user:
            raise InvalidCredentialsError()

        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise InvalidCredentialsError()

        # Check account status
        if user.status == UserStatus.SUSPENDED:
            raise AccountSuspendedError()

        # Create tokens
        token_pair, access_jti, refresh_jti, refresh_expires = create_token_pair(
            str(user.id), user.role.value
        )

        # Store refresh token session
        await self.session_repo.create({
            "user_id": user.id,
            "token_jti": refresh_jti,
            "expires_at": refresh_expires,
            "revoked": False,
            "user_agent": user_agent,
            "ip_address": ip_address,
        })

        # Update last login
        await self.user_repo.update_last_login(user.id)

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token
            user_agent: Client user agent
            ip_address: Client IP address

        Returns:
            New TokenResponse

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise InvalidTokenError("Invalid refresh token")

        # Verify it's a refresh token
        if payload.type != "refresh":
            raise InvalidTokenError("Invalid token type")

        # Check if session is valid
        session = await self.session_repo.find_by_jti(payload.jti)
        if not session:
            raise InvalidTokenError("Token has been revoked or expired")

        # Get user
        user = await self.user_repo.find_by_id(payload.sub)
        if not user:
            raise InvalidTokenError("User not found")

        if user.status == UserStatus.SUSPENDED:
            # Revoke all sessions for suspended user
            await self.session_repo.revoke_all_for_user(user.id)
            raise AccountSuspendedError()

        # Revoke old session
        await self.session_repo.revoke(payload.jti)

        # Create new tokens
        token_pair, access_jti, refresh_jti, refresh_expires = create_token_pair(
            str(user.id), user.role.value
        )

        # Store new refresh token session
        await self.session_repo.create({
            "user_id": user.id,
            "token_jti": refresh_jti,
            "expires_at": refresh_expires,
            "revoked": False,
            "user_agent": user_agent,
            "ip_address": ip_address,
        })

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )

    async def logout(self, user_id: str, token_jti: str | None = None) -> None:
        """
        Logout user by revoking session(s).

        Args:
            user_id: User ID
            token_jti: Specific token JTI to revoke (revokes all if None)
        """
        if token_jti:
            await self.session_repo.revoke(token_jti)
        else:
            await self.session_repo.revoke_all_for_user(user_id)

    async def logout_all(self, user_id: str) -> int:
        """Logout user from all sessions."""
        return await self.session_repo.revoke_all_for_user(user_id)

    async def change_password(
        self,
        user_id: str,
        request: ChangePasswordRequest,
    ) -> None:
        """
        Change user password.

        Args:
            user_id: User ID
            request: Current and new password

        Raises:
            InvalidCredentialsError: If current password is wrong
            NotFoundError: If user not found
        """
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        # Verify current password
        if not verify_password(request.current_password, user.password_hash):
            raise InvalidCredentialsError()

        # Update password
        new_hash = hash_password(request.new_password)
        await self.user_repo.update_password(user_id, new_hash)

        # Revoke all sessions to force re-login
        await self.session_repo.revoke_all_for_user(user_id)

    async def get_user_profile(self, user_id: str) -> UserProfileResponse:
        """Get user profile with attraction info."""
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        attraction_name = None
        if user.attraction_id and self.attraction_collection:
            attraction = await self.attraction_collection.find_one(
                {"_id": user.attraction_id}
            )
            if attraction:
                attraction_name = attraction.get("name")

        return UserProfileResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            username=user.username,
            role=user.role,
            status=user.status,
            attraction_id=str(user.attraction_id) if user.attraction_id else None,
            attraction_name=attraction_name,
            subscription_status=user.subscription_status,
            subscription_end=user.subscription_end,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )

    async def create_user(
        self,
        request: CreateUserRequest,
        created_by: str | None = None,
    ) -> CreateUserResponse:
        """
        Create new user (Super Admin only).

        Args:
            request: User creation data
            created_by: ID of admin creating the user

        Returns:
            Created user response

        Raises:
            DuplicateError: If username or email already exists
            ValidationError: If attraction_admin without attraction_name
        """
        # Check for duplicates
        if await self.user_repo.username_exists(request.username):
            raise DuplicateError("User", "username")
        if await self.user_repo.email_exists(request.email):
            raise DuplicateError("User", "email")

        # Validate attraction admin requires attraction name
        attraction_id = None
        if request.role == UserRole.ATTRACTION_ADMIN:
            if not request.attraction_name:
                raise ValidationError("attraction_name is required for attraction_admin role")

            # Create attraction
            if self.attraction_collection:
                attraction_doc = {
                    "_id": ObjectId(),
                    "name": request.attraction_name,
                    "monthly_fee": request.monthly_fee,
                    "yearly_fee": request.yearly_fee,
                    "subscription_status": SubscriptionStatus.NOT_SUBSCRIBED.value,
                    "auto_renew": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
                await self.attraction_collection.insert_one(attraction_doc)
                attraction_id = attraction_doc["_id"]

        # Hash password
        password_hash = hash_password(request.password)

        # Create user
        user_data = {
            "role": request.role.value,
            "status": UserStatus.ACTIVE.value,
            "name": request.name,
            "email": request.email,
            "username": request.username,
            "password_hash": password_hash,
            "attraction_id": attraction_id,
        }

        if request.role == UserRole.ATTRACTION_ADMIN:
            user_data["subscription_status"] = SubscriptionStatus.NOT_SUBSCRIBED.value

        user = await self.user_repo.create(user_data)

        # Update attraction with admin_id
        if attraction_id and self.attraction_collection:
            await self.attraction_collection.update_one(
                {"_id": attraction_id},
                {"$set": {"admin_id": user.id}}
            )

        return CreateUserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            username=user.username,
            role=user.role,
            status=user.status,
            attraction_id=str(attraction_id) if attraction_id else None,
            created_at=user.created_at,
        )

    async def validate_token(self, token: str) -> User:
        """
        Validate access token and return user.

        Args:
            token: JWT access token

        Returns:
            User if valid

        Raises:
            InvalidTokenError: If token is invalid
            AccountSuspendedError: If user is suspended
        """
        try:
            payload = decode_token(token)
        except Exception:
            raise InvalidTokenError()

        if payload.type != "access":
            raise InvalidTokenError("Invalid token type")

        user = await self.user_repo.find_by_id(payload.sub)
        if not user:
            raise InvalidTokenError("User not found")

        if user.status == UserStatus.SUSPENDED:
            raise AccountSuspendedError()

        return user
