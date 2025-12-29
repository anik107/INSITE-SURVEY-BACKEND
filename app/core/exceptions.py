"""Custom application exceptions."""
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception with error code support."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code

    @property
    def message(self):
        return self.detail

    @property
    def details(self):
        # For compatibility with main.py, return detail (or customize as needed)
        return self.detail


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | None = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with ID '{identifier}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
        )


class UnauthorizedError(AppException):
    """Authentication required or failed."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsError(UnauthorizedError):
    """Invalid username or password."""

    def __init__(self):
        super().__init__(detail="Invalid username or password")
        self.error_code = "INVALID_CREDENTIALS"


class InvalidTokenError(UnauthorizedError):
    """Invalid or expired token."""

    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(detail=detail)
        self.error_code = "INVALID_TOKEN"


class ForbiddenError(AppException):
    """Insufficient permissions."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN",
        )


class AccountSuspendedError(ForbiddenError):
    """User account is suspended."""

    def __init__(self):
        super().__init__(detail="Account is suspended")
        self.error_code = "ACCOUNT_SUSPENDED"


class ConflictError(AppException):
    """Resource conflict (duplicate, state violation)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
        )


class DuplicateError(ConflictError):
    """Duplicate resource error."""

    def __init__(self, resource: str, field: str):
        super().__init__(detail=f"{resource} with this {field} already exists")
        self.error_code = "DUPLICATE"


class ValidationError(AppException):
    """Business validation error."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class BusinessRuleError(ValidationError):
    """Business rule violation."""

    def __init__(self, rule_id: str, detail: str):
        super().__init__(detail=f"[{rule_id}] {detail}")
        self.error_code = "BUSINESS_RULE_VIOLATION"
        self.rule_id = rule_id


class SubscriptionRequiredError(AppException):
    """Active subscription required."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required for this action",
            error_code="SUBSCRIPTION_REQUIRED",
        )


class SubscriptionExpiredError(SubscriptionRequiredError):
    """Subscription has expired."""

    def __init__(self):
        super().__init__()
        self.detail = "Subscription has expired"
        self.error_code = "SUBSCRIPTION_EXPIRED"


class DuplicateResponseError(AppException):
    """Duplicate survey response detected."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A response was already submitted recently",
            error_code="DUPLICATE_RESPONSE",
        )


class SurveyNotPublishedError(AppException):
    """Survey is not published and cannot accept responses."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This survey is not currently accepting responses",
            error_code="SURVEY_NOT_PUBLISHED",
        )


class TemplateNotPublishedError(AppException):
    """No published template available."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published template available",
            error_code="TEMPLATE_NOT_PUBLISHED",
        )
