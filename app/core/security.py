"""Security utilities for authentication and authorization."""
from datetime import datetime, timedelta
from typing import Any
import uuid

import bcrypt
import jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # user_id
    role: str  # UserRole
    type: str  # "access" or "refresh"
    exp: datetime
    iat: datetime
    jti: str  # unique token id for revocation


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    # Store as UTF-8 string for DB compatibility
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    # bcrypt expects the hash as bytes, so encode it back
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(user_id: str, role: str) -> tuple[str, str, datetime]:
    """
    Create short-lived access token.

    Returns:
        Tuple of (token, jti, expiry_datetime)
    """
    now = datetime.utcnow()
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expires,
        "iat": now,
        "jti": jti,
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires


def create_refresh_token(user_id: str, role: str) -> tuple[str, str, datetime]:
    """
    Create long-lived refresh token.

    Returns:
        Tuple of (token, jti, expiry_datetime)
    """
    now = datetime.utcnow()
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    jti = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "role": role,
        "type": "refresh",
        "exp": expires,
        "iat": now,
        "jti": jti,
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires


def create_token_pair(user_id: str, role: str) -> tuple[TokenPair, str, str, datetime]:
    """
    Create both access and refresh tokens.

    Returns:
        Tuple of (TokenPair, access_jti, refresh_jti, refresh_expires)
    """
    access_token, access_jti, _ = create_access_token(user_id, role)
    refresh_token, refresh_jti, refresh_expires = create_refresh_token(user_id, role)

    token_pair = TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )

    return token_pair, access_jti, refresh_jti, refresh_expires


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate JWT token.

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm]
    )

    return TokenPayload(
        sub=payload["sub"],
        role=payload["role"],
        type=payload["type"],
        exp=datetime.fromtimestamp(payload["exp"]),
        iat=datetime.fromtimestamp(payload["iat"]),
        jti=payload["jti"],
    )


def decode_token_unverified(token: str) -> dict[str, Any]:
    """Decode token without verification (for debugging/logging)."""
    return jwt.decode(
        token,
        options={"verify_signature": False}
    )
