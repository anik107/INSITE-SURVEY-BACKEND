"""Survey response repository for database operations."""
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import SurveyResponse
from app.repositories.base import BaseRepository


class ResponseRepository(BaseRepository[SurveyResponse]):
    """Repository for SurveyResponse collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "survey_responses", SurveyResponse)

    async def find_by_survey(
        self,
        survey_id: str | ObjectId,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SurveyResponse]:
        """Find responses for survey with optional date filtering."""
        filter: dict[str, Any] = {"survey_id": self._to_object_id(survey_id)}

        if start_date or end_date:
            filter["submitted_at"] = {}
            if start_date:
                filter["submitted_at"]["$gte"] = start_date
            if end_date:
                filter["submitted_at"]["$lte"] = end_date

        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("submitted_at", -1)],
        )

    async def count_by_survey(
        self,
        survey_id: str | ObjectId,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count responses for survey."""
        filter: dict[str, Any] = {"survey_id": self._to_object_id(survey_id)}

        if start_date or end_date:
            filter["submitted_at"] = {}
            if start_date:
                filter["submitted_at"]["$gte"] = start_date
            if end_date:
                filter["submitted_at"]["$lte"] = end_date

        return await self.count(filter)

    async def find_by_attraction(
        self,
        attraction_id: str | ObjectId,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SurveyResponse]:
        """Find all responses for attraction."""
        filter: dict[str, Any] = {"attraction_id": self._to_object_id(attraction_id)}

        if start_date or end_date:
            filter["submitted_at"] = {}
            if start_date:
                filter["submitted_at"]["$gte"] = start_date
            if end_date:
                filter["submitted_at"]["$lte"] = end_date

        return await self.find_many(
            filter,
            skip=skip,
            limit=limit,
            sort=[("submitted_at", -1)],
        )

    async def count_by_attraction(
        self,
        attraction_id: str | ObjectId,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count responses for attraction."""
        filter: dict[str, Any] = {"attraction_id": self._to_object_id(attraction_id)}

        if start_date or end_date:
            filter["submitted_at"] = {}
            if start_date:
                filter["submitted_at"]["$gte"] = start_date
            if end_date:
                filter["submitted_at"]["$lte"] = end_date

        return await self.count(filter)

    async def check_duplicate(
        self,
        survey_id: str,
        fingerprint: str,
        window_hours: int = 12,
    ) -> bool:
        """Check if fingerprint exists within time window for survey."""
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        return await self.exists({
            "survey_id": self._to_object_id(survey_id),
            "duplicate_fingerprint": fingerprint,
            "submitted_at": {"$gte": cutoff},
        })

    async def get_survey_analytics(
        self,
        survey_id: str | ObjectId,
    ) -> dict[str, Any]:
        """Aggregate analytics for survey."""
        pipeline = [
            {"$match": {"survey_id": self._to_object_id(survey_id)}},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "spaces_places_sum": {"$sum": "$tag_scores.spaces_places"},
                    "spaces_places_count": {
                        "$sum": {"$cond": [{"$ifNull": ["$tag_scores.spaces_places", False]}, 1, 0]}
                    },
                    "empathy_emotion_sum": {"$sum": "$tag_scores.empathy_emotion"},
                    "empathy_emotion_count": {
                        "$sum": {"$cond": [{"$ifNull": ["$tag_scores.empathy_emotion", False]}, 1, 0]}
                    },
                    "storytelling_sum": {"$sum": "$tag_scores.storytelling"},
                    "storytelling_count": {
                        "$sum": {"$cond": [{"$ifNull": ["$tag_scores.storytelling", False]}, 1, 0]}
                    },
                }
            },
        ]

        results = await self.aggregate(pipeline)
        if not results:
            return {"total": 0, "tag_scores": {}, "section_scores": {}}

        result = results[0]
        tag_scores = {}

        # Spaces & Places
        if result.get("spaces_places_count", 0) > 0:
            tag_scores["spaces_places"] = {
                "average": result["spaces_places_sum"] / result["spaces_places_count"],
                "count": result["spaces_places_count"],
            }

        # Empathy & Emotion
        if result.get("empathy_emotion_count", 0) > 0:
            tag_scores["empathy_emotion"] = {
                "average": result["empathy_emotion_sum"] / result["empathy_emotion_count"],
                "count": result["empathy_emotion_count"],
            }

        # Storytelling
        if result.get("storytelling_count", 0) > 0:
            tag_scores["storytelling"] = {
                "average": result["storytelling_sum"] / result["storytelling_count"],
                "count": result["storytelling_count"],
            }

        return {
            "total": result.get("total", 0),
            "tag_scores": tag_scores,
            "section_scores": {},  # Would need separate aggregation
        }

    async def get_attraction_analytics(
        self,
        attraction_id: str | ObjectId,
    ) -> dict[str, Any]:
        """Aggregate analytics for attraction."""
        pipeline = [
            {"$match": {"attraction_id": self._to_object_id(attraction_id)}},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "spaces_places_sum": {"$sum": "$tag_scores.spaces_places"},
                    "spaces_places_count": {
                        "$sum": {"$cond": [{"$ifNull": ["$tag_scores.spaces_places", False]}, 1, 0]}
                    },
                    "empathy_emotion_sum": {"$sum": "$tag_scores.empathy_emotion"},
                    "empathy_emotion_count": {
                        "$sum": {"$cond": [{"$ifNull": ["$tag_scores.empathy_emotion", False]}, 1, 0]}
                    },
                    "storytelling_sum": {"$sum": "$tag_scores.storytelling"},
                    "storytelling_count": {
                        "$sum": {"$cond": [{"$ifNull": ["$tag_scores.storytelling", False]}, 1, 0]}
                    },
                }
            },
        ]

        results = await self.aggregate(pipeline)
        if not results:
            return {"total": 0, "tag_scores": {}, "section_scores": {}}

        result = results[0]
        tag_scores = {}

        if result.get("spaces_places_count", 0) > 0:
            tag_scores["spaces_places"] = {
                "average": result["spaces_places_sum"] / result["spaces_places_count"],
                "count": result["spaces_places_count"],
            }

        if result.get("empathy_emotion_count", 0) > 0:
            tag_scores["empathy_emotion"] = {
                "average": result["empathy_emotion_sum"] / result["empathy_emotion_count"],
                "count": result["empathy_emotion_count"],
            }

        if result.get("storytelling_count", 0) > 0:
            tag_scores["storytelling"] = {
                "average": result["storytelling_sum"] / result["storytelling_count"],
                "count": result["storytelling_count"],
            }

        return {
            "total": result.get("total", 0),
            "tag_scores": tag_scores,
            "section_scores": {},
        }

    async def get_daily_trend(
        self,
        attraction_id: str | ObjectId,
        survey_id: str | ObjectId | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily response trend."""
        match_filter: dict[str, Any] = {
            "attraction_id": self._to_object_id(attraction_id)
        }

        if survey_id:
            match_filter["survey_id"] = self._to_object_id(survey_id)

        if start_date or end_date:
            match_filter["submitted_at"] = {}
            if start_date:
                match_filter["submitted_at"]["$gte"] = start_date
            if end_date:
                match_filter["submitted_at"]["$lte"] = end_date

        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$submitted_at",
                        }
                    },
                    "count": {"$sum": 1},
                    "spaces_places_avg": {"$avg": "$tag_scores.spaces_places"},
                    "empathy_emotion_avg": {"$avg": "$tag_scores.empathy_emotion"},
                    "storytelling_avg": {"$avg": "$tag_scores.storytelling"},
                }
            },
            {"$sort": {"_id": 1}},
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id",
                    "count": 1,
                    "tag_averages": {
                        "spaces_places": "$spaces_places_avg",
                        "empathy_emotion": "$empathy_emotion_avg",
                        "storytelling": "$storytelling_avg",
                    },
                }
            },
        ]

        return await self.aggregate(pipeline)
