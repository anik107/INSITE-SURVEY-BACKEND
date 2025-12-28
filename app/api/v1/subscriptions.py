"""Subscription management endpoints."""
from fastapi import APIRouter, Query

from app.api.deps import (
    AttractionAdminUser,
    DatabaseDep,
    UserRepoDep,
)
from app.models.schemas.subscription import (
    SubscribeRequest,
    SubscriptionStatusResponse,
    SubscriptionResult,
    TransactionResponse,
    TransactionListResponse,
    TransactionSummary,
    PricingResponse,
    AutoRenewUpdate,
)
from app.repositories.attraction_repository import AttractionRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService


router = APIRouter(prefix="/subscriptions", tags=["Subscription Management"])


def get_subscription_service(
    db: DatabaseDep,
    user_repo: UserRepoDep,
) -> SubscriptionService:
    """Get subscription service instance."""
    return SubscriptionService(
        attraction_repo=AttractionRepository(db),
        subscription_repo=SubscriptionRepository(db),
        user_repo=user_repo,
    )


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing(
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Get subscription pricing information.

    Returns available plans and their prices.
    """
    service = get_subscription_service(db, user_repo)
    pricing = await service.get_pricing()
    return PricingResponse(**pricing)


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Get current subscription status.

    Returns the current subscription details for the attraction.

    Requires Attraction Admin role.
    """
    service = get_subscription_service(db, user_repo)
    status = await service.get_subscription_status(str(current_user.attraction_id))
    return SubscriptionStatusResponse(**status)


@router.post("/subscribe", response_model=SubscriptionResult)
async def subscribe(
    body: SubscribeRequest,
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Subscribe to a plan or renew subscription.

    This is a simulated payment flow. In production, this would integrate with Stripe.

    Requires Attraction Admin role.
    """
    service = get_subscription_service(db, user_repo)
    result = await service.subscribe(
        attraction_id=str(current_user.attraction_id),
        admin_id=str(current_user.id),
        plan=body.plan,
        card_last4=body.card_last4,
        card_brand=body.card_brand,
        auto_renew=body.auto_renew,
    )
    return SubscriptionResult(**result)


@router.post("/auto-renew/enable", response_model=AutoRenewUpdate)
async def enable_auto_renew(
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Enable auto-renewal for subscription.

    Requires Attraction Admin role.
    """
    service = get_subscription_service(db, user_repo)
    await service.enable_auto_renew(str(current_user.attraction_id))
    return AutoRenewUpdate(
        auto_renew=True,
        message="Auto-renewal enabled successfully",
    )


@router.post("/auto-renew/disable", response_model=AutoRenewUpdate)
async def disable_auto_renew(
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Disable auto-renewal for subscription.

    Your subscription will remain active until the end of the current period.

    Requires Attraction Admin role.
    """
    service = get_subscription_service(db, user_repo)
    await service.cancel_auto_renew(str(current_user.attraction_id))
    return AutoRenewUpdate(
        auto_renew=False,
        message="Auto-renewal disabled. Your subscription will expire at the end of the current period.",
    )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transaction_history(
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get transaction history.

    Returns all subscription transactions for the attraction.

    Requires Attraction Admin role.
    """
    service = get_subscription_service(db, user_repo)
    transactions, total = await service.get_transaction_history(
        attraction_id=str(current_user.attraction_id),
        skip=skip,
        limit=limit,
    )

    return TransactionListResponse(
        items=[TransactionResponse(**_format_transaction(t.model_dump())) for t in transactions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/transactions/summary", response_model=TransactionSummary)
async def get_transaction_summary(
    current_user: AttractionAdminUser,
    db: DatabaseDep,
    user_repo: UserRepoDep,
):
    """
    Get transaction summary.

    Returns aggregated transaction statistics.

    Requires Attraction Admin role.
    """
    service = get_subscription_service(db, user_repo)
    summary = await service.get_transaction_summary(str(current_user.attraction_id))
    return TransactionSummary(**summary)


def _format_transaction(txn: dict) -> dict:
    """Format transaction dict for response."""
    # Convert ObjectId fields to strings
    if "_id" in txn:
        txn["_id"] = str(txn["_id"])
    if "id" in txn:
        txn["id"] = str(txn["id"])
    if "attraction_id" in txn:
        txn["attraction_id"] = str(txn["attraction_id"])
    if "admin_id" in txn:
        txn["admin_id"] = str(txn["admin_id"])
    return txn
