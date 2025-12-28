"""Survey repository for database operations."""
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import Survey, SurveyStatus
from app.repositories.base import BaseRepository


class SurveyRepository(BaseRepository[Survey]):
    """Repository for Survey collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "surveys", Survey)

    async def find_by_share_id(self, share_id: str) -> Survey | None:
        """Find survey by public share_id."""
        return await self.find_one({"share_id": share_id})

    async def find_published_by_share_id(self, share_id: str) -> Survey | None:
        """Find published survey by share_id."""
        return await self.find_one({
            "share_id": share_id,
            "status": SurveyStatus.PUBLISHED.value,
        })

    async def find_published_for_attraction(
        self,
        attraction_id: str | ObjectId,
    ) -> Survey | None:
        """Find published survey for attraction."""
        return await self.find_one({
            "attraction_id": self._to_object_id(attraction_id),
            "status": SurveyStatus.PUBLISHED.value,
        })

    async def find_by_attraction(
        self,
        attraction_id: str | ObjectId,
        status: SurveyStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Survey]:
        """Find surveys for attraction."""
        filter = {"attraction_id": self._to_object_id(attraction_id)}
        if status:
            filter["status"] = status.value
        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("updated_at", -1)],
        )

    async def count_by_attraction(
        self,
        attraction_id: str | ObjectId,
        status: SurveyStatus | None = None,
    ) -> int:
        """Count surveys for attraction."""
        filter = {"attraction_id": self._to_object_id(attraction_id)}
        if status:
            filter["status"] = status.value
        return await self.count(filter)

    async def find_by_template(
        self,
        template_id: str | ObjectId,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Survey]:
        """Find surveys using a template."""
        return await self.find_many(
            {"template_id": self._to_object_id(template_id)},
            skip=skip,
            limit=limit,
            sort=[("updated_at", -1)],
        )

    async def archive_published_for_attraction(
        self,
        attraction_id: str | ObjectId,
    ) -> bool:
        """Archive currently published survey for attraction."""
        now = datetime.utcnow()
        result = await self.collection.update_one(
            {
                "attraction_id": self._to_object_id(attraction_id),
                "status": SurveyStatus.PUBLISHED.value,
            },
            {
                "$set": {
                    "status": SurveyStatus.ARCHIVED.value,
                    "archived_at": now,
                    "updated_at": now,
                }
            },
        )
        return result.modified_count > 0

    async def publish(self, survey_id: str | ObjectId) -> Survey | None:
        """Publish a survey."""
        now = datetime.utcnow()
        return await self.update(
            survey_id,
            {
                "status": SurveyStatus.PUBLISHED.value,
                "published_at": now,
            },
        )

    async def archive(self, survey_id: str | ObjectId) -> Survey | None:
        """Archive a survey."""
        now = datetime.utcnow()
        return await self.update(
            survey_id,
            {
                "status": SurveyStatus.ARCHIVED.value,
                "archived_at": now,
            },
        )

    async def share_id_exists(self, share_id: str) -> bool:
        """Check if share_id is already taken."""
        return await self.exists({"share_id": share_id})

    async def update_qr_code(
        self,
        survey_id: str | ObjectId,
        qr_code_url: str,
    ) -> Survey | None:
        """Update survey QR code URL."""
        return await self.update(survey_id, {"qr_code_url": qr_code_url})

    async def has_responses(self, survey_id: str | ObjectId) -> bool:
        """Check if survey has any responses."""
        db = self.collection.database
        count = await db.survey_responses.count_documents(
            {"survey_id": self._to_object_id(survey_id)},
            limit=1,
        )
        return count > 0
