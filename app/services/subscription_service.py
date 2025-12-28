"""Subscription service for business logic."""
import secrets
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Any

from bson import ObjectId

from app.core.exceptions import NotFoundError, ValidationError, BusinessRuleError
from app.models.domain import (
    Attraction,
    SubscriptionStatus,
    SubscriptionPlan,
    SubscriptionTransaction,
    User,
)
from app.repositories.attraction_repository import AttractionRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository


# Subscription pricing
SUBSCRIPTION_PRICES = {
    SubscriptionPlan.MONTHLY: 0.0,  # Monthly is free (or configure as needed)
    SubscriptionPlan.YEARLY: 199.0,
}


class SubscriptionService:
    """Service for subscription management operations."""

    def __init__(
        self,
        attraction_repo: AttractionRepository,
        subscription_repo: SubscriptionRepository,
        user_repo: UserRepository,
    ):
        self.attraction_repo = attraction_repo
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo

    def _generate_reference(self) -> str:
        """Generate a unique transaction reference."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4).upper()
        return f"TXN-{timestamp}-{random_part}"

    def _calculate_period_end(
        self,
        start: datetime,
        plan: SubscriptionPlan,
    ) -> datetime:
        """Calculate subscription period end date."""
        if plan == SubscriptionPlan.MONTHLY:
            return start + relativedelta(months=1)
        else:  # YEARLY
            return start + relativedelta(years=1)

    async def get_subscription_status(
        self,
        attraction_id: str,
    ) -> dict[str, Any]:
        """Get current subscription status for an attraction."""
        attraction = await self.attraction_repo.find_by_id(attraction_id)
        if not attraction:
            raise NotFoundError("Attraction", attraction_id)

        # Get latest transaction
        latest_transaction = await self.subscription_repo.find_latest_transaction(
            attraction_id
        )

        return {
            "status": attraction.subscription_status,
            "plan": attraction.subscription_plan,
            "start_date": attraction.subscription_start,
            "end_date": attraction.subscription_end,
            "auto_renew": attraction.auto_renew,
            "card_last4": attraction.card_last4,
            "card_brand": attraction.card_brand,
            "last_payment_date": attraction.last_payment_date,
            "latest_transaction": latest_transaction.model_dump() if latest_transaction else None,
        }

    async def subscribe(
        self,
        attraction_id: str,
        admin_id: str,
        plan: SubscriptionPlan,
        card_last4: str = "4242",
        card_brand: str = "visa",
        auto_renew: bool = True,
    ) -> dict[str, Any]:
        """
        Activate or renew subscription.

        This is a simulated payment flow. In production, integrate with Stripe.
        """
        attraction = await self.attraction_repo.find_by_id(attraction_id)
        if not attraction:
            raise NotFoundError("Attraction", attraction_id)

        # Calculate subscription period
        now = datetime.utcnow()
        period_start = now

        # If renewing an active subscription, extend from current end date
        if (
            attraction.subscription_status == SubscriptionStatus.ACTIVE
            and attraction.subscription_end
            and attraction.subscription_end > now
        ):
            period_start = attraction.subscription_end

        period_end = self._calculate_period_end(period_start, plan)

        # Get amount based on plan
        amount = SUBSCRIPTION_PRICES.get(plan, 0.0)

        # Generate transaction reference
        reference = self._generate_reference()

        # Create transaction record
        transaction = await self.subscription_repo.create_transaction(
            attraction_id=attraction_id,
            admin_id=admin_id,
            amount=amount,
            transaction_type=plan,
            period_start=period_start,
            period_end=period_end,
            card_last4=card_last4,
            card_brand=card_brand,
            reference=reference,
            auto_renew=auto_renew,
        )

        # Update attraction subscription info
        await self.attraction_repo.update_subscription(
            attraction_id=attraction_id,
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_plan=plan,
            subscription_start=period_start,
            subscription_end=period_end,
            auto_renew=auto_renew,
        )

        # Update payment info
        await self.attraction_repo.update_payment_info(
            attraction_id=attraction_id,
            card_last4=card_last4,
            card_brand=card_brand,
            last_payment_date=now,
        )

        # Update user subscription info
        await self.user_repo.update_subscription_info(
            user_id=admin_id,
            subscription_status=SubscriptionStatus.ACTIVE.value,
            subscription_end=period_end,
        )

        return {
            "success": True,
            "transaction_id": str(transaction.id),
            "reference": reference,
            "amount": amount,
            "plan": plan.value,
            "period_start": period_start,
            "period_end": period_end,
            "message": f"Subscription activated successfully. Valid until {period_end.strftime('%Y-%m-%d')}",
        }

    async def cancel_auto_renew(
        self,
        attraction_id: str,
    ) -> Attraction:
        """Turn off auto-renewal for subscription."""
        attraction = await self.attraction_repo.find_by_id(attraction_id)
        if not attraction:
            raise NotFoundError("Attraction", attraction_id)

        if attraction.subscription_status != SubscriptionStatus.ACTIVE:
            raise ValidationError("No active subscription to cancel auto-renewal")

        updated = await self.attraction_repo.set_auto_renew(attraction_id, False)
        if not updated:
            raise NotFoundError("Attraction", attraction_id)

        return updated

    async def enable_auto_renew(
        self,
        attraction_id: str,
    ) -> Attraction:
        """Turn on auto-renewal for subscription."""
        attraction = await self.attraction_repo.find_by_id(attraction_id)
        if not attraction:
            raise NotFoundError("Attraction", attraction_id)

        if attraction.subscription_status != SubscriptionStatus.ACTIVE:
            raise ValidationError("No active subscription to enable auto-renewal")

        updated = await self.attraction_repo.set_auto_renew(attraction_id, True)
        if not updated:
            raise NotFoundError("Attraction", attraction_id)

        return updated

    async def get_transaction_history(
        self,
        attraction_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SubscriptionTransaction], int]:
        """Get transaction history for an attraction."""
        attraction = await self.attraction_repo.find_by_id(attraction_id)
        if not attraction:
            raise NotFoundError("Attraction", attraction_id)

        transactions = await self.subscription_repo.find_by_attraction(
            attraction_id, skip, limit
        )
        total = await self.subscription_repo.count_by_attraction(attraction_id)

        return transactions, total

    async def get_transaction_summary(
        self,
        attraction_id: str,
    ) -> dict[str, Any]:
        """Get transaction summary for an attraction."""
        attraction = await self.attraction_repo.find_by_id(attraction_id)
        if not attraction:
            raise NotFoundError("Attraction", attraction_id)

        return await self.subscription_repo.get_transaction_summary(attraction_id)

    async def process_expired_subscriptions(self) -> int:
        """
        Process expired subscriptions (for cron job).

        Returns count of expired subscriptions processed.
        """
        expired = await self.attraction_repo.find_expired()
        count = 0

        for attraction in expired:
            # Check if auto-renew is enabled
            if attraction.auto_renew and attraction.card_last4:
                # In production, attempt auto-renewal via Stripe
                # For now, just log it as a renewal attempt
                pass
            else:
                # Mark as expired
                await self.attraction_repo.expire_subscription(attraction.id)

                # Update user subscription status
                if attraction.admin_id:
                    await self.user_repo.update_subscription_info(
                        user_id=attraction.admin_id,
                        subscription_status=SubscriptionStatus.EXPIRED.value,
                        subscription_end=attraction.subscription_end,
                    )

                count += 1

        return count

    async def get_pricing(self) -> dict[str, Any]:
        """Get subscription pricing info."""
        return {
            "plans": [
                {
                    "plan": SubscriptionPlan.MONTHLY.value,
                    "price": SUBSCRIPTION_PRICES[SubscriptionPlan.MONTHLY],
                    "description": "Monthly subscription",
                    "billing_period": "month",
                },
                {
                    "plan": SubscriptionPlan.YEARLY.value,
                    "price": SUBSCRIPTION_PRICES[SubscriptionPlan.YEARLY],
                    "description": "Yearly subscription (save more!)",
                    "billing_period": "year",
                },
            ],
            "currency": "USD",
        }
