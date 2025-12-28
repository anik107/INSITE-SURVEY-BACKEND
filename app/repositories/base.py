"""Base repository with generic CRUD operations."""
from datetime import datetime
from typing import Any, Generic, TypeVar, Type

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from app.models.base import DocumentModel

T = TypeVar("T", bound=DocumentModel)


class BaseRepository(Generic[T]):
    """Generic repository with CRUD operations for MongoDB collections."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        collection_name: str,
        model_class: Type[T],
    ):
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_class = model_class

    def _to_object_id(self, id: str | ObjectId) -> ObjectId:
        """Convert string to ObjectId if needed."""
        return ObjectId(id) if isinstance(id, str) else id

    def _doc_to_model(self, doc: dict[str, Any] | None) -> T | None:
        """Convert MongoDB document to Pydantic model."""
        if doc is None:
            return None
        return self.model_class(**doc)

    async def find_by_id(self, id: str | ObjectId) -> T | None:
        """Find document by _id."""
        doc = await self.collection.find_one({"_id": self._to_object_id(id)})
        return self._doc_to_model(doc)

    async def find_one(self, filter: dict[str, Any]) -> T | None:
        """Find single document matching filter."""
        doc = await self.collection.find_one(filter)
        return self._doc_to_model(doc)

    async def find_many(
        self,
        filter: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        """Find documents with pagination and sorting."""
        cursor = self.collection.find(filter or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self.model_class(**doc) for doc in docs]

    async def find_all(
        self,
        filter: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        """Find all documents matching filter (no pagination)."""
        cursor = self.collection.find(filter or {})
        if sort:
            cursor = cursor.sort(sort)
        docs = await cursor.to_list(length=None)
        return [self.model_class(**doc) for doc in docs]

    async def count(self, filter: dict[str, Any] | None = None) -> int:
        """Count documents matching filter."""
        return await self.collection.count_documents(filter or {})

    async def exists(self, filter: dict[str, Any]) -> bool:
        """Check if document exists matching filter."""
        return await self.collection.count_documents(filter, limit=1) > 0

    async def create(self, data: dict[str, Any]) -> T:
        """
        Insert new document.

        Args:
            data: Document data (without _id, created_at, updated_at)

        Returns:
            Created document as model
        """
        now = datetime.utcnow()
        doc = {
            "_id": ObjectId(),
            **data,
            "created_at": now,
            "updated_at": now,
        }

        await self.collection.insert_one(doc)
        return self.model_class(**doc)

    async def create_from_model(self, model: T) -> T:
        """
        Insert new document from model.

        Args:
            model: Pydantic model to insert

        Returns:
            Created document as model
        """
        now = datetime.utcnow()
        data = model.model_dump(by_alias=True, exclude_none=True)

        if "_id" not in data or data["_id"] is None:
            data["_id"] = ObjectId()

        data["created_at"] = now
        data["updated_at"] = now

        await self.collection.insert_one(data)
        return self.model_class(**data)

    async def update(
        self,
        id: str | ObjectId,
        data: dict[str, Any],
    ) -> T | None:
        """
        Update document by _id.

        Args:
            id: Document ID
            data: Fields to update

        Returns:
            Updated document or None if not found
        """
        data["updated_at"] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            {"_id": self._to_object_id(id)},
            {"$set": data},
            return_document=True,
        )
        return self._doc_to_model(result)

    async def update_many(
        self,
        filter: dict[str, Any],
        data: dict[str, Any],
    ) -> int:
        """
        Update multiple documents matching filter.

        Returns:
            Number of documents modified
        """
        data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_many(filter, {"$set": data})
        return result.modified_count

    async def delete(self, id: str | ObjectId) -> bool:
        """
        Delete document by _id.

        Returns:
            True if deleted, False if not found
        """
        result = await self.collection.delete_one({"_id": self._to_object_id(id)})
        return result.deleted_count > 0

    async def delete_many(self, filter: dict[str, Any]) -> int:
        """
        Delete multiple documents matching filter.

        Returns:
            Number of documents deleted
        """
        result = await self.collection.delete_many(filter)
        return result.deleted_count

    async def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run aggregation pipeline."""
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=None)
