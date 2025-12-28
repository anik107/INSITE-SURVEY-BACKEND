"""Subscription management schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import SubscriptionStatus, SubscriptionPlan


class SubscribeRequest(BaseModel):
    """Request body for subscribing to a plan."""
    plan: SubscriptionPlan
    card_last4: str = Field(default="4242", min_length=4, max_length=4)
    card_brand: str = Field(default="visa", max_length=20)
    auto_renew: bool = True


class SubscriptionStatusResponse(BaseModel):
    """Response for subscription status."""
    status: SubscriptionStatus
    plan: SubscriptionPlan | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    auto_renew: bool = True
    card_last4: str | None = None
    card_brand: str | None = None
    last_payment_date: datetime | None = None


class SubscriptionResult(BaseModel):
    """Response after subscription action."""
    success: bool
    transaction_id: str | None = None
    reference: str | None = None
    amount: float = 0.0
    plan: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    message: str


class TransactionResponse(BaseModel):
    """Response for a single transaction."""
    id: str = Field(alias="_id")
    attraction_id: str
    admin_id: str
    amount: float
    transaction_type: str
    status: str
    payment_date: datetime
    period_start: datetime
    period_end: datetime
    card_last4: str
    card_brand: str
    auto_renew_snapshot: bool
    reference: str
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Response for transaction list."""
    items: list[TransactionResponse]
    total: int
    skip: int
    limit: int


class TransactionSummary(BaseModel):
    """Transaction summary response."""
    total_amount: float
    transaction_count: int
    first_payment: datetime | None = None
    last_payment: datetime | None = None


class PlanInfo(BaseModel):
    """Subscription plan info."""
    plan: str
    price: float
    description: str
    billing_period: str


class PricingResponse(BaseModel):
    """Response for pricing info."""
    plans: list[PlanInfo]
    currency: str


class AutoRenewUpdate(BaseModel):
    """Response after auto-renew update."""
    auto_renew: bool
    message: str
