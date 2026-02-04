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

    async def list_attractions_enriched(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        """
        List attractions with admin data using aggregation pipeline.
        Returns raw dicts with admin_name, admin_email, admin_username pre-joined.

        This replaces the N+1 query pattern with a single aggregation query.
        """
        # Aggregation pipeline
        pipeline = [
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},

            # Join with users collection for admin data
            {
                "$lookup": {
                    "from": "users",
                    "localField": "admin_id",
                    "foreignField": "_id",
                    "as": "admin_data"
                }
            },

            # Project final shape
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "admin_id": 1,
                    "monthly_fee": 1,
                    "yearly_fee": 1,
                    "subscription_status": 1,
                    "subscription_plan": 1,
                    "subscription_start": 1,
                    "subscription_end": 1,
                    "auto_renew": 1,
                    "card_last4": 1,
                    "card_brand": 1,
                    "last_payment_date": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "admin_name": {"$arrayElemAt": ["$admin_data.name", 0]},
                    "admin_email": {"$arrayElemAt": ["$admin_data.email", 0]},
                    "admin_username": {"$arrayElemAt": ["$admin_data.username", 0]},
                    "admin_status": {"$arrayElemAt": ["$admin_data.status", 0]},
                }
            }
        ]

        # Execute aggregation
        results = await self.aggregate(pipeline)

        # Get total count
        total = await self.count()

        return results, total
