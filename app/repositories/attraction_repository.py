"""Attraction repository for database operations."""
from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import Attraction, SubscriptionStatus, SubscriptionPlan
from app.repositories.base import BaseRepository


class AttractionRepository(BaseRepository[Attraction]):
    """Repository for Attraction collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "attractions", Attraction)

    async def find_by_admin(
        self,
        admin_id: str | ObjectId,
    ) -> Attraction | None:
        """Find attraction by admin ID."""
        return await self.find_one({
            "admin_id": self._to_object_id(admin_id)
        })

    async def update_subscription(
        self,
        attraction_id: str | ObjectId,
        subscription_status: SubscriptionStatus,
        subscription_plan: SubscriptionPlan | None,
        subscription_start: datetime | None,
        subscription_end: datetime | None,
        auto_renew: bool = True,
    ) -> Attraction | None:
        """Update attraction subscription info."""
        update_data = {
            "subscription_status": subscription_status.value,
            "subscription_plan": subscription_plan.value if subscription_plan else None,
            "subscription_start": subscription_start,
            "subscription_end": subscription_end,
            "auto_renew": auto_renew,
        }
        return await self.update(attraction_id, update_data)

    async def update_payment_info(
        self,
        attraction_id: str | ObjectId,
        card_last4: str,
        card_brand: str,
        last_payment_date: datetime,
    ) -> Attraction | None:
        """Update payment card info."""
        return await self.update(attraction_id, {
            "card_last4": card_last4,
            "card_brand": card_brand,
            "last_payment_date": last_payment_date,
        })

    async def set_auto_renew(
        self,
        attraction_id: str | ObjectId,
        auto_renew: bool,
    ) -> Attraction | None:
        """Update auto-renew setting."""
        return await self.update(attraction_id, {"auto_renew": auto_renew})

    async def find_expiring_soon(
        self,
        days_until_expiry: int = 7,
    ) -> list[Attraction]:
        """Find attractions with subscriptions expiring soon."""
        now = datetime.utcnow()
        expiry_threshold = datetime(
            now.year, now.month, now.day + days_until_expiry
        )

        return await self.find_all({
            "subscription_status": SubscriptionStatus.ACTIVE.value,
            "subscription_end": {
                "$lte": expiry_threshold,
                "$gte": now,
            },
        })

    async def find_expired(self) -> list[Attraction]:
        """Find attractions with expired subscriptions."""
        now = datetime.utcnow()
        return await self.find_all({
            "subscription_status": SubscriptionStatus.ACTIVE.value,
            "subscription_end": {"$lt": now},
        })

    async def expire_subscription(
        self,
        attraction_id: str | ObjectId,
    ) -> Attraction | None:
        """Mark subscription as expired."""
        return await self.update(attraction_id, {
            "subscription_status": SubscriptionStatus.EXPIRED.value,
        })
