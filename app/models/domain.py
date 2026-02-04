"""Domain models representing MongoDB collections."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import DocumentModel, PyObjectId


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ATTRACTION_ADMIN = "attraction_admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SurveyStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SectionRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubscriptionStatus(str, Enum):
    NOT_SUBSCRIBED = "not_subscribed"
    ACTIVE = "active"
    EXPIRED = "expired"


class SubscriptionPlan(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class QuestionTag(str, Enum):
    SPACES_PLACES = "spaces_places"
    EMPATHY_EMOTION = "empathy_emotion"
    STORYTELLING = "storytelling"


class QuestionType(str, Enum):
    YES_NO = "yes_no"
    NUMERIC = "numeric"
    DROPDOWN = "dropdown"


class YesNoConfig(BaseModel):
    yes_weight: float = 1.0
    no_weight: float = 0.0


class NumericConfig(BaseModel):
    min_value: int = 0
    max_value: int = 5
    step: int = 1


class DropdownOption(BaseModel):
    value: str
    label: str
    weight: float


class DropdownConfig(BaseModel):
    options: list[DropdownOption]


class Question(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    text: str
    type: QuestionType
    tag: QuestionTag
    allow_na: bool = False
    config: YesNoConfig | NumericConfig | DropdownConfig | None = None


class Section(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str
    weight: int = Field(ge=1, le=100)
    allow_notes: bool = False
    questions: list[Question] = Field(default_factory=list)


class Template(DocumentModel):
    title: str
    status: TemplateStatus = TemplateStatus.DRAFT
    sections: list[Section] = Field(default_factory=list)
    published_at: datetime | None = None
    created_by: PyObjectId | None = None


class SurveySection(BaseModel):
    section_id: PyObjectId
    allow_notes: bool = False
    question_count: int


class Survey(DocumentModel):
    template_id: PyObjectId
    attraction_id: PyObjectId
    name: str
    status: SurveyStatus = SurveyStatus.DRAFT
    sections: list[SurveySection]
    share_id: str = Field(description="Unique slug used in public survey URLs")
    qr_code_url: str | None = None
    published_at: datetime | None = None
    archived_at: datetime | None = None


class QuestionResponse(BaseModel):
    question_id: PyObjectId
    type: QuestionType
    value: Any = None
    score: float | None = None
    tag: QuestionTag


class SectionResponse(BaseModel):
    section_id: PyObjectId
    note: str | None = None
    images: list[str] | None = None  # Base64 encoded images
    questions: list[QuestionResponse]


class SurveyResponse(DocumentModel):
    survey_id: PyObjectId
    attraction_id: PyObjectId
    template_id: PyObjectId
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    sections: list[SectionResponse]
    tag_scores: dict[QuestionTag, float] = Field(default_factory=dict)
    section_scores: dict[str, float] = Field(default_factory=dict)
    weather_snapshot: dict[str, Any] | None = None
    duplicate_fingerprint: str | None = None


class Attraction(DocumentModel):
    name: str
    admin_id: PyObjectId | None = None
    monthly_fee: float = 0.0
    yearly_fee: float = 199.0
    subscription_status: SubscriptionStatus = SubscriptionStatus.NOT_SUBSCRIBED
    subscription_plan: SubscriptionPlan | None = None
    subscription_start: datetime | None = None
    subscription_end: datetime | None = None
    auto_renew: bool = True
    last_payment_date: datetime | None = None
    card_last4: str | None = None
    card_brand: str | None = None


class User(DocumentModel):
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    name: str
    email: str
    username: str
    password_hash: str
    attraction_id: PyObjectId | None = None
    subscription_status: SubscriptionStatus | None = None
    subscription_end: datetime | None = None
    last_login_at: datetime | None = None


class PasswordResetToken(DocumentModel):
    """Password reset token for email-based password reset."""
    user_id: PyObjectId
    token: str  # Unique token (hashed)
    expires_at: datetime
    used: bool = False


class SectionRequest(DocumentModel):
    attraction_id: PyObjectId
    admin_id: PyObjectId
    section_name: str
    description: str
    status: SectionRequestStatus = SectionRequestStatus.PENDING
    reviewed_by: PyObjectId | None = None
    reviewed_at: datetime | None = None


class SubscriptionTransaction(DocumentModel):
    attraction_id: PyObjectId
    admin_id: PyObjectId
    amount: float
    transaction_type: SubscriptionPlan
    status: str = "completed"
    payment_date: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime
    period_end: datetime
    card_last4: str
    card_brand: str
    auto_renew_snapshot: bool = True
    reference: str


class Session(DocumentModel):
    """User session for refresh token management."""
    user_id: PyObjectId
    token_jti: str = Field(description="Unique token identifier")
    expires_at: datetime
    revoked: bool = False
    user_agent: str | None = None
    ip_address: str | None = None
