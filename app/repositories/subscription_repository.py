"""Subscription transaction repository for database operations."""
from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import SubscriptionTransaction, SubscriptionPlan
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[SubscriptionTransaction]):
    """Repository for SubscriptionTransaction collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "subscription_transactions", SubscriptionTransaction)

    async def find_by_attraction(
        self,
        attraction_id: str | ObjectId,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SubscriptionTransaction]:
        """Find subscription transactions for an attraction."""
        return await self.find_many(
            {"attraction_id": self._to_object_id(attraction_id)},
            skip=skip,
            limit=limit,
            sort=[("payment_date", -1)],
        )

    async def count_by_attraction(
        self,
        attraction_id: str | ObjectId,
    ) -> int:
        """Count subscription transactions for an attraction."""
        return await self.count({
            "attraction_id": self._to_object_id(attraction_id)
        })

    async def find_latest_transaction(
        self,
        attraction_id: str | ObjectId,
    ) -> SubscriptionTransaction | None:
        """Find the most recent transaction for an attraction."""
        transactions = await self.find_many(
            {"attraction_id": self._to_object_id(attraction_id)},
            skip=0,
            limit=1,
            sort=[("payment_date", -1)],
        )
        return transactions[0] if transactions else None

    async def create_transaction(
        self,
        attraction_id: str | ObjectId,
        admin_id: str | ObjectId,
        amount: float,
        transaction_type: SubscriptionPlan,
        period_start: datetime,
        period_end: datetime,
        card_last4: str,
        card_brand: str,
        reference: str,
        auto_renew: bool = True,
    ) -> SubscriptionTransaction:
        """Create a new subscription transaction."""
        transaction_data = {
            "attraction_id": self._to_object_id(attraction_id),
            "admin_id": self._to_object_id(admin_id),
            "amount": amount,
            "transaction_type": transaction_type.value,
            "status": "completed",
            "payment_date": datetime.utcnow(),
            "period_start": period_start,
            "period_end": period_end,
            "card_last4": card_last4,
            "card_brand": card_brand,
            "auto_renew_snapshot": auto_renew,
            "reference": reference,
        }
        return await self.create(transaction_data)

    async def get_transaction_summary(
        self,
        attraction_id: str | ObjectId,
    ) -> dict[str, Any]:
        """Get transaction summary for an attraction."""
        pipeline = [
            {"$match": {"attraction_id": self._to_object_id(attraction_id)}},
            {
                "$group": {
                    "_id": None,
                    "total_amount": {"$sum": "$amount"},
                    "transaction_count": {"$sum": 1},
                    "first_payment": {"$min": "$payment_date"},
                    "last_payment": {"$max": "$payment_date"},
                }
            },
        ]
        result = await self.aggregate(pipeline)
        if result:
            return {
                "total_amount": result[0].get("total_amount", 0),
                "transaction_count": result[0].get("transaction_count", 0),
                "first_payment": result[0].get("first_payment"),
                "last_payment": result[0].get("last_payment"),
            }
        return {
            "total_amount": 0,
            "transaction_count": 0,
            "first_payment": None,
            "last_payment": None,
        }
